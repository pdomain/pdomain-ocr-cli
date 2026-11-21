"""Contract tests for the explicit OCR CLI updater."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from io import BytesIO
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from pdomain_ocr_cli import _self_update as updater
from pdomain_ocr_cli import ocr_to_txt as cli

if TYPE_CHECKING:
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
def test_apply_runs_bundled_posix_installer_with_approved_tag(
    override: str | None,
    expected: str,
    release: str,
    installers: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = installers / "install.sh"
    script.touch()
    run = Mock(return_value=subprocess.CompletedProcess(["sh"], 7))
    version_info = SimpleNamespace(major=3, minor=12)
    monkeypatch.setattr(
        updater, "sys", SimpleNamespace(platform="linux", version_info=version_info)
    )
    monkeypatch.setattr("shutil.which", Mock(return_value="/absolute/sh"))
    monkeypatch.setattr("subprocess.run", run)
    monkeypatch.setenv("CUDA_VERSION", "13.0")
    if override is None:
        monkeypatch.delenv("PD_OCR_INSTALL_PYTHON", raising=False)
    else:
        monkeypatch.setenv("PD_OCR_INSTALL_PYTHON", override)

    assert updater.run_update(["--yes"]) == 7
    run.assert_called_once_with(
        ["/absolute/sh", str(script)],
        env={
            **os.environ,
            "PDOMAIN_OCR_EXPECTED_RELEASE_TAG": release,
            "PD_OCR_INSTALL_PYTHON": expected,
        },
        check=False,
    )


@pytest.mark.parametrize("launch_error", [False, True])
def test_windows_apply_hands_off_bundled_installer_before_replacing_launcher(
    launch_error: bool,
    release: str,
    installers: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    script = installers / "install.ps1"
    _ = script.write_text("Write-Output 'bundled installer'", encoding="utf-8")
    directory = installers / "private"
    directory.mkdir()
    popen = Mock(side_effect=OSError("launch failed") if launch_error else None)
    version_info = SimpleNamespace(major=3, minor=13)
    monkeypatch.setattr(
        updater,
        "sys",
        SimpleNamespace(platform="win32", stderr=sys.stderr, version_info=version_info),
    )
    monkeypatch.delenv("PD_OCR_INSTALL_PYTHON", raising=False)
    monkeypatch.setattr("shutil.which", Mock(return_value="/absolute/powershell.exe"))
    monkeypatch.setattr("os.getpid", lambda: 34)
    monkeypatch.setattr("os.getppid", lambda: 56)
    monkeypatch.setattr("tempfile.mkdtemp", Mock(return_value=str(directory)))
    monkeypatch.setattr("subprocess.Popen", popen)

    if launch_error:
        assert updater.run_update(["--yes"]) == 1
        assert "launch failed" in capsys.readouterr().err
        assert not directory.exists()
    else:
        assert updater.run_update(["--yes"]) == 0
        assert (directory / script.name).read_bytes() == script.read_bytes()
        handoff = (directory / "handoff.ps1").read_text(encoding="utf-8")
        assert handoff.index("WaitForExit") < handoff.index("'install.ps1'")
        assert "Update handed off" in capsys.readouterr().out

    popen.assert_called_once_with(
        [
            "/absolute/powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "RemoteSigned",
            "-File",
            str(directory / "handoff.ps1"),
            "34",
            "56",
        ],
        env={
            **os.environ,
            "PDOMAIN_OCR_EXPECTED_RELEASE_TAG": release,
            "PD_OCR_INSTALL_PYTHON": "3.13",
        },
    )
