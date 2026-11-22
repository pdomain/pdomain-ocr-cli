from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

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
