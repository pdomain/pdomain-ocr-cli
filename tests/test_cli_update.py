"""Contract tests for the explicit OCR CLI updater."""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import contextmanager
from io import BytesIO
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from pdomain_ocr_cli import _self_update as updater
from pdomain_ocr_cli import _update_worker as worker
from pdomain_ocr_cli import ocr_to_txt as cli

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path
    from urllib.request import Request

    from _pytest.capture import CaptureFixture


@pytest.fixture
def release(monkeypatch: pytest.MonkeyPatch) -> str:
    """Supply a newer release without accessing the network."""
    monkeypatch.setattr(updater, "VERSION", "1.0.0")
    tag = "v1.1.0"
    monkeypatch.setattr(updater, "_latest_release_tag", lambda: tag)
    return tag


@pytest.fixture
def installer(release: str, monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Record any installation request without changing a real installation."""
    assert release
    monkeypatch.setattr(updater, "_is_managed_install", lambda: True)
    apply = Mock(return_value=0)
    monkeypatch.setattr(updater, "_apply_release", apply)
    return apply


def test_cli_update_check_dispatches_without_ocr(
    installer: Mock,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "update").mkdir()
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "update", "--check"])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert "1.0.0" in output
    assert "1.1.0" in output
    installer.assert_not_called()


@pytest.mark.parametrize(("choice", "expected"), [("on", "true"), ("off", "false")])
def test_cli_saves_auto_check_preference_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, choice: str, expected: str
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "update").mkdir()
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    lookup = Mock(side_effect=AssertionError("Saving a preference must stay offline"))
    monkeypatch.setattr(updater, "_latest_release_tag", lookup)
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "update", "--auto-check", choice])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 0
    assert (tmp_path / "pdomain-ocr" / "update.toml").read_text() == f"auto_check = {expected}\n"
    lookup.assert_not_called()


@pytest.mark.parametrize("tag", ["v1.0.0", "v0.9.9"])
def test_updater_skips_equal_and_older_releases(
    tag: str, installer: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(updater, "_latest_release_tag", lambda: tag)
    assert updater.run_update(["--yes"]) == 0
    installer.assert_not_called()


def test_updater_yes_runs_only_the_selected_release(
    installer: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompt = Mock(side_effect=AssertionError("--yes must not prompt"))
    monkeypatch.setattr("builtins.input", prompt)
    assert updater.run_update(["--yes"]) == 0
    installer.assert_called_once_with("v1.1.0")


def test_updater_prompts_then_runs_approved_release(
    installer: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompt = Mock(return_value=" Y ")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", prompt)
    assert updater.run_update([]) == 0
    prompt.assert_called_once()
    installer.assert_called_once_with("v1.1.0")


@pytest.mark.parametrize("reply", ["", "n", "later"])
def test_updater_declines_without_installing(
    reply: str, installer: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", Mock(return_value=reply))
    assert updater.run_update([]) == 0
    installer.assert_not_called()


@pytest.mark.parametrize("error", [EOFError, KeyboardInterrupt])
def test_updater_handles_interrupted_confirmation(
    error: type[BaseException], installer: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", Mock(side_effect=error))
    assert updater.run_update([]) == 130
    installer.assert_not_called()


def test_updater_refuses_unmanaged_install(
    installer: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(updater, "_is_managed_install", lambda: False)
    assert updater.run_update(["--yes"]) != 0
    installer.assert_not_called()


@pytest.mark.parametrize("error", [OSError("offline"), ValueError("bad release metadata")])
def test_check_reports_release_lookup_failures(
    error: Exception,
    installer: Mock,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    monkeypatch.setattr(updater, "_latest_release_tag", Mock(side_effect=error))
    assert updater.run_update(["--check"]) != 0
    assert str(error) in capsys.readouterr().err
    installer.assert_not_called()


def test_updater_propagates_installer_failure(installer: Mock) -> None:
    installer.return_value = 7
    assert updater.run_update(["--yes"]) == 7
    installer.assert_called_once_with("v1.1.0")


def test_update_named_directory_remains_an_ocr_input(
    tmp_path: Path, installer: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "update").mkdir()
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "update"])
    original = RuntimeError("normal OCR parser reached")
    monkeypatch.setattr(cli, "parse_args", Mock(side_effect=original))
    with pytest.raises(RuntimeError, match="normal OCR parser reached"):
        cli.main()
    installer.assert_not_called()


def test_updater_requires_confirmation_in_noninteractive_shell(
    installer: Mock, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert updater.run_update([]) == 1
    assert "--yes" in capsys.readouterr().err
    installer.assert_not_called()


def test_updater_reports_uv_lookup_failure(
    installer: Mock, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    failure = subprocess.CalledProcessError(2, ["uv", "tool", "dir"])
    monkeypatch.setattr(updater, "_is_managed_install", Mock(side_effect=failure))
    assert updater.run_update(["--yes"]) == 1
    assert "Update failed" in capsys.readouterr().err
    installer.assert_not_called()


def test_updater_refuses_conflicting_flags(installer: Mock) -> None:
    with pytest.raises(SystemExit) as result:
        _ = updater.run_update(["--yes", "--check"])
    assert result.value.code == 2
    installer.assert_not_called()


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"[]", "release object"),
        (b"{}", "stable release tag"),
        (b'{"tag_name": 1}', "stable release tag"),
        (b'{"tag_name": "v1.0.0-rc1"}', "stable release tag"),
        (b"<html>", "Expecting value"),
    ],
)
def test_check_reports_bad_release_response(
    body: bytes, message: str, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", Mock(return_value=BytesIO(body)))
    assert updater.run_update(["--check"]) == 1
    assert message in capsys.readouterr().err


def test_release_lookup_uses_latest_release_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updater, "VERSION", "1.0.0")
    requests: list[Request] = []

    def fetch(request: Request, *, timeout: float) -> BytesIO:
        requests.append(request)
        assert timeout == 10
        return BytesIO(json.dumps({"tag_name": "v1.1.0"}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fetch)
    assert updater.run_update(["--check"]) == 0
    assert len(requests) == 1
    request = requests[0]
    assert (
        request.full_url == "https://api.github.com/repos/pdomain/pdomain-ocr-cli/releases/latest"
    )
    assert request.get_header("User-agent") == "pdomain-ocr-cli/1.0.0"


def test_managed_detection_rejects_editable_install_before_uv(
    release: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    editable = Mock(return_value=True)
    run = Mock(side_effect=AssertionError("editable installs must not query uv"))
    monkeypatch.setattr(updater, "is_editable_install", editable)
    monkeypatch.setattr("subprocess.run", run)
    assert release
    assert updater.run_update(["--yes"]) == 1
    editable.assert_called_once_with("pdomain-ocr-cli")
    run.assert_not_called()


@pytest.mark.parametrize(
    ("tool_dir_text", "receipt", "managed"),
    [("correct", True, True), ("correct", False, False), ("other", True, False), ("", True, False)],
)
def test_managed_detection_requires_matching_uv_directory_and_receipt(
    tool_dir_text: str,
    receipt: bool,
    managed: bool,
    release: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = tmp_path / "correct" / "pdomain-ocr-cli"
    prefix.mkdir(parents=True)
    if receipt:
        (prefix / "uv-receipt.toml").touch()
    stdout = f"{tmp_path / tool_dir_text}\n" if tool_dir_text else " \n"
    run = Mock(return_value=subprocess.CompletedProcess(["uv"], 0, stdout=stdout))
    apply = Mock(return_value=0)
    monkeypatch.setattr(updater, "is_editable_install", Mock(return_value=False))
    monkeypatch.setattr("shutil.which", Mock(return_value="/absolute/uv"))
    monkeypatch.setattr(updater, "sys", SimpleNamespace(prefix=str(prefix), stderr=sys.stderr))
    monkeypatch.setattr(updater, "_apply_release", apply)
    monkeypatch.setattr("subprocess.run", run)

    assert updater.run_update(["--yes"]) == (0 if managed else 1)
    run.assert_called_once_with(
        ["/absolute/uv", "tool", "dir"], check=True, capture_output=True, text=True
    )
    if managed:
        apply.assert_called_once_with(release)
    else:
        apply.assert_not_called()


def test_updater_reports_uv_missing(
    release: str, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(updater, "is_editable_install", Mock(return_value=False))
    monkeypatch.setattr("shutil.which", Mock(return_value=None))
    assert release
    assert updater.run_update(["--yes"]) == 1
    assert "uv is not on PATH" in capsys.readouterr().err


@pytest.fixture
def installers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use real installer handoff code with local test scripts."""
    monkeypatch.setattr(updater, "_INSTALLERS", tmp_path)
    monkeypatch.setattr(updater, "_is_managed_install", Mock(return_value=True))
    return tmp_path


def test_apply_reports_missing_bundled_installer(
    release: str, installers: Path, capsys: CaptureFixture[str]
) -> None:
    assert release
    assert not list(installers.iterdir())
    assert updater.run_update(["--yes"]) == 1
    assert "bundled installer" in capsys.readouterr().err


@pytest.mark.parametrize(("override", "expected"), [(None, "3.12"), ("3.11", "3.11")])
@pytest.mark.parametrize("stage_fails", [False, True])
def test_apply_prepares_candidate_before_launching_worker(
    override: str | None,
    expected: str,
    stage_fails: bool,
    release: str,
    installers: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tools = installers / "tools"
    live = tools / "pdomain-ocr-cli"
    live.mkdir(parents=True)
    public = installers / "bin" / "pdomain-ocr"
    public.parent.mkdir()
    public.touch()
    script = installers / "install.sh"
    script.touch()
    base_python = installers / "python"
    base_python.touch()
    monkeypatch.setattr(
        updater,
        "sys",
        SimpleNamespace(
            platform="linux",
            version_info=SimpleNamespace(major=3, minor=12),
            prefix=str(live),
            stderr=sys.stderr,
            _base_executable=str(base_python),
        ),
    )
    monkeypatch.setattr("shutil.which", Mock(return_value="/absolute/uv"))
    if override is None:
        monkeypatch.delenv("PD_OCR_INSTALL_PYTHON", raising=False)
    else:
        monkeypatch.setenv("PD_OCR_INSTALL_PYTHON", override)
    monkeypatch.setenv("PD_OCR_INSTALL_AUTO_UPDATE_CHECK", "1")
    prepare = Mock(side_effect=ValueError("bad wheel") if stage_fails else None)
    journal = Mock()
    launch = Mock(return_value=7)
    monkeypatch.setattr(updater, "prepare_candidate", prepare, raising=False)
    monkeypatch.setattr(updater, "prepare_transaction", journal, raising=False)
    monkeypatch.setattr(updater, "_launch_worker", launch, raising=False)
    monkeypatch.setattr(
        "subprocess.run",
        Mock(return_value=subprocess.CompletedProcess(["uv"], 0, stdout=str(public.parent))),
    )

    assert updater.run_update(["--yes"]) == (1 if stage_fails else 7)
    uv, installer, directory, env, launcher = prepare.call_args.args
    assert uv == "/absolute/uv"
    assert installer == script
    assert directory.parent == tools.parent
    assert launcher == public
    assert env["PDOMAIN_OCR_EXPECTED_RELEASE_TAG"] == release
    assert env["PD_OCR_INSTALL_PYTHON"] == expected
    assert "PD_OCR_INSTALL_AUTO_UPDATE_CHECK" not in env
    if stage_fails:
        assert not directory.exists()
        journal.assert_not_called()
        launch.assert_not_called()
        return
    journal.assert_called_once_with(
        directory, live, prepare.return_value, public, previous_version="1.0.0", version="1.1.0"
    )
    launch.assert_called_once()
    assert journal.return_value in launch.call_args.args


def test_posix_worker_runs_with_external_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "base python"
    worker = tmp_path / "worker.py"
    journal = tmp_path / "transaction.json"
    run = Mock(return_value=subprocess.CompletedProcess([], 1))
    monkeypatch.setattr("subprocess.run", run)

    assert updater._launch_worker(base, worker, journal, windows=False) == 1
    run.assert_called_once_with([str(base), "-I", str(worker), str(journal)], check=False)


@pytest.mark.parametrize("problem", ["unknown", "absent", "inside", "bin"])
def test_update_refuses_when_recovery_paths_are_unavailable(
    problem: str,
    release: str,
    installers: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    live = installers / "tools" / "pdomain-ocr-cli"
    live.mkdir(parents=True)
    base = (live if problem == "inside" else installers) / "python"
    if problem != "absent":
        base.touch()
    (installers / "install.sh").touch()
    monkeypatch.setattr(
        updater,
        "sys",
        SimpleNamespace(
            platform="linux",
            version_info=SimpleNamespace(major=3, minor=13),
            prefix=str(live),
            stderr=sys.stderr,
            _base_executable=None if problem == "unknown" else str(base),
        ),
    )
    monkeypatch.setattr("shutil.which", Mock(return_value="/absolute/uv"))
    monkeypatch.setattr(
        "subprocess.run", Mock(return_value=subprocess.CompletedProcess([], 0, stdout="relative"))
    )
    prepare = Mock()
    monkeypatch.setattr(updater, "prepare_candidate", prepare)

    assert release
    assert updater.run_update(["--yes"]) == 1
    error = capsys.readouterr().err
    assert ("absolute launcher directory" if problem == "bin" else "external Python") in error
    prepare.assert_not_called()


def test_windows_worker_waits_before_starting_external_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    base = tmp_path / "base python.exe"
    worker = tmp_path / "worker.py"
    journal = tmp_path / "transaction.json"
    popen = Mock()
    monkeypatch.setattr("subprocess.Popen", popen)
    monkeypatch.setattr("shutil.which", Mock(return_value="/absolute/powershell.exe"))
    monkeypatch.setattr("os.getpid", lambda: 34)
    monkeypatch.setattr("os.getppid", lambda: 56)

    assert updater._launch_worker(base, worker, journal, windows=True) == 0
    handoff = tmp_path / "handoff.ps1"
    script = handoff.read_text(encoding="utf-8")
    assert script.index("$launcher.WaitForExit") < script.index("& $Python -I $Worker $Journal")
    assert "Update handed off" in capsys.readouterr().out
    popen.assert_called_once_with(
        [
            "/absolute/powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "RemoteSigned",
            "-File",
            str(handoff),
            "34",
            "56",
            str(base),
            str(worker),
            str(journal),
        ]
    )


@pytest.mark.parametrize("windows", [False, True])
def test_recovery_command_quotes_all_paths(tmp_path: Path, windows: bool) -> None:
    base = tmp_path / "base's python"
    worker = tmp_path / "private worker.py"
    journal = tmp_path / "transaction.json"

    command = updater._recovery_command(base, worker, journal, windows=windows)
    assert command.endswith("'--recover'" if windows else "--recover")
    assert "base''s python" in command if windows else "base'\"'\"'s python" in command


@pytest.mark.parametrize(
    "mode",
    ["ocr", "models", "version", "probe", "busy", "parked", "stale", "unmanaged", "no-receipt"],
)
def test_managed_ocr_holds_installation_during_work(
    mode: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    prefix = tmp_path / ("unmanaged" if mode == "unmanaged" else "pdomain-ocr-cli")
    prefix.mkdir()
    if mode not in {"no-receipt", "parked"}:
        (prefix / "uv-receipt.toml").touch()
    if mode == "parked":
        (prefix.parent / ".pdomain-ocr-cli.in-use.lock").touch()
    monkeypatch.setattr(
        cli, "_installed_version", lambda name: "old" if mode == "stale" else cli._VERSION
    )
    monkeypatch.setattr(sys, "prefix", str(prefix))
    arg = {"models": "download-models", "version": "--version", "probe": "--version"}.get(
        mode, "page.png"
    )
    if mode == "probe":
        monkeypatch.setenv("PDOMAIN_OCR_UPDATE_PROBE", "1")
    else:
        monkeypatch.delenv("PDOMAIN_OCR_UPDATE_PROBE", raising=False)
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", arg])
    events: list[str] = []

    @contextmanager
    def hold(path: Path) -> Generator[None]:
        assert path == prefix
        if mode in {"busy", "parked"}:
            raise TimeoutError("update in progress")
        events.append("locked")
        try:
            yield
        finally:
            events.append("released")

    def ocr() -> None:
        events.append("ocr")

    def models(args: list[str]) -> int:
        assert not args
        events.append("models")
        return 0

    monkeypatch.setattr(worker, "hold_installation", hold, raising=False)
    monkeypatch.setattr(cli, "_run_ocr", ocr, raising=False)
    monkeypatch.setattr(cli, "_download_models", models)
    if mode in {"models", "busy", "parked", "stale"}:
        with pytest.raises(SystemExit) as result:
            cli.main()
        assert result.value.code == (0 if mode == "models" else 1)
    else:
        cli.main()
    if mode in {"busy", "parked"}:
        assert "update in progress" in capsys.readouterr().err
        assert not events
    elif mode == "stale":
        assert "changed during startup" in capsys.readouterr().err
        assert events == ["locked", "released"]
    elif mode in {"ocr", "models"}:
        assert events == ["locked", mode, "released"]
    elif mode == "version":
        assert events == ["locked", "ocr", "released"]
    else:
        assert events == ["ocr"]


def test_runtime_health_check_runs_offline_and_reports_exact_version(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    import importlib

    probe = Mock()
    monkeypatch.setattr(importlib, "import_module", probe)
    monkeypatch.setattr(updater, "VERSION", "1.2.3")
    monkeypatch.setattr(updater, "_latest_release_tag", Mock(side_effect=AssertionError))
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "--check-runtime"])

    with pytest.raises(SystemExit) as result:
        cli.main()

    assert result.value.code == 0
    assert capsys.readouterr().out.strip() == "pdomain-ocr runtime OK 1.2.3"
    assert {call.args[0] for call in probe.call_args_list} == {
        "pdomain_book_tools.ocr.doctr_support",
        "pdomain_ops.gpu.device",
        "pdomain_ops.gpu.doctr_batch",
    }


def test_runtime_health_check_reports_import_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    import importlib

    monkeypatch.setattr(
        importlib, "import_module", Mock(side_effect=ImportError("broken OCR dependency"))
    )
    assert updater.check_runtime() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "broken OCR dependency" in captured.err
