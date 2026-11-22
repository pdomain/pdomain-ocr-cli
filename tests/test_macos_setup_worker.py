from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

WORKER = Path(__file__).resolve().parents[1] / "installer/macos/setup-worker.sh"


@pytest.mark.parametrize(("models", "prefetch"), [("download", True), ("skip", False)])
def test_setup_uses_terminal_installer(tmp_path: Path, models: str, prefetch: bool) -> None:
    worker = tmp_path / "setup-worker.sh"
    _ = shutil.copyfile(WORKER, worker)
    launcher = tmp_path / "bin/pdomain-ocr"
    launcher.parent.mkdir()
    _ = launcher.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\n'
        'case "$1" in --version) echo "pdomain-ocr 0.10.0";; esac\n'
    )
    launcher.chmod(0o755)
    uv = tmp_path / "bin/uv"
    _ = uv.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_BIN"\n')
    uv.chmod(0o755)
    _ = (tmp_path / "release-tag").write_text("v0.10.0\n")
    _ = (tmp_path / "install.sh").write_text(
        '#!/bin/sh\nprintf "%s %s %s\\n" "$PDOMAIN_OCR_EXPECTED_RELEASE_TAG" '
        '"$PD_OCR_INSTALL_AUTO_UPDATE_CHECK" "$*" >> "$TEST_LOG"\n'
    )
    log = tmp_path / "events"
    result = subprocess.run(
        ["sh", str(worker), "install", models, "enabled"],
        env={
            **os.environ,
            "UV_INSTALL_DIR": str(launcher.parent),
            "TEST_BIN": str(launcher.parent),
            "TEST_LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"OCR_SETUP_LAUNCHER {launcher}" in result.stdout
    assert log.read_text().splitlines() == [
        "v0.10.0 1 --skip-models",
        "--version",
        "--check-runtime",
        *(["download-models"] if prefetch else []),
    ]


def _fixture_wheel(root: Path, name: str, script: str) -> Path:
    stem = f"{name}-0.10.0"
    info = f"{stem}.dist-info"
    wheel = root / f"{stem}-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr(f"{name}.py", 'def main():\n    print("pdomain-ocr 0.10.0")\n')
        archive.writestr(
            f"{info}/METADATA", f"Metadata-Version: 2.1\nName: {name}\nVersion: 0.10.0\n"
        )
        archive.writestr(
            f"{info}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        )
        archive.writestr(f"{info}/entry_points.txt", f"[console_scripts]\n{script} = {name}:main\n")
        archive.writestr(f"{info}/RECORD", "")
    return wheel


@pytest.mark.parametrize("settings", ["keep-settings", "remove-settings"])
def test_setup_install_and_remove_use_cli_storage(tmp_path: Path, settings: str) -> None:
    uv = shutil.which("uv")
    assert uv is not None
    worker = tmp_path / "setup-worker.sh"
    _ = shutil.copyfile(WORKER, worker)
    _ = (tmp_path / "release-tag").write_text("v0.10.0\n")
    cli = _fixture_wheel(tmp_path, "pdomain_ocr_cli", "pdomain-ocr")
    gui = _fixture_wheel(tmp_path, "pdomain_ocr_gui", "pdomain-ocr-gui")
    tools = tmp_path / "tool storage"
    bin_dir = tmp_path / "launchers"
    config = tmp_path / "config"
    settings_file = config / "pdomain-ocr/update.toml"
    settings_file.parent.mkdir(parents=True)
    _ = settings_file.write_text("auto_check = true\n")
    other_settings = config / "pdomain-ocr/keep.toml"
    _ = other_settings.write_text("keep\n")
    cache = tmp_path / "shared model cache"
    cache.mkdir()
    model = cache / "model"
    _ = model.write_text("shared\n")
    env = {
        "HOME": str(tmp_path),
        "PATH": os.environ["PATH"],
        "UV_OFFLINE": "1",
        "UV_TOOL_DIR": str(tools),
        "UV_TOOL_BIN_DIR": str(bin_dir),
        "UV_CACHE_DIR": str(tmp_path / "uv cache"),
        "UV_INSTALL_DIR": str(Path(uv).parent),
        "UV_NO_MODIFY_PATH": "1",
        "XDG_CONFIG_HOME": str(config),
        "HF_HUB_CACHE": str(cache),
        "FIXTURE_UV": uv,
        "FIXTURE_PYTHON": sys.executable,
        "FIXTURE_WHEEL": str(cli),
    }
    _ = (tmp_path / "install.sh").write_text(
        '#!/bin/sh\nexec "$FIXTURE_UV" tool install --offline --no-config '
        '--python "$FIXTURE_PYTHON" "$FIXTURE_WHEEL"\n'
    )
    for command in (
        [uv, "tool", "install", "--offline", "--no-config", "--python", sys.executable, str(gui)],
        ["sh", str(worker), "install", "skip", "disabled"],
    ):
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
    launcher = bin_dir / "pdomain-ocr"
    receipt = tools / "pdomain-ocr-cli/uv-receipt.toml"
    assert launcher.is_file()
    assert receipt.is_file()
    backup = receipt.with_suffix(".backup")
    _ = receipt.rename(backup)
    receipt.symlink_to(backup)
    refused = subprocess.run(
        ["sh", str(worker), "remove", "remove-settings"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode != 0
    assert "Cannot verify the OCR CLI uv receipt" in refused.stderr
    assert launcher.is_file()
    assert settings_file.is_file()
    receipt.unlink()
    _ = backup.rename(receipt)
    preview = subprocess.run(
        ["sh", str(worker), "remove-preview"], env=env, capture_output=True, text=True, check=False
    )
    assert preview.returncode == 0, preview.stdout + preview.stderr
    for path in (launcher, receipt, settings_file, cache):
        assert str(path) in preview.stdout
    assert launcher.is_file()
    assert receipt.is_file()
    for _attempt in range(2):
        removal = subprocess.run(
            ["sh", str(worker), "remove", settings],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert removal.returncode == 0, removal.stdout + removal.stderr
        assert not launcher.exists()
        assert not launcher.is_symlink()
        assert not receipt.exists()
        assert (tools / "pdomain-ocr-gui/uv-receipt.toml").is_file()
        assert (bin_dir / "pdomain-ocr-gui").is_file()
        assert other_settings.is_file()
        assert model.is_file()
        assert settings_file.exists() == (settings == "keep-settings")
