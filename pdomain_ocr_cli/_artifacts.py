from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol
from uuid import uuid4

if TYPE_CHECKING:
    from pathlib import Path


def _open_staged(path: Path) -> tuple[int, Path]:
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
        staged = path.parent / f".{path.name}.{uuid4().hex}.tmp"
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
    txt_path: Path
    json_path: Path
    extra_paths: list[str] = field(default_factory=list)

    def write_text_last(self, text: str) -> None:
        atomic_write_text(self.txt_path, text)
