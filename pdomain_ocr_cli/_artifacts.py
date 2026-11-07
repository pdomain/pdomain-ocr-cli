from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _open_staged(path: Path, *, suffix: str = ".tmp") -> tuple[int, Path]:
    """Create a staging file beside *path*, open for writing.

    Not ``tempfile.mkstemp``: that hardcodes 0600 and ignores the umask, which
    is right for a private scratch file and wrong for one about to be
    published, because a rename preserves the mode. Passing the mode to
    ``os.open`` lets the kernel apply the umask exactly as for a plain
    ``open()``, so there is no chmod to forget. 0666, not 0777: nothing
    published this way is a program. ``O_EXCL`` keeps ``mkstemp``'s guarantee
    that creation fails rather than following a symlink into an existing file.
    """
    while True:
        staged = path.parent / f".{path.name}.{uuid4().hex}{suffix}"
        try:
            return os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666), staged
        except FileExistsError:  # pragma: no cover - needs a uuid4 collision
            continue


def _fsync_parent_dir(path: Path) -> None:
    if os.name == "nt":  # pragma: no cover - Windows-only branch
        return
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _reserve_sibling_path(path: Path, *, suffix: str) -> Path:
    """Reserve a unique sibling path without holding its descriptor open."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, staged = _open_staged(path, suffix=suffix)
    os.close(fd)
    return staged


def _write_sibling_temp(path: Path, data: bytes, *, suffix: str) -> Path:
    """Durably write *data* beside *path* without touching *path* itself."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _open_staged(path, suffix=suffix)
    try:
        try:
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()
        raise
    return tmp


def _stage_via_writer(path: Path, writer: Callable[[Path], None], *, suffix: str) -> Path:
    """Let *writer* fill a sibling temp, then fsync it, without touching *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _open_staged(path, suffix=suffix)
    os.close(fd)
    try:
        writer(tmp)
        with tmp.open("rb") as fh:
            os.fsync(fh.fileno())
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()
        raise
    return tmp


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _open_staged(path)
    try:
        try:
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        _ = tmp.replace(path)
        _fsync_parent_dir(path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()
        raise


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


class JsonDocumentLike(Protocol):
    def to_json_file(self, file_path: str | Path) -> None: ...


def atomic_write_json_document(path: Path, doc: JsonDocumentLike) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _open_staged(path)
    os.close(fd)
    try:
        doc.to_json_file(tmp)
        with tmp.open("rb") as fh:
            os.fsync(fh.fileno())
        _ = tmp.replace(path)
        _fsync_parent_dir(path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()
        raise


@dataclass
class PageOutputTransaction:
    """Stage new page artifacts, then promote or roll them all back together.

    ``add_bytes`` and ``add_text`` durably stage new content beside each
    destination without touching the destination. ``commit`` backs up every
    pre-existing destination, then promotes every staged file into place. A
    successful commit discards the backups. If any promotion fails, or the
    process is interrupted mid-commit, ``commit`` removes the new files it
    already promoted and restores every backup, in reverse order, before
    re-raising the original failure.
    """

    _staged: list[tuple[Path, Path]] = field(default_factory=list, init=False, repr=False)
    _backups: list[tuple[Path, Path]] = field(default_factory=list, init=False, repr=False)
    _promoted: list[Path] = field(default_factory=list, init=False, repr=False)
    _committed: bool = field(default=False, init=False, repr=False)

    def add_bytes(self, path: Path, data: bytes) -> None:
        """Stage *data* for *path* without touching *path* itself."""
        try:
            staged = _write_sibling_temp(path, data, suffix=".stage")
        except BaseException:
            _ = self._discard_staged()
            raise
        self._staged.append((path, staged))

    def add_text(self, path: Path, text: str, *, encoding: str = "utf-8") -> None:
        """Stage text for *path* without touching *path* itself."""
        self.add_bytes(path, text.encode(encoding))

    def add_via_writer(self, path: Path, writer: Callable[[Path], None]) -> None:
        """Stage *path* by calling *writer* with a reserved sibling temp.

        Use this when the content is produced by writing to a path, for
        example a document object's ``to_json_file``, rather than as bytes.
        """
        try:
            staged = _stage_via_writer(path, writer, suffix=".stage")
        except BaseException:
            _ = self._discard_staged()
            raise
        self._staged.append((path, staged))

    def commit(self) -> None:
        """Promote every staged file, or restore the prior files and re-raise."""
        try:
            self._backup_existing_destinations()
            for destination, staged in self._staged:
                self._promote(destination, staged)
        except BaseException as exc:
            errors = self._rollback()
            if errors and isinstance(exc, Exception):
                raise BaseExceptionGroup(
                    "artifact promotion and rollback failed", [exc, *errors]
                ) from exc
            if errors:
                # A bare BaseException such as KeyboardInterrupt must keep its
                # own type. Wrapping it in a BaseExceptionGroup would miss both
                # the KeyboardInterrupt handler and the Exception handler in
                # the page loop.
                for error in errors:
                    exc.add_note(f"rollback also failed: {error!r}")
            raise
        else:
            self._committed = True
            self._discard_backups()

    def abort(self) -> None:
        """Remove staged files when ``commit`` did not finish.

        A failure or interrupt after a successful ``add_*`` and before
        ``commit`` would otherwise leave ``.stage`` siblings in the output
        directory. ``commit`` cleans up after itself. Calling ``abort`` after
        a successful commit does nothing.
        """
        if self._committed:
            return
        _ = self._discard_staged()

    def _backup_existing_destinations(self) -> None:
        for destination, _staged in self._staged:
            if destination.exists():
                backup = _reserve_sibling_path(destination, suffix=".bak")
                _ = destination.replace(backup)
                self._backups.append((destination, backup))

    def _promote(self, destination: Path, staged: Path) -> None:
        _ = staged.replace(destination)
        # Record the destination immediately after the rename, before the
        # parent-dir fsync. If fsync fails, rollback still knows to remove
        # the file that already landed.
        self._promoted.append(destination)
        _fsync_parent_dir(destination)

    def _rollback(self) -> list[Exception]:
        errors: list[Exception] = []
        for destination in reversed(self._promoted):
            try:
                destination.unlink(missing_ok=True)
            except Exception as exc:  # noqa: BLE001  # rollback must not mask the original failure
                errors.append(exc)
        for destination, backup in reversed(self._backups):
            try:
                _ = backup.replace(destination)
            except Exception as exc:  # noqa: BLE001  # rollback must not mask the original failure
                errors.append(exc)
        errors.extend(self._discard_staged())
        return errors

    def _discard_staged(self) -> list[Exception]:
        errors: list[Exception] = []
        for _destination, staged in self._staged:
            try:
                staged.unlink()
            except FileNotFoundError:
                continue
            except Exception as exc:  # noqa: BLE001  # rollback must not mask the original failure
                errors.append(exc)
        return errors

    def _discard_backups(self) -> None:
        # The page already promoted successfully. A failure discarding a
        # backup must not turn that page into a reported error.
        for _destination, backup in self._backups:
            with contextlib.suppress(OSError):
                backup.unlink()
