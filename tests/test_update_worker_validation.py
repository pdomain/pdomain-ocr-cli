from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pdomain_ocr_cli import _update_worker as worker

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX fixture paths")


@pytest.fixture
def layout(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    workspace = tmp_path / "transaction"
    workspace.mkdir(mode=0o700)
    live = tmp_path / "tools" / "pdomain-ocr-cli"
    candidate = workspace / "staged" / "pdomain-ocr-cli"
    for path in (live, candidate):
        path.mkdir(parents=True)
        (path / "uv-receipt.toml").touch()
    launcher = tmp_path / "bin" / "pdomain-ocr"
    launcher.parent.mkdir()
    launcher.symlink_to(live / "bin" / launcher.name)
    return workspace, live, candidate, launcher


def _record(layout: tuple[Path, Path, Path, Path]) -> Path:
    return worker.prepare_transaction(*layout, previous_version="1.0.0", version="2.0.0")


@pytest.mark.parametrize(
    ("data", "error", "message"),
    [
        ([], TypeError, "contain an object"),
        ({"phase": None}, TypeError, "journal field"),
        ({"phase": "unknown"}, ValueError, "Unknown update phase"),
    ],
)
def test_invalid_journal_stops_before_activation(
    layout: tuple[Path, Path, Path, Path], data: object, error: type[Exception], message: str
) -> None:
    journal = _record(layout)
    _ = journal.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(error, match=message):
        _ = worker.execute(journal, recover=True)


@pytest.mark.parametrize("identity", [None, [], ["fake", 2, "abc"], [1, "fake", "abc"], [1, 2, 3]])
def test_invalid_environment_identity_stops_recovery(
    layout: tuple[Path, Path, Path, Path], identity: object
) -> None:
    journal = _record(layout)
    data = json.loads(journal.read_text(encoding="utf-8"))
    data["old_identity"] = identity
    _ = journal.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid identity"):
        _ = worker.execute(journal, recover=True)


def test_journal_must_be_a_regular_file(layout: tuple[Path, Path, Path, Path]) -> None:
    journal = _record(layout)
    renamed = journal.with_name("former.json")
    _ = journal.rename(renamed)
    journal.symlink_to(renamed)

    with pytest.raises(ValueError, match="regular file"):
        _ = worker.execute(journal)


@pytest.mark.parametrize(
    ("problem", "message"),
    [
        ("relative", "canonical"),
        ("private", "must be private"),
        ("owner", "must be private"),
        ("name", "Unsupported uv"),
        ("launcher", "Unsupported retained POSIX"),
        ("missing", "distinct directories"),
        ("old-missing", "distinct directories"),
        ("receipt", "receipt changed"),
        ("environment", "environment changed"),
        ("version", "Invalid OCR CLI version"),
        ("filesystem", "share a filesystem"),
    ],
)
def test_prepare_rejects_unsafe_layout(
    layout: tuple[Path, Path, Path, Path],
    problem: str,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, live, candidate, launcher = layout
    version = "2.0.0"
    if problem == "relative":
        live = Path("relative")
    elif problem == "private":
        workspace.chmod(0o755)
    elif problem == "owner":
        monkeypatch.setattr(worker.os, "geteuid", lambda: workspace.stat().st_uid + 1)
    elif problem == "name":
        candidate = candidate.with_name("other-tool")
    elif problem == "launcher":
        launcher.unlink()
        launcher.touch()
    elif problem == "missing":
        _ = candidate.rename(candidate.with_name("absent"))
    elif problem == "old-missing":
        _ = live.rename(live.with_name("absent"))
    elif problem == "receipt":
        receipt = candidate / "uv-receipt.toml"
        receipt.unlink()
        receipt.mkdir()
    elif problem == "environment":
        _ = candidate.rename(candidate.with_name("absent"))
        candidate.touch()
    elif problem == "version":
        version = "invalid version"
    else:
        original_stat = Path.stat

        def separate_drive(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
            result = original_stat(path, follow_symlinks=follow_symlinks)
            if path == candidate.parent:
                parts = list(result)
                parts[2] += 1
                return os.stat_result(parts)
            return result

        monkeypatch.setattr(Path, "stat", separate_drive)

    with pytest.raises(ValueError, match=message):
        _ = worker.prepare_transaction(
            workspace, live, candidate, launcher, previous_version="1.0.0", version=version
        )


def test_recovery_refuses_changed_posix_launcher(
    layout: tuple[Path, Path, Path, Path],
) -> None:
    journal = _record(layout)
    _, live, _, launcher = layout
    _ = launcher.rename(launcher.with_name("moved"))
    launcher.symlink_to(live / "bin" / launcher.name)

    with pytest.raises(ValueError, match="retained launcher changed"):
        _ = worker.execute(journal, recover=True)


def test_recovery_refuses_state_inconsistent_with_phase(
    layout: tuple[Path, Path, Path, Path],
) -> None:
    journal = _record(layout)
    workspace, live, _, _ = layout
    _ = live.rename(workspace / "backup")

    with pytest.raises(ValueError, match="changed during update phase"):
        _ = worker.execute(journal, recover=True)


@pytest.mark.parametrize("problem", ["none", "wrong-name", "symlink"])
def test_windows_launcher_path_must_be_canonical(
    layout: tuple[Path, Path, Path, Path], problem: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, live, candidate, launcher = layout
    monkeypatch.setattr(worker, "_WINDOWS", True)
    executable = launcher.with_suffix(".exe")
    executable.touch()
    if problem == "none":
        worker._validate_paths(workspace / "transaction.json", live, candidate, executable)
        return
    if problem == "symlink":
        executable.unlink()
        executable.symlink_to(launcher)
    else:
        executable = launcher
    with pytest.raises(ValueError, match="Unsupported retained Windows"):
        worker._validate_paths(workspace / "transaction.json", live, candidate, executable)


def test_windows_launcher_identity_checks_executable_bytes(
    layout: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, launcher = layout
    monkeypatch.setattr(worker, "_WINDOWS", True)
    with pytest.raises(ValueError, match="retained launcher changed"):
        _ = worker._launcher_identity(launcher)
    launcher.unlink()
    _ = launcher.write_bytes(b"original")
    original = worker._launcher_identity(launcher)
    _ = launcher.write_bytes(b"replacement")
    assert worker._launcher_identity(launcher) != original


def test_posix_launcher_identity_refuses_regular_file(
    layout: tuple[Path, Path, Path, Path],
) -> None:
    _, _, _, launcher = layout
    launcher.unlink()
    launcher.touch()

    with pytest.raises(ValueError, match="retained launcher changed"):
        _ = worker._launcher_identity(launcher)


def test_prepare_refuses_identical_environment_identities(
    layout: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = worker._Identity(1, 2, "same")
    monkeypatch.setattr(worker, "_environment_identity", lambda path: identity)

    with pytest.raises(ValueError, match="distinct directories"):
        _ = _record(layout)


def _make_live_launchable(live: Path, launcher: Path) -> None:
    installed = live / "bin" / launcher.name
    installed.parent.mkdir()
    _ = installed.write_text("#!/bin/sh\nprintf 'pdomain-ocr 1.0.0\\n'\n", encoding="utf-8")
    installed.chmod(0o700)
    _ = (live / "uv-receipt.toml").write_text(
        '[tool]\nentrypoints = [{ name = "pdomain-ocr", from = "pdomain-ocr-cli", '
        + f"install-path = {json.dumps(str(launcher))}"
        + " }]\n",
        encoding="utf-8",
    )


def test_failed_restore_preserves_backup_for_recovery(
    layout: tuple[Path, Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, live, candidate, launcher = layout
    _make_live_launchable(live, launcher)
    original = live.stat().st_ino
    journal = _record(layout)
    move = worker._move
    backup = workspace / "backup"

    def deny_restore(source: Path, destination: Path) -> None:
        if source == backup:
            raise PermissionError("The old environment is temporarily locked")
        move(source, destination)

    with monkeypatch.context() as context:
        context.setattr(worker, "_move", deny_restore)
        with pytest.raises(PermissionError, match="temporarily locked"):
            _ = worker.execute(journal)

    assert json.loads(journal.read_text())["status"] == "recovery needed"
    assert backup.stat().st_ino == original
    assert not live.exists()
    assert candidate.is_dir()
    assert worker.execute(journal, recover=True) == "rolled back"
    assert live.stat().st_ino == original


@pytest.mark.parametrize("moves", [1, 2])
def test_recovery_command_restores_after_worker_process_exit(
    layout: tuple[Path, Path, Path, Path], moves: int
) -> None:
    workspace, live, candidate, launcher = layout
    _make_live_launchable(live, launcher)
    old_inode = live.stat().st_ino
    journal = _record(layout)
    copied = workspace / "worker.py"
    _ = shutil.copyfile(Path(worker.__file__), copied)
    fault = """
import os
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import worker

move = worker._move
remaining = int(sys.argv[3])

def interrupt(source, destination):
    global remaining
    move(source, destination)
    remaining -= 1
    if remaining == 0:
        os._exit(83)

worker._move = interrupt
worker.execute(Path(sys.argv[2]))
"""
    interrupted = subprocess.run(
        [sys.executable, "-I", "-c", fault, str(workspace), str(journal), str(moves)],
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert interrupted.returncode == 83, interrupted.stderr
    recovered = subprocess.run(
        [sys.executable, "-I", str(copied), str(journal), "--recover"],
        capture_output=True,
        check=True,
        timeout=10,
    )
    assert recovered.stdout.strip() == b"OCR CLI rolled back."
    assert live.stat().st_ino == old_inode
    assert candidate.is_dir()
