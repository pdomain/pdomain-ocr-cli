from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pdomain_ocr_cli import _update_worker as worker

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX transaction proof")


def _environment(path: Path, version: str, *, healthy: bool = True) -> None:
    executable = path / "bin" / "pdomain-ocr"
    executable.parent.mkdir(parents=True)
    _ = (path / "uv-receipt.toml").write_text(f'version = "{version}"\n', encoding="utf-8")
    contents = f"""#!/bin/sh
case "$1" in
    --version) echo 'pdomain-ocr {version}';;
    --check-runtime)
        [ "$HF_HUB_OFFLINE/$TRANSFORMERS_OFFLINE" = 1/1 ] || exit 4
        echo 'pdomain-ocr runtime OK {version}'
        exit {0 if healthy else 3};;
    download-models) exit 0;;
    *) exit 2;;
esac
"""
    _ = executable.write_text(contents, encoding="utf-8")
    executable.chmod(0o700)


@pytest.fixture
def paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    directory = tmp_path / "update"
    directory.mkdir(mode=0o700)
    live = tmp_path / "tools" / "pdomain-ocr-cli"
    candidate = directory / "stage" / "pdomain-ocr-cli"
    launcher = tmp_path / "bin" / "pdomain-ocr"
    launcher.parent.mkdir()
    launcher.symlink_to(live / "bin" / "pdomain-ocr")
    _environment(live, "1.0.0")
    receipt = live / "uv-receipt.toml"
    _ = receipt.write_text(
        receipt.read_text()
        + '[tool]\nentrypoints = [{ name = "pdomain-ocr", from = "pdomain-ocr-cli", '
        + f"install-path = {json.dumps(str(launcher))}"
        + " }]\n",
        encoding="utf-8",
    )
    return directory, live, candidate, launcher


def _prepare(
    paths: tuple[Path, Path, Path, Path], *, healthy: bool = True
) -> tuple[Path, Path, Path, Path]:
    directory, live, candidate, launcher = paths
    worker.make_workspace_private(directory)
    _environment(candidate, "2.0.0", healthy=healthy)
    journal = worker.prepare_transaction(
        directory, live, candidate, launcher, previous_version="1.0.0", version="2.0.0"
    )
    return journal, live, candidate, launcher


def test_activation_refuses_extra_retained_launchers(paths: tuple[Path, Path, Path, Path]) -> None:
    directory, live, candidate, launcher = paths
    old_inode = live.stat().st_ino
    receipt = live / "uv-receipt.toml"
    _ = receipt.write_text(
        '[tool]\nentrypoints = [{ name = "other-entry" }, { name = "pdomain-ocr", '
        + f'from = "pdomain-ocr-cli", install-path = {json.dumps(str(launcher))}'
        + " }]\n",
        encoding="utf-8",
    )
    _environment(candidate, "2.0.0")
    journal = worker.prepare_transaction(
        directory, live, candidate, launcher, previous_version="1.0.0", version="2.0.0"
    )

    with pytest.raises(ValueError, match="unsupported launchers"):
        _ = worker.execute(journal)

    assert live.stat().st_ino == old_inode
    assert not (directory / "backup").exists()


def test_activation_verifies_public_launcher(paths: tuple[Path, Path, Path, Path]) -> None:
    journal, live, candidate, launcher = _prepare(paths)
    launcher_inode = launcher.lstat().st_ino
    assert worker.execute(journal) == "updated"
    assert "2.0.0" in (live / "uv-receipt.toml").read_text()
    assert not candidate.exists()
    assert launcher.lstat().st_ino == launcher_inode
    assert worker.execute(journal) == "updated"
    assert worker.execute(journal, recover=True) == "updated"


def test_failed_installed_probe_restores_previous_environment(
    paths: tuple[Path, Path, Path, Path],
) -> None:
    journal, live, candidate, launcher = _prepare(paths, healthy=False)
    original = live.stat().st_ino
    assert worker.execute(journal) == "rolled back"
    assert live.stat().st_ino == original
    assert launcher.is_file()
    assert candidate.is_dir()
    assert worker.execute(journal, recover=True) == "rolled back"


class _SimulatedStop(BaseException):
    pass


