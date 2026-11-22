"""Contract tests for preparing a relocatable OCR update."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest

from pdomain_ocr_cli import _update_stage as staging

_WHEEL = "pdomain_ocr_cli-1.2.3-py3-none-any.whl"
_DIST = "pdomain-ocr-cli"


def _wheel_bytes(entrypoints: str | None) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        if entrypoints is not None:
            archive.writestr("pdomain_ocr_cli-1.2.3.dist-info/entry_points.txt", entrypoints)
    return buffer.getvalue()


_WHEEL_BYTES = _wheel_bytes("[console_scripts]\npdomain-ocr = pdomain_ocr_cli.ocr_to_txt:main\n")
_DIGEST = hashlib.sha256(_WHEEL_BYTES).hexdigest()


@dataclass
class _Commands:
    directory: Path
    wheel_name: str = _WHEEL
    python: str = "3.13"
    backend: str = ""
    digest: str = _DIGEST
    record: str | None = None
    receipt: str | None = None
    wheel_bytes: bytes = _WHEEL_BYTES
    missing_wheel: bool = False
    relocatable: bool = True
    timeout: bool = False
    calls: list[list[str]] = field(default_factory=list)

    def __call__(
        self,
        argv: list[str],
        *,
        env: dict[str, str],
        cwd: Path,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[bytes]:
        assert cwd == self.directory
        assert check
        assert timeout > 0
        self.calls.append(argv)
        tools = Path(env["UV_TOOL_DIR"])
        launcher_dir = Path(env["UV_TOOL_BIN_DIR"])
        assert tools == self.directory / "tools"
        assert launcher_dir == self.directory / "bin"
        if self.timeout:
            raise subprocess.TimeoutExpired(argv, timeout)
        if len(self.calls) == 1:
            release = Path(argv[-1])
            assert env["PDOMAIN_OCR_EXPECTED_RELEASE_TAG"] == "v1.2.3"
            release.mkdir()
            _ = (release / "candidate").write_text(
                self.record
                if self.record is not None
                else f"{self.wheel_name}\n{self.python}\n{self.backend}\n{self.digest}\n",
                encoding="ascii",
            )
            if not self.missing_wheel:
                _ = (release / _WHEEL).write_bytes(self.wheel_bytes)
        else:
            environment = tools / _DIST
            if argv[1] == "venv":
                environment.mkdir(parents=True)
                _ = (environment / "pyvenv.cfg").write_text(
                    f"relocatable = {str(self.relocatable).lower()}\n", encoding="ascii"
                )
            elif argv[1] == "tool":
                launcher_name = (
                    "pdomain-ocr.exe" if self.calls[0][0] == "powershell.exe" else "pdomain-ocr"
                )
                launcher_dir.mkdir()
                (launcher_dir / launcher_name).touch()
                receipt = self.receipt
                if receipt is None:
                    value = json.dumps(str(launcher_dir / launcher_name))
                    receipt = (
                        '[tool]\npython = "3.13"\n'
                        'entrypoints = [{ name = "pdomain-ocr", '
                        f'install-path = {value}, from = "{_DIST}" }}]\n'
                        '[tool.options]\nindex-strategy = "first-index"\n'
                    )
                _ = (environment / "uv-receipt.toml").write_bytes(receipt.encode("utf-8"))
            else:
                assert argv[-2:] == ["-CheckStagedRuntime", str(environment)]
                assert (environment / "uv-receipt.toml").is_file()
        return subprocess.CompletedProcess(argv, 0)


@pytest.fixture
def commands(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _Commands:
    runner = _Commands(tmp_path / "update with spaces")
    runner.directory.mkdir()
    monkeypatch.setattr(staging.subprocess, "run", runner)
    monkeypatch.setattr(staging.shutil, "which", lambda program, **kwargs: program)
    return runner


def _prepare(commands: _Commands, *, powershell: bool = False) -> Path:
    launcher = (
        commands.directory.parent
        / 'live café "OCR"'
        / ("pdomain-ocr.exe" if powershell else "pdomain-ocr")
    )

    return staging.prepare_candidate(
        "/fake/uv",
        commands.directory.parent / ("install.ps1" if powershell else "install.sh"),
        commands.directory,
        {
            "PDOMAIN_OCR_EXPECTED_RELEASE_TAG": "v1.2.3",
            "PD_OCR_INSTALL_PYTHON": "3.13",
            "UV_TOOL_DIR": "/live/tools",
            "UV_TOOL_BIN_DIR": "/live/bin",
        },
        launcher,
    )


@pytest.mark.parametrize(("flushes", "commands_run"), [(0, 1), (1, 3)])
def test_failed_stage_flush_does_not_return_candidate(
    commands: _Commands, flushes: int, commands_run: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed_flush = Mock(side_effect=[None] * flushes + [OSError("flush failed")])
    monkeypatch.setattr(staging.os, "fsync", failed_flush)

    with pytest.raises(OSError, match="flush failed"):
        _ = _prepare(commands)

    assert len(commands.calls) == commands_run


@pytest.mark.parametrize("powershell", [False, True])
def test_prepares_isolated_candidate_and_retargets_receipt(
    commands: _Commands, powershell: bool
) -> None:
    commands.backend = "auto" if powershell else ""
    environment = _prepare(commands, powershell=powershell)

    expected_shell = "powershell.exe" if powershell else "sh"
    expected_prepare = "-PrepareUpdate" if powershell else "--prepare-update"
    release = commands.directory / "release"
    assert commands.calls[0][0] == expected_shell
    assert commands.calls[0][-2:] == [expected_prepare, str(release)]
    assert commands.calls[1] == [
        "/fake/uv",
        "venv",
        "--relocatable",
        "--python",
        "3.13",
        str(environment),
    ]
    assert commands.calls[2][:5] == ["/fake/uv", "tool", "install", "--python", "3.13"]
    assert str(release / _WHEEL) in commands.calls[2]
    assert "pdomain=https://pdomain.github.io/pdomain-index-pip/simple/" in commands.calls[2]
    assert ("--torch-backend" in commands.calls[2]) is powershell
    assert len(commands.calls) == (4 if powershell else 3)
    if powershell:
        assert commands.calls[3] == [
            *commands.calls[0][:-2],
            "-CheckStagedRuntime",
            str(environment),
        ]
    assert (release / _WHEEL).read_bytes() == _WHEEL_BYTES
    receipt = (environment / "uv-receipt.toml").read_text(encoding="utf-8")
    assert 'index-strategy = "first-index"' in receipt
    assert tomllib.loads(receipt)["tool"]["entrypoints"] == [
        {
            "name": "pdomain-ocr",
            "from": _DIST,
            "install-path": str(
                commands.directory.parent
                / 'live café "OCR"'
                / ("pdomain-ocr.exe" if powershell else "pdomain-ocr")
            ),
        },
    ]


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("wheel_name", "../" + _WHEEL, "candidate record"),
        ("python", "3.12", "candidate record"),
        ("backend", "cu128", "candidate record"),
        ("digest", "not-a-digest", "candidate record"),
        ("digest", "0" * 64, "digest mismatch"),
    ],
)
def test_invalid_candidate_does_not_reach_uv(
    commands: _Commands, field_name: str, value: str, message: str
) -> None:
    setattr(commands, field_name, value)
    with pytest.raises(ValueError, match=message):
        _prepare(commands)
    assert len(commands.calls) == 1


def test_fails_when_uv_replaces_relocatable_environment(commands: _Commands) -> None:
    commands.relocatable = False
    with pytest.raises(ValueError, match="relocatable"):
        _prepare(commands)


@pytest.mark.parametrize(
    "receipt",
    [
        "",
        "[tool]\n",
        "[tool]\nentrypoints = []\n",
        "[tool]\nentrypoints = [1]\n",
        '[tool]\nentrypoints = [{ name = "other-tool" }]\n',
        '[tool]\nentrypoints = [{ name = "pdomain-ocr", from = "other-tool" }]\n',
        '[tool]\nentrypoints = [{ name = "pdomain-ocr", from = "pdomain-ocr-cli" }]\n',
        '[tool]\nentrypoints = [{ name = "pdomain-ocr", from = "pdomain-ocr-cli", install-path = "/wrong" }]\n',
    ],
)
def test_refuses_unexpected_receipt(commands: _Commands, receipt: str) -> None:
    commands.receipt = receipt
    with pytest.raises((TypeError, ValueError), match="receipt"):
        _prepare(commands)


def test_preparation_reports_timeout(commands: _Commands) -> None:
    commands.timeout = True
    with pytest.raises(OSError, match="timed out"):
        _prepare(commands)


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("missing approval", "approved"),
        ("missing directory", "staging directory"),
        ("relative launcher", "absolute path"),
        ("existing stage", "already exist"),
    ],
)
def test_candidate_checks_paths_and_approval_before_running(
    commands: _Commands, case: str, message: str
) -> None:
    env = {"PDOMAIN_OCR_EXPECTED_RELEASE_TAG": "v1.2.3"}
    directory = commands.directory
    launcher = directory.parent / "pdomain-ocr"
    if case == "missing approval":
        env.clear()
    elif case == "missing directory":
        directory = directory / "absent"
    elif case == "relative launcher":
        launcher = Path("pdomain-ocr")
    else:
        (directory / "release").mkdir()

    with pytest.raises(ValueError, match=message):
        staging.prepare_candidate("/fake/uv", launcher, directory, env, launcher)
    assert commands.calls == []


def test_refuses_missing_shell(commands: _Commands, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(staging.shutil, "which", lambda *args, **kwargs: None)
    with pytest.raises(FileNotFoundError, match="sh is not on PATH"):
        _prepare(commands)
    assert commands.calls == []


def test_refuses_malformed_record(commands: _Commands) -> None:
    commands.record = _WHEEL + "\n"
    with pytest.raises(ValueError, match="candidate record"):
        _prepare(commands)


def test_refuses_missing_wheel(commands: _Commands) -> None:
    commands.missing_wheel = True
    with pytest.raises(ValueError, match="candidate record"):
        _prepare(commands)


@pytest.mark.parametrize(
    ("relative", "message"),
    [
        ("release/candidate", "candidate record"),
        ("tools/pdomain-ocr-cli/uv-receipt.toml", "receipt"),
    ],
)
def test_refuses_linked_metadata(
    commands: _Commands, monkeypatch: pytest.MonkeyPatch, relative: str, message: str
) -> None:
    real_is_symlink = Path.is_symlink
    forbidden = commands.directory / relative

    def is_symlink(path: Path) -> bool:
        return path == forbidden or real_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", is_symlink)
    with pytest.raises(ValueError, match=message):
        _prepare(commands)


@pytest.mark.parametrize(
    ("comment", "message"),
    [("", "Unsupported install-path"), ('# install-path = "example"\n', "Failed to retarget")],
)
def test_refuses_ambiguous_receipt_replacement(
    commands: _Commands, comment: str, message: str
) -> None:
    path = json.dumps(str(commands.directory / "bin/pdomain-ocr"))
    commands.receipt = (
        f'[tool]\n{comment}entrypoints = [{{ name = "pdomain-ocr", "install-path" = {path},'
        ' from = "pdomain-ocr-cli" }]\n'
    )
    with pytest.raises(ValueError, match=message):
        _prepare(commands)


@pytest.mark.parametrize(
    "entrypoints",
    [
        None,
        "malformed file",
        "[gui_scripts]\npdomain-ocr = pdomain_ocr_cli.ocr_to_txt:main\n",
        "[console_scripts]\npdomain-ocr = pdomain_ocr_cli.replacement:main\n",
        "[console_scripts]\nPDOMAIN-OCR = pdomain_ocr_cli.ocr_to_txt:main\n",
        "[console_scripts]\npdomain-ocr = pdomain_ocr_cli.ocr_to_txt:main\nextra = example:main\n",
    ],
)
def test_rejects_wheel_with_incompatible_public_launcher(
    commands: _Commands, entrypoints: str | None
) -> None:
    commands.wheel_bytes = _wheel_bytes(entrypoints)
    commands.digest = hashlib.sha256(commands.wheel_bytes).hexdigest()
    with pytest.raises(ValueError, match="console entry point"):
        _prepare(commands)
    assert len(commands.calls) == 1
