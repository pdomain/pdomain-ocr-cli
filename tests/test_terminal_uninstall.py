"""Keep the terminal uninstaller bound to the invoking uv environment."""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn

import pytest

from pdomain_ocr_cli import _terminal_uninstall, ocr_to_txt


def test_terminal_dispatches_uninstall(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "uninstall", "--preview"])
    monkeypatch.setattr(
        _terminal_uninstall,
        "run_terminal_uninstall",
        lambda args: 7 if args == ["--preview"] else 9,
    )
    with pytest.raises(SystemExit, match="7"):
        ocr_to_txt.main()


def test_terminal_uninstall_validates_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_terminal_uninstall, "os", SimpleNamespace(name="nt", environ={}))
    assert _terminal_uninstall.run_terminal_uninstall([]) == 2
    monkeypatch.setattr(_terminal_uninstall, "os", SimpleNamespace(name="posix", environ={}))
    prefix = tmp_path / "pdomain-ocr-cli"
    prefix.mkdir()
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    assert _terminal_uninstall.run_terminal_uninstall([]) == 2
    monkeypatch.setattr(sys, "prefix", str(prefix))
    assert _terminal_uninstall.run_terminal_uninstall([]) == 2
    (prefix / "uv-receipt.toml").touch()

    def execute(path: str, argv: list[str], env: dict[str, str]) -> NoReturn:
        assert path == "/bin/sh"
        assert argv[2:] == ["terminal-uninstall", "--preview"]
        assert env["PDOMAIN_OCR_EXPECTED_TOOL_ENV"] == str(prefix)
        raise SystemExit(7)

    with pytest.raises(SystemExit, match="7"):
        _terminal_uninstall.run_terminal_uninstall(["--preview"], execute=execute)