@pytest.mark.parametrize("after", [1, 2])
def test_recovery_after_rename_before_next_journal_write(
    paths: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch, after: int
) -> None:
    journal, live, candidate, _ = _prepare(paths)
    original = live.stat().st_ino
    rename = Path.rename
    count = 0

    def move_then_stop(source: Path, destination: Path) -> Path:
        nonlocal count
        moved = rename(source, destination)
        count += 1
        if count == after:
            raise _SimulatedStop
        return moved

    with monkeypatch.context() as context:
        context.setattr(Path, "rename", move_then_stop)
        with pytest.raises(_SimulatedStop):
            _ = worker.execute(journal)

    assert json.loads(journal.read_text())["status"] == "recovery needed"
    with pytest.raises(ValueError, match="interrupted update"):
        _ = worker.execute(journal)
    assert worker.execute(journal, recover=True) == "rolled back"
    assert live.stat().st_ino == original
    assert candidate.is_dir()


def test_recovery_keeps_external_install_and_parked_backup(
    paths: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, live, _, _ = _prepare(paths)
    original = live.stat().st_ino
    rename = Path.rename

    def move_then_stop(source: Path, destination: Path) -> None:
        _ = rename(source, destination)
        raise _SimulatedStop

    with monkeypatch.context() as context:
        context.setattr(Path, "rename", move_then_stop)
        with pytest.raises(_SimulatedStop):
            _ = worker.execute(journal)
    _environment(live, "9.0.0")
    external = live.stat().st_ino

    with pytest.raises(ValueError, match="changed"):
        _ = worker.execute(journal, recover=True)

    assert live.stat().st_ino == external
    assert (journal.parent / "backup").stat().st_ino == original


def test_copied_worker_recovers_after_process_termination(
    paths: tuple[Path, Path, Path, Path],
) -> None:
    journal, live, candidate, launcher = _prepare(paths)
    original = live.stat().st_ino
    copied_worker = journal.with_name("worker.py")
    _ = shutil.copyfile(worker.__file__, copied_worker)
    fault = journal.with_name("interrupt.py")
    _ = fault.write_text(
        """import os
import runpy
import sys
from pathlib import Path

script, journal = sys.argv[1:]
namespace = runpy.run_path(script)["execute"].__globals__
move = namespace["_move"]
def stop_after_move(source, destination):
    move(source, destination)
    os._exit(76)
namespace["_move"] = stop_after_move
namespace["execute"](Path(journal))
""",
        encoding="utf-8",
    )
    process = subprocess.run(
        [sys.executable, "-I", str(fault), str(copied_worker), str(journal)],
        check=False,
        timeout=15,
    )
    assert process.returncode == 76
    assert not live.exists()
    assert not launcher.exists()
    assert json.loads(journal.read_text())["status"] == "recovery needed"

    recovered = subprocess.run(
        [sys.executable, "-I", str(copied_worker), str(journal), "--recover"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert recovered.returncode == 0, recovered.stderr
    assert recovered.stdout == "OCR CLI rolled back.\n"
    assert live.stat().st_ino == original
    assert candidate.is_dir()


def test_recovery_rechecks_candidate_after_recorded_success(
    paths: tuple[Path, Path, Path, Path],
) -> None:
    journal, live, _, _ = _prepare(paths)
    original = live.stat().st_ino
    assert worker.execute(journal) == "updated"
    (live / "bin" / "pdomain-ocr").unlink()
    assert worker.execute(journal, recover=True) == "rolled back"
    assert live.stat().st_ino == original


def test_recovery_before_activation_is_safe(paths: tuple[Path, Path, Path, Path]) -> None:
    journal, live, _, _ = _prepare(paths)
    original = live.stat().st_ino
    assert worker.execute(journal, recover=True) == "rolled back"
    assert live.stat().st_ino == original


def test_old_version_is_verified_before_swap(paths: tuple[Path, Path, Path, Path]) -> None:
    directory, live, candidate, launcher = paths
    _environment(candidate, "2.0.0")
    journal = worker.prepare_transaction(
        directory, live, candidate, launcher, previous_version="8.0.0", version="2.0.0"
    )
    with pytest.raises(ValueError, match="--version failed"):
        _ = worker.execute(journal)
    assert not (directory / "backup").exists()
    assert candidate.is_dir()


def test_regular_ocr_readers_share_lock_without_locking_uv_tools(
    paths: tuple[Path, Path, Path, Path],
) -> None:
    _, live, _, _ = paths
    with (
        worker.hold_installation(live),
        worker.hold_installation(live),
        worker._lock(live.parent),
    ):
        assert live.is_dir()


@pytest.mark.parametrize("recover", [False, True])
def test_readers_prevent_activation_and_recovery_until_they_release(
    paths: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch, recover: bool
) -> None:
    journal, live, candidate, _ = _prepare(paths)
    monkeypatch.setattr(worker, "_LOCK_TIMEOUT", 0.0)
    with (
        worker.hold_installation(live),
        pytest.raises(TimeoutError, match="pdomain-ocr installation"),
    ):
        _ = worker.execute(journal, recover=recover)
    assert json.loads(journal.read_text())["phase"] == "prepared"
    assert candidate.is_dir()
    assert not (journal.parent / "backup").exists()
    assert worker.execute(journal, recover=recover) == ("rolled back" if recover else "updated")


def test_new_ocr_run_fails_while_update_has_exclusive_lock(
    paths: tuple[Path, Path, Path, Path],
) -> None:
    _, live, _, _ = paths
    with (
        worker._installation_lock(live, exclusive=True),
        pytest.raises(TimeoutError, match="pdomain-ocr installation"),
        worker.hold_installation(live),
    ):
        pytest.fail("OCR cannot begin during activation")


@pytest.fixture
def native_api(monkeypatch: pytest.MonkeyPatch) -> dict[str, Mock]:
    functions = {
        name: Mock(return_value=1)
        for name in (
            "CloseHandle",
            "ConvertStringSecurityDescriptorToSecurityDescriptorW",
            "CreateFileW",
            "FlushFileBuffers",
            "LocalFree",
            "LockFileEx",
            "MoveFileExW",
            "SetFileSecurityW",
        )
    }
    monkeypatch.setattr(worker, "_WINDOWS", True)
    monkeypatch.setattr(
        worker.ctypes, "WinDLL", Mock(return_value=SimpleNamespace(**functions)), raising=False
    )
    monkeypatch.setattr(
        worker.ctypes,
        "WinError",
        Mock(side_effect=lambda code: OSError("native failure", code)),
        raising=False,
    )
    monkeypatch.setattr(worker.ctypes, "get_last_error", Mock(return_value=87), raising=False)
    return functions


def test_windows_adapter_requests_write_through_and_flushes(
    tmp_path: Path, native_api: dict[str, Mock]
) -> None:
    worker.make_workspace_private(tmp_path)
    assert native_api["SetFileSecurityW"].call_args.args[:2] == (str(tmp_path), 0x80000004)
    native_api["LocalFree"].assert_called_once()
    destination = tmp_path / "second"
    worker._move(tmp_path / "first", destination)
    native_api["MoveFileExW"].assert_called_once_with(str(tmp_path / "first"), str(destination), 8)
    native_api["FlushFileBuffers"].assert_called_once_with(1)
    native_api["CloseHandle"].assert_called_once_with(1)


@pytest.mark.parametrize(
    ("function", "result", "cleanup"),
    [
        ("ConvertStringSecurityDescriptorToSecurityDescriptorW", 0, None),
        ("SetFileSecurityW", 0, "LocalFree"),
        ("MoveFileExW", 0, None),
        ("CreateFileW", worker.ctypes.c_void_p(-1).value, None),
        ("FlushFileBuffers", 0, "CloseHandle"),
    ],
)
def test_windows_adapter_reports_failures(
    tmp_path: Path,
    native_api: dict[str, Mock],
    function: str,
    result: int | None,
    cleanup: str | None,
) -> None:
    native_api[function].return_value = result
    if function in ("ConvertStringSecurityDescriptorToSecurityDescriptorW", "SetFileSecurityW"):
        with pytest.raises(OSError, match="native failure") as raised:
            worker.make_workspace_private(tmp_path)
    else:
        with pytest.raises(OSError, match="native failure") as raised:
            worker._move(tmp_path / "first", tmp_path / "second")
    assert raised.value.args == ("native failure", 87)
    if cleanup is not None:
        native_api[cleanup].assert_called_once()


@pytest.mark.parametrize("code", [None, errno.EACCES, errno.EINVAL])
def test_windows_byte_lock_normalizes_only_contention(
    monkeypatch: pytest.MonkeyPatch, code: int | None
) -> None:
    lock = Mock(side_effect=None if code is None else OSError(code, "lock failed"))
    monkeypatch.setattr(worker, "_WINDOWS", True)
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(locking=lock, LK_NBLCK=2))
    if code is None:
        worker._try_lock(11)
    else:
        with pytest.raises(BlockingIOError if code == errno.EACCES else OSError):
            worker._try_lock(11)
    lock.assert_called_once_with(11, 2, 1)


@pytest.mark.parametrize(("exclusive", "flags"), [(False, 1), (True, 3)])
def test_windows_ocr_lock_selects_shared_or_exclusive_mode(
    native_api: dict[str, Mock], monkeypatch: pytest.MonkeyPatch, exclusive: bool, flags: int
) -> None:
    handle = Mock(return_value=19)
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(get_osfhandle=handle))
    worker._try_installation_lock(11, exclusive=exclusive)
    handle.assert_called_once_with(11)
    assert native_api["LockFileEx"].call_args.args[:5] == (19, flags, 0, 1, 0)


@pytest.mark.parametrize(("code", "expected"), [(33, BlockingIOError), (6, OSError)])
def test_windows_ocr_lock_normalizes_only_lock_violation(
    native_api: dict[str, Mock],
    monkeypatch: pytest.MonkeyPatch,
    code: int,
    expected: type[OSError],
) -> None:
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(get_osfhandle=lambda _: 19))
    error = OSError("Windows error")
    error.winerror = code
    monkeypatch.setattr(worker, "_windows_error", lambda: error)
    native_api["LockFileEx"].return_value = 0
    with pytest.raises(expected) as raised:
        worker._try_installation_lock(11, exclusive=True)
    assert type(raised.value) is expected


