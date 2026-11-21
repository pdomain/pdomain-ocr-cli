from __future__ import annotations

from types import SimpleNamespace

import pytest

from pdomain_ocr_cli._startup_notices import save_auto_update_check, update_check_disabled


def test_update_check_disabled_by_flag(monkeypatch) -> None:
    monkeypatch.delenv("PD_OCR_NO_UPDATE_CHECK", raising=False)
    assert update_check_disabled(SimpleNamespace(no_update_check=True)) is True


def test_update_check_disabled_by_env(monkeypatch) -> None:
    monkeypatch.setenv("PD_OCR_NO_UPDATE_CHECK", "1")
    assert update_check_disabled(SimpleNamespace(no_update_check=False)) is True


def test_update_check_disabled_by_default(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("PD_OCR_NO_UPDATE_CHECK", raising=False)
    monkeypatch.delenv("PD_OCR_AUTO_UPDATE_CHECK", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
    assert update_check_disabled(SimpleNamespace(no_update_check=False)) is True


@pytest.mark.parametrize(
    ("override", "file_value", "disabled"),
    [
        ("", True, False),
        ("", False, True),
        ("invalid", True, False),
        ("0", True, True),
        ("yes", False, False),
    ],
)
def test_update_check_preference(monkeypatch, tmp_path, override, file_value, disabled) -> None:
    monkeypatch.delenv("PD_OCR_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setenv("PD_OCR_AUTO_UPDATE_CHECK", override)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = save_auto_update_check(enabled=file_value)
    assert path == tmp_path / "pdomain-ocr" / "update.toml"
    assert update_check_disabled(SimpleNamespace(no_update_check=False)) is disabled
    assert update_check_disabled(SimpleNamespace(no_update_check=True)) is True
    monkeypatch.setenv("PD_OCR_NO_UPDATE_CHECK", "1")
    assert update_check_disabled(SimpleNamespace(no_update_check=False)) is True


def test_invalid_update_config_defaults_to_disabled(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("PD_OCR_NO_UPDATE_CHECK", raising=False)
    monkeypatch.delenv("PD_OCR_AUTO_UPDATE_CHECK", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = save_auto_update_check(enabled=True)
    _ = path.write_text("auto_check = [", encoding="utf-8")
    assert update_check_disabled(SimpleNamespace(no_update_check=False)) is True
