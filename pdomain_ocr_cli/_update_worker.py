"""Offline activation and rollback for a staged uv tool environment."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NamedTuple, Protocol, cast, final

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from contextlib import AbstractContextManager

_DIST = "pdomain-ocr-cli"
_JOURNAL = "transaction.json"
_RECEIPT = "uv-receipt.toml"
_VERSION = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9.+!-]*")
_LOCK_TIMEOUT = 15.0
_PROBE_TIMEOUT = 60.0
_PREFETCH_TIMEOUT = 300.0
_WINDOWS = os.name == "nt"

_Slot = Literal["old", "new", "empty"]
_Layout = tuple[_Slot, _Slot, _Slot]
_READY: _Layout = ("old", "new", "empty")
_PARKED: _Layout = ("empty", "new", "old")
_INSTALLED: _Layout = ("new", "empty", "old")
_LAYOUTS: dict[str, tuple[_Layout, ...]] = {
    "prepared": (_READY,),
    "parking": (_READY, _PARKED),
    "activating": (_PARKED, _INSTALLED),
    "deactivating": (_INSTALLED, _PARKED),
    "restoring": (_PARKED, _READY),
    "rolled back": (_READY,),
    "updated": (_INSTALLED,),
}
_Outcome = Literal["updated", "rolled back"]


class _Identity(NamedTuple):
    device: int
    inode: int
    fingerprint: str


@dataclass(frozen=True)
class _Transaction:
    journal: Path
    live: Path
    candidate: Path
    launcher: Path
    previous_version: str
    version: str
    old_identity: _Identity
    new_identity: _Identity
    launcher_identity: _Identity

    @property
    def backup(self) -> Path:
        return self.journal.parent / "backup"


class _Arguments(argparse.Namespace):
    journal: Path = Path()
    recover: bool = False


class _NativeCall(Protocol):
    argtypes: tuple[type[object], ...]
    restype: type[object]

    def __call__(self, *args: object) -> int: ...


class _NativeLibrary(Protocol):
    def __getattr__(self, name: str) -> _NativeCall: ...


class _WindowsLibrary(Protocol):
    def __call__(self, name: str, *, use_last_error: bool) -> _NativeLibrary: ...


class _WindowsError(Protocol):
    def __call__(self, code: int) -> OSError: ...


@final
class _Overlapped(ctypes.Structure):
    _fields_ = (
        ("internal", ctypes.c_size_t),
        ("internal_high", ctypes.c_size_t),
        ("offset", ctypes.c_uint32),
        ("offset_high", ctypes.c_uint32),
        ("event", ctypes.c_void_p),
    )


def _native(
    library: str, name: str, return_type: type[object], *parameter_types: type[object]
) -> _NativeCall:
    load_library = cast("_WindowsLibrary", vars(ctypes)["WinDLL"])
    function = cast("_NativeCall", getattr(load_library(library, use_last_error=True), name))
    function.argtypes = parameter_types
    function.restype = return_type
    return function


def _windows_error() -> OSError:
    code = cast("Callable[[], int]", vars(ctypes)["get_last_error"])()
    return cast("_WindowsError", vars(ctypes)["WinError"])(code)


def _require_platform() -> None:
    if os.name not in ("nt", "posix"):
        raise ValueError("This platform does not support durable OCR update activation.")


def make_workspace_private(directory: Path) -> None:
    """Restrict inherited permissions on a fresh Windows update directory."""
    if not _WINDOWS:
        return
    security = ctypes.c_void_p()
    convert = _native(
        "advapi32",
        "ConvertStringSecurityDescriptorToSecurityDescriptorW",
        ctypes.c_int,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    )
    # Only the owner, LocalSystem, and local Administrators inherit access.
    if not convert(
        "D:P(A;OICI;FA;;;OW)(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)", 1, ctypes.byref(security), None
    ):
        raise _windows_error()
    free = _native("kernel32", "LocalFree", ctypes.c_void_p, ctypes.c_void_p)
    try:
        restrict = _native(
            "advapi32",
            "SetFileSecurityW",
            ctypes.c_int,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
        )
        protected_dacl = 0x80000004
        if not restrict(str(directory), protected_dacl, security):
            raise _windows_error()
    finally:
        _ = free(security)


def _sync_windows_directory(directory: Path) -> None:
    create = _native(
        "kernel32",
        "CreateFileW",
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    # GENERIC_WRITE, share read/write/delete, OPEN_EXISTING, BACKUP_SEMANTICS.
    handle = create(str(directory), 0x40000000, 7, None, 3, 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise _windows_error()
    close = _native("kernel32", "CloseHandle", ctypes.c_int, ctypes.c_void_p)
    try:
        flush = _native("kernel32", "FlushFileBuffers", ctypes.c_int, ctypes.c_void_p)
        if not flush(handle):
            raise _windows_error()
    finally:
        _ = close(handle)


def _sync_directory(directory: Path) -> None:
    if _WINDOWS:
        _sync_windows_directory(directory)
        return
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename(source: Path, destination: Path, *, replace: bool = False) -> None:
    if _WINDOWS:
        move = _native(
            "kernel32",
            "MoveFileExW",
            ctypes.c_int,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
        )
        if not move(str(source), str(destination), 8 | int(replace)):
            raise _windows_error()
    elif replace:
        _ = source.replace(destination)
    else:
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Update destination already exists: {destination}")
        _ = source.rename(destination)


def _move(source: Path, destination: Path) -> None:
    _rename(source, destination)
    _sync_directory(destination.parent)
    if source.parent != destination.parent:
        _sync_directory(source.parent)


def _try_lock(descriptor: int) -> None:
    if _WINDOWS:
        import msvcrt

        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            raise BlockingIOError from error
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _try_installation_lock(descriptor: int, *, exclusive: bool) -> None:
    if _WINDOWS:
        import msvcrt

        lock = _native(
            "kernel32",
            "LockFileEx",
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(_Overlapped),
        )
        flags = 3 if exclusive else 1
        if not lock(msvcrt.get_osfhandle(descriptor), flags, 0, 1, 0, ctypes.byref(_Overlapped())):
            error = _windows_error()
            if cast("int | None", getattr(error, "winerror", None)) == 33:
                raise BlockingIOError from error
            raise error
    else:
        import fcntl

        mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(descriptor, mode | fcntl.LOCK_NB)


@contextmanager
def _file_lock(
    path: Path, acquire: Callable[[int], None], *, timeout: float, label: str
) -> Generator[None]:
    flags = os.O_RDWR | os.O_CREAT
    if _WINDOWS:
        if path.resolve() != path:
            raise ValueError(f"Unsupported {label} lock: {path}")
    else:
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"Unsupported {label} lock: {path}")
        deadline = time.monotonic() + timeout
        while True:
            try:
                acquire(descriptor)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for {label}'s lock at {path}") from None
                time.sleep(0.05)
        if not os.path.samestat(os.fstat(descriptor), path.lstat()):
            raise ValueError(f"{label}'s lock changed while waiting: {path}")
        yield
    finally:
        os.close(descriptor)


def _lock(directory: Path) -> AbstractContextManager[None]:
    return _file_lock(directory / ".lock", _try_lock, timeout=_LOCK_TIMEOUT, label="uv")


def _installation_lock(live: Path, *, exclusive: bool) -> AbstractContextManager[None]:
    return _file_lock(
        live.with_name(f".{live.name}.in-use.lock"),
        lambda descriptor: _try_installation_lock(descriptor, exclusive=exclusive),
        timeout=_LOCK_TIMEOUT if exclusive else 0,
        label="pdomain-ocr installation",
    )


@contextmanager
def hold_installation(live: Path) -> Generator[None]:
    """Keep the live environment in place for an installed OCR command."""
    with _installation_lock(live, exclusive=False):
        yield


def _validate_paths(journal: Path, live: Path, candidate: Path, launcher: Path) -> None:
    directory = journal.parent
    if journal.name != _JOURNAL or any(
        not path.is_absolute() or path.resolve() != path
        for path in (directory, live, candidate, launcher.parent)
    ):
        raise ValueError("The update paths must identify canonical locations.")
    workspace = directory.stat()
    if not _WINDOWS and (workspace.st_uid != os.geteuid() or workspace.st_mode & 0o077):
        raise ValueError("The update directory must be private and owned by the current user.")
    if (
        live.name != _DIST
        or directory.is_relative_to(live.parent)
        or candidate.name != _DIST
        or not candidate.is_relative_to(directory)
        or candidate.is_relative_to(directory / "backup")
        or launcher.is_relative_to(directory)
    ):
        raise ValueError("Unsupported uv installation or update layout.")
    if _WINDOWS:
        if launcher.name != "pdomain-ocr.exe" or launcher.resolve() != launcher:
            raise ValueError("Unsupported retained Windows launcher.")
    elif launcher.name != "pdomain-ocr" or launcher.resolve() != live / "bin" / launcher.name:
        raise ValueError("Unsupported retained POSIX launcher.")
    if workspace.st_dev != live.parent.stat().st_dev or (
        workspace.st_dev != candidate.parent.stat().st_dev
    ):
        raise ValueError("The update and tool directories must share a filesystem.")


def _environment_identity(path: Path) -> _Identity | None:
    try:
        directory = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISDIR(directory.st_mode):
        raise ValueError(f"The update environment changed at {path}")
    receipt = path / _RECEIPT
    receipt_info = receipt.lstat()
    if not stat.S_ISREG(receipt_info.st_mode):
        raise ValueError(f"The update receipt changed at {receipt}")
    digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
    receipt_identity = f"{receipt_info.st_ino}:{receipt_info.st_mtime_ns}:{digest}"
    return _Identity(directory.st_dev, directory.st_ino, receipt_identity)


def _launcher_identity(path: Path) -> _Identity:
    info = path.lstat()
    if _WINDOWS:
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"The retained launcher changed at {path}")
        return _Identity(info.st_dev, info.st_ino, hashlib.sha256(path.read_bytes()).hexdigest())
    if not stat.S_ISLNK(info.st_mode):
        raise ValueError(f"The retained launcher changed at {path}")
    return _Identity(info.st_dev, info.st_ino, os.fspath(path.readlink()))


def _write_phase(transaction: _Transaction, phase: str, *, initial: bool = False) -> None:
    journal = transaction.journal
    data = {
        "phase": phase,
        "status": phase if phase in ("prepared", "updated", "rolled back") else "recovery needed",
        "live": str(transaction.live),
        "candidate": str(transaction.candidate),
        "launcher": str(transaction.launcher),
        "previous_version": transaction.previous_version,
        "version": transaction.version,
        "old_identity": transaction.old_identity,
        "new_identity": transaction.new_identity,
        "launcher_identity": transaction.launcher_identity,
    }
    descriptor, name = tempfile.mkstemp(dir=journal.parent, prefix=".transaction-")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if initial and not _WINDOWS:
            os.link(temporary, journal)
        else:
            _rename(temporary, journal, replace=not initial)
        _sync_directory(journal.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _read_identity(value: object) -> _Identity:
    if isinstance(value, list):
        parts = cast("list[object]", value)
        if len(parts) != 3:
            raise ValueError("The update journal contains an invalid identity.")
        device, inode, fingerprint = parts
        if isinstance(device, int) and isinstance(inode, int) and isinstance(fingerprint, str):
            return _Identity(device, inode, fingerprint)
    raise ValueError("The update journal contains an invalid identity.")


def _version(value: str) -> str:
    if _VERSION.fullmatch(value) is None:
        raise ValueError(f"Invalid OCR CLI version: {value!r}")
    return value


def _read_journal(journal: Path) -> tuple[_Transaction, str]:
    if not stat.S_ISREG(journal.lstat().st_mode):
        raise ValueError("The update journal must be a regular file.")
    value = cast("object", json.loads(journal.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise TypeError("The update journal must contain an object.")
    data = cast("dict[object, object]", value)

    def string(key: str) -> str:
        item = data.get(key)
        if not isinstance(item, str):
            raise TypeError(f"Invalid or missing journal field: {key}")
        return item

    phase = string("phase")
    if phase not in _LAYOUTS:
        raise ValueError(f"Unknown update phase: {phase}")
    transaction = _Transaction(
        journal,
        Path(string("live")),
        Path(string("candidate")),
        Path(string("launcher")),
        _version(string("previous_version")),
        _version(string("version")),
        _read_identity(data.get("old_identity")),
        _read_identity(data.get("new_identity")),
        _read_identity(data.get("launcher_identity")),
    )
    _validate_paths(journal, transaction.live, transaction.candidate, transaction.launcher)
    return transaction, phase


def prepare_transaction(
    directory: Path,
    live: Path,
    candidate: Path,
    launcher: Path,
    *,
    previous_version: str,
    version: str,
) -> Path:
    """Record the prepared environment and the installation it may replace."""
    _require_platform()
    journal = directory / _JOURNAL
    _validate_paths(journal, live, candidate, launcher)
    old_identity = _environment_identity(live)
    new_identity = _environment_identity(candidate)
    if old_identity is None or new_identity is None or old_identity == new_identity:
        raise ValueError("The live and candidate environments must exist as distinct directories.")
    transaction = _Transaction(
        journal,
        live,
        candidate,
        launcher,
        _version(previous_version),
        _version(version),
        old_identity,
        new_identity,
        _launcher_identity(launcher),
    )
    _ = _validate_state(transaction, "prepared")
    _sync_directory(directory.parent)
    _write_phase(transaction, "prepared", initial=True)
    return journal


def _validate_state(transaction: _Transaction, phase: str) -> _Layout:
    if _launcher_identity(transaction.launcher) != transaction.launcher_identity:
        raise ValueError(f"The retained launcher changed at {transaction.launcher}")

    def identify(path: Path) -> _Slot:
        identity = _environment_identity(path)
        if identity is None:
            return "empty"
        if identity == transaction.old_identity:
            return "old"
        if identity == transaction.new_identity:
            return "new"
        raise ValueError(f"The installation changed at {path}. The worker will leave it in place.")

    layout = (
        identify(transaction.live),
        identify(transaction.candidate),
        identify(transaction.backup),
    )
    if layout not in _LAYOUTS[phase]:
        raise ValueError(f"The installation changed during update phase {phase}: {layout}")
    return layout


def _launcher_environment() -> dict[str, str]:
    environment = dict(os.environ)
    _ = environment.pop("PYTHONPATH", None)
    _ = environment.pop("PYTHONHOME", None)
    return environment


def _probe(launcher: Path, version: str, *, runtime: bool = False) -> None:
    option, expected = (
        ("--check-runtime", f"pdomain-ocr runtime OK {version}")
        if runtime
        else ("--version", f"pdomain-ocr {version}")
    )
    environment = _launcher_environment()
    environment.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        UV_OFFLINE="1",
        PDOMAIN_OCR_UPDATE_PROBE="1",
    )
    completed = subprocess.run(  # noqa: S603  # Validated absolute launcher; fixed probe options.
        [str(launcher), option],
        env=environment,
        cwd=launcher.parent,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=_PROBE_TIMEOUT,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip() != expected:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ValueError(
            f"OCR launcher {option} failed (exit {completed.returncode}, expected {expected!r}): {detail}"
        )


def _rollback(transaction: _Transaction, layout: _Layout) -> _Outcome:
    if layout == _INSTALLED:
        _write_phase(transaction, "deactivating")
        _move(transaction.live, transaction.candidate)
    if layout != _READY:
        _write_phase(transaction, "restoring")
        _move(transaction.backup, transaction.live)
    _probe(transaction.launcher, transaction.previous_version)
    _write_phase(transaction, "rolled back")
    return "rolled back"


def _activate(transaction: _Transaction) -> _Outcome:
    receipt = (transaction.live / _RECEIPT).read_text(encoding="utf-8")
    metadata = cast("object", tomllib.loads(receipt))
    match metadata:
        case {
            "tool": {
                "entrypoints": [
                    {"name": "pdomain-ocr", "from": "pdomain-ocr-cli", "install-path": str(path)}
                ]
            }
        } if Path(path).is_absolute() and Path(path) == transaction.launcher:
            pass
        case _:
            raise ValueError("The current uv installation has unsupported launchers.")
    _probe(transaction.launcher, transaction.previous_version)
    for directory in (transaction.live.parent, transaction.candidate.parent):
        _sync_directory(directory)
    try:
        _write_phase(transaction, "parking")
        _move(transaction.live, transaction.backup)
        _write_phase(transaction, "activating")
        _move(transaction.candidate, transaction.live)
        _probe(transaction.launcher, transaction.version)
        _probe(transaction.launcher, transaction.version, runtime=True)
    except (OSError, TypeError, ValueError, subprocess.SubprocessError) as error:
        _ = sys.stderr.write(f"Candidate activation failed: {error}\n")
        _, phase = _read_journal(transaction.journal)
        layout = _validate_state(transaction, phase)
        return _rollback(transaction, layout)
    _write_phase(transaction, "updated")
    return "updated"


def _confirm_updated(transaction: _Transaction, layout: _Layout) -> _Outcome:
    try:
        _probe(transaction.launcher, transaction.version)
        _probe(transaction.launcher, transaction.version, runtime=True)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        _ = sys.stderr.write(f"Installed candidate no longer passes its health check: {error}\n")
        return _rollback(transaction, layout)
    return "updated"


def execute(journal: Path, *, recover: bool = False) -> _Outcome:
    """Serialize activation and recovery with other uv tool directory operations."""
    _require_platform()
    transaction, _ = _read_journal(journal)
    with _lock(transaction.live.parent), _installation_lock(transaction.live, exclusive=True):
        locked, phase = _read_journal(journal)
        if locked != transaction:
            raise ValueError("The update journal changed while waiting for uv's lock.")
        layout = _validate_state(locked, phase)
        if phase == "updated":
            return _confirm_updated(locked, layout) if recover else "updated"
        if phase == "rolled back":
            _probe(locked.launcher, locked.previous_version)
            return "rolled back"
        if recover:
            return _rollback(locked, layout)
        if phase != "prepared":
            raise ValueError("An interrupted update needs the recovery command before retrying.")
        return _activate(locked)


def _prefetch(journal: Path) -> None:
    try:
        transaction, _ = _read_journal(journal)
        launcher = transaction.launcher
        _ = subprocess.run(  # noqa: S603  # Validated absolute launcher; fixed command.
            [str(launcher), "download-models"],
            env=_launcher_environment(),
            cwd=launcher.parent,
            stdin=subprocess.DEVNULL,
            timeout=_PREFETCH_TIMEOUT,
            check=True,
        )
    except (OSError, TypeError, ValueError, subprocess.SubprocessError) as error:
        _ = sys.stderr.write(f"Model prefetch could not finish: {error}\n")


def main() -> int:
    """Run the transaction from a Python interpreter outside either environment."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("journal", type=Path)
    _ = parser.add_argument("--recover", action="store_true")
    args = _Arguments()
    _ = parser.parse_args(namespace=args)
    try:
        result = execute(args.journal, recover=args.recover)
    except (OSError, TypeError, ValueError, subprocess.SubprocessError) as error:
        backup = args.journal.parent / "backup"
        _ = sys.stderr.write(
            f"Recovery needed: {error}\nJournal: {args.journal}\nParked environment: {backup}\n"
        )
        return 2
    _ = sys.stdout.write(f"OCR CLI {result}.\n")
    _ = sys.stdout.flush()
    if result == "updated" and not args.recover:
        _prefetch(args.journal)
    return int(result == "rolled back" and not args.recover)


if __name__ == "__main__":
    raise SystemExit(main())