def test_lock_wait_retries_once_and_times_out(
    paths: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    import fcntl

    journal, live, _, _ = _prepare(paths)
    lock = live.parent / ".lock"
    with lock.open("wb") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        monkeypatch.setattr(worker, "_LOCK_TIMEOUT", 0.01)
        sleep = Mock()
        monkeypatch.setattr(worker.time, "sleep", sleep)
        clock = Mock(side_effect=[0.0, 0.001, 0.011])
        monkeypatch.setattr(worker.time, "monotonic", clock)
        with pytest.raises(TimeoutError, match="waiting for uv"):
            _ = worker.execute(journal)
        sleep.assert_called_once()
    assert live.is_dir()
    assert not (journal.parent / "backup").exists()


def test_lock_refuses_nonregular_file(
    paths: tuple[Path, Path, Path, Path],
) -> None:
    journal, live, _, _ = _prepare(paths)
    os.mkfifo(live.parent / ".lock")
    with pytest.raises(ValueError, match="Unsupported uv lock"):
        _ = worker.execute(journal)


def test_lock_refuses_replaced_inode(
    paths: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, live, _, _ = _prepare(paths)
    lock = live.parent / ".lock"

    def replace_lock(descriptor: int) -> None:
        assert descriptor >= 0
        lock.unlink()
        lock.touch()

    monkeypatch.setattr(worker, "_try_lock", replace_lock)
    with pytest.raises(ValueError, match="lock changed"):
        _ = worker.execute(journal)


def test_windows_disallows_symlink_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker, "_WINDOWS", True)
    (tmp_path / ".lock").symlink_to(tmp_path / "another-lock")
    with pytest.raises(ValueError, match="Unsupported uv lock"), worker._lock(tmp_path):
        pytest.fail("A symlink cannot be used as a lock")


def test_windows_journal_writes_and_lock_open(
    tmp_path: Path, native_api: dict[str, Mock], monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "work"
    directory.mkdir()
    live = tmp_path / "tools" / "pdomain-ocr-cli"
    candidate = directory / "stage" / "pdomain-ocr-cli"
    _environment(live, "1.0.0")
    _environment(candidate, "2.0.0")
    launcher = tmp_path / "pdomain-ocr.exe"
    launcher.touch()
    lock = Mock()
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(locking=lock, LK_NBLCK=2))

    def move(source: str, destination: str, flags: int) -> int:
        _ = Path(source).replace(destination) if flags & 1 else Path(source).rename(destination)
        return 1

    native_api["MoveFileExW"].side_effect = move
    journal = worker.prepare_transaction(
        directory, live, candidate, launcher, previous_version="1.0.0", version="2.0.0"
    )
    native_api["MoveFileExW"].assert_called_once()
    assert native_api["MoveFileExW"].call_args.args[-1] == 8
    with worker._lock(live.parent):
        lock.assert_called_once()
    assert journal.is_file()


def test_rename_within_one_directory_and_destination_conflict(tmp_path: Path) -> None:
    source = tmp_path / "old"
    source.touch()
    destination = tmp_path / "new"
    worker._move(source, destination)
    assert destination.exists()
    source.touch()
    with pytest.raises(FileExistsError, match="already exists"):
        worker._move(source, destination)


def test_refuses_journal_changed_while_waiting_for_lock(
    paths: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, _, _, _ = _prepare(paths)

    def change_expected_version(descriptor: int) -> None:
        assert descriptor >= 0
        document = json.loads(journal.read_text())
        document["version"] = "3.0.0"
        _ = journal.write_text(json.dumps(document))

    monkeypatch.setattr(worker, "_try_lock", change_expected_version)
    with pytest.raises(ValueError, match="journal changed while waiting"):
        _ = worker.execute(journal)


def test_unsupported_platform_refuses_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(worker, "os", SimpleNamespace(name="unsupported"))
    with pytest.raises(ValueError, match="does not support durable"):
        _ = worker.execute(tmp_path / "transaction.json")


def test_prefetch_runs_without_uv_lock(
    paths: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import fcntl

    journal, live, _, _ = _prepare(paths)
    monkeypatch.setattr(sys, "argv", ["worker", str(journal)])

    def check_lock_released(journal_path: Path) -> None:
        assert journal_path == journal
        with (live.parent / ".lock").open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    prefetch = Mock(side_effect=check_lock_released)
    monkeypatch.setattr(worker, "_prefetch", prefetch)
    assert worker.main() == 0
    prefetch.assert_called_once_with(journal)
    assert "OCR CLI updated" in capsys.readouterr().out


def test_prefetch_failure_does_not_reject_verified_install(
    paths: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    journal, live, _, _ = _prepare(paths)
    monkeypatch.setattr(sys, "argv", ["worker", str(journal)])
    staged_launcher = paths[2] / "bin" / "pdomain-ocr"
    _ = staged_launcher.write_text(
        staged_launcher.read_text().replace("download-models) exit 0", "download-models) exit 3")
    )
    assert worker.main() == 0
    assert "Model prefetch could not finish" in capsys.readouterr().err
    assert "2.0.0" in (live / "uv-receipt.toml").read_text()


def test_worker_main_reports_unavailable_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["worker", str(tmp_path / "transaction.json"), "--recover"])
    assert worker.main() == 2
    assert "Recovery needed" in capsys.readouterr().err


@pytest.mark.parametrize(("healthy", "exit_code"), [(True, 0), (False, 1)])
def test_worker_main_prints_outcome(
    paths: tuple[Path, Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    healthy: bool,
    exit_code: int,
) -> None:
    journal, _, _, _ = _prepare(paths, healthy=healthy)
    monkeypatch.setattr(sys, "argv", ["worker", str(journal)])
    assert worker.main() == exit_code
    assert capsys.readouterr().out == (
        "OCR CLI updated.\n" if healthy else "OCR CLI rolled back.\n"
    )


def test_explicit_recovery_rechecks_health_without_prefetch(
    paths: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, _, _, _ = _prepare(paths)
    assert worker.execute(journal) == "updated"
    monkeypatch.setattr(sys, "argv", ["worker", str(journal), "--recover"])
    prefetch = Mock()
    monkeypatch.setattr(worker, "_prefetch", prefetch)
    assert worker.main() == 0
    prefetch.assert_not_called()
