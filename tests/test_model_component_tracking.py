"""Exercise the CLI prefetch entry point with the shared registry."""

import os
import shutil
import subprocess
import sys
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

import pytest
from huggingface_hub import constants

from pdomain_ocr_cli import _hf_models


@pytest.mark.parametrize("missing", ["pdomain_ops.suite.model_components", "filelock"])
def test_prefetch_only_falls_back_for_older_ops(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    def load(name: str) -> object:
        if name == "pdomain_ops.suite.model_components":
            raise ModuleNotFoundError(name=missing)
        return import_module(name)

    def download(**_kwargs: object) -> tuple[Path, Path]:
        return Path("det"), Path("rec")

    monkeypatch.setattr(_hf_models.importlib, "import_module", load)
    monkeypatch.setattr(_hf_models, "_resolve_ocr_models_kwargs", download)
    if missing == "filelock":
        with pytest.raises(ModuleNotFoundError):
            _hf_models.prefetch_default_models(revision="a" * 40, layout_model="none")
    else:
        _hf_models.prefetch_default_models(revision="a" * 40, layout_model="none")


def test_layout_prefetch_tracks_in_runtime_and_falls_back_for_custom_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if find_spec("pdomain_ops.suite.model_components") is None:
        pytest.skip("shared registry is not available in this environment")
    cache = tmp_path / "cache"
    suite = tmp_path / "suite"
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(suite))
    monkeypatch.delenv("PDOMAIN_OCR_MODEL_SOURCE", raising=False)
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(cache))
    revision = "b" * 40
    calls: list[str] = []

    def download(repo: str, _revision: str) -> None:
        calls.append(repo)
        if repo == "pdomain/layout":
            entry = (
                cache
                / "models--pdomain--layout"
                / "snapshots"
                / revision
                / _hf_models.LAYOUT_MODEL_FILES[0]
            )
            entry.parent.mkdir(parents=True)
            entry.touch()

    monkeypatch.setattr(_hf_models._HF, "prefetch_layout_files", download)
    _ = _hf_models.prefetch_layout_files("pdomain/layout", revision)
    _ = _hf_models.prefetch_layout_files("/custom/config", revision)
    assert calls == ["pdomain/layout", "/custom/config"]
    assert '"source": "runtime"' in (suite / "components.json").read_text()
    monkeypatch.setattr(constants, "HF_HUB_CACHE", None)
    with pytest.raises(TypeError, match="model cache path"):
        _ = _hf_models.prefetch_layout_files("pdomain/layout", revision)


def test_prefetch_records_only_new_pinned_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if find_spec("pdomain_ops.suite.model_components") is None:
        pytest.skip("shared registry is not available in this environment")
    revision = "a" * 40
    cache = tmp_path / "cache"
    suite = tmp_path / "suite"
    snapshot = cache / "models--pdomain--pdomain-ocr-models" / "snapshots" / revision
    existing = snapshot / _hf_models.DEFAULT_DET_FILENAME
    created = snapshot / _hf_models.DEFAULT_RECO_FILENAME
    existing.parent.mkdir(parents=True)
    _ = existing.write_bytes(b"external")
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(cache))
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(suite))
    monkeypatch.setenv("PDOMAIN_OCR_MODEL_SOURCE", "installer")

    def download(**_kwargs: object) -> tuple[Path, Path]:
        created.parent.mkdir(parents=True)
        _ = created.write_bytes(b"download")
        return existing, created

    monkeypatch.setattr(_hf_models, "_resolve_ocr_models_kwargs", download)
    _hf_models.prefetch_default_models(revision=revision, layout_model="none")
    record = (suite / "components.json").read_text()
    assert created.name in record
    assert existing.name not in record
    assert '"installed_by": "pdomain-ocr-cli"' in record
    assert '"source": "installer"' in record

    tool = tmp_path / "tools/pdomain-ocr-cli"
    python = tool / "bin/python"
    python.parent.mkdir(parents=True)
    (tool / "uv-receipt.toml").touch()
    _ = python.write_text('#!/bin/sh\nshift\nexec "$TEST_PYTHON" "$@"\n')
    python.chmod(0o755)
    uv = tmp_path / "uv"
    _ = uv.write_text(
        '#!/bin/sh\nif [ "$2" = uninstall ]; then\n'
        '    rm -f "$TEST_TOOL_DIR/pdomain-ocr-cli/uv-receipt.toml"\n'
        'else\n    printf "%s\\n" "$TEST_TOOL_DIR"\nfi\n'
    )
    uv.chmod(0o755)
    worker = Path(__file__).resolve().parents[1] / "installer/macos/setup-worker.sh"

    def run_worker(*args: str, answer: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", str(worker), *args],
            input=answer,
            env={
                **os.environ,
                "HOME": str(tmp_path),
                "UV_UNMANAGED_INSTALL": str(tmp_path),
                "TEST_TOOL_DIR": str(tool.parent),
                "TEST_PYTHON": sys.executable,
                "HF_HUB_CACHE": str(cache),
            },
            text=True,
            capture_output=True,
            check=False,
        )

    result = run_worker("remove-preview")
    assert result.returncode == 0, result.stderr
    assert f"  {created}" in result.stdout
    assert str(existing) not in result.stdout
    assert created.is_file()
    marker = "OCR_SETUP_MODEL_TOKEN "
    (token,) = (
        line.removeprefix(marker) for line in result.stdout.splitlines() if line.startswith(marker)
    )
    sibling = tool.parent / "pdomain-ocr-simple-gui"
    sibling.mkdir()
    assert run_worker("remove", "keep-settings", token).returncode != 0
    assert created.is_file()
    sibling.rmdir()
    assert run_worker("remove", "keep-settings", "0" * 64).returncode != 0
    assert created.is_file()
    terminal_preview = run_worker("terminal-uninstall", "--preview")
    assert terminal_preview.returncode == 0, terminal_preview.stderr
    assert str(created) in terminal_preview.stdout
    assert "OCR_SETUP_MODEL_TOKEN" not in terminal_preview.stdout
    cancellation = run_worker("terminal-uninstall", "--remove-models", answer="no\n")
    assert cancellation.returncode == 0, cancellation.stderr
    assert created.is_file()
    outcome = run_worker("terminal-uninstall", "--remove-models", answer="REMOVE\n")
    assert outcome.returncode == 0, outcome.stderr
    assert not created.exists()
    assert existing.read_bytes() == b"external"


def test_setup_records_fresh_uv_only_after_staging(tmp_path: Path) -> None:
    if find_spec("pdomain_ops.suite.model_components") is None:
        pytest.skip("shared registry is not available in this environment")
    worker = tmp_path / "setup-worker.sh"
    source = Path(__file__).resolve().parents[1] / "installer/macos/setup-worker.sh"
    _ = shutil.copyfile(source, worker)
    _ = (tmp_path / "release-tag").write_text("v0.10.0\n")
    _ = (tmp_path / "install.sh").write_text(
        """#!/bin/sh
set -eu
uv --color never python install --no-bin 3.13
"$TEST_PYTHON" - "$TEST_BASE" "$TEST_PYTHON_ROOT" <<'PY'
import sys
from pathlib import Path
from pdomain_ops.suite.components import ComponentProbe, ComponentRegistry
from pdomain_ops.suite.python_components import ManagedPython
base, root = map(Path, sys.argv[1:])
item = ManagedPython(root, base.parents[1].name, base)
assert ComponentRegistry().record_created(
    "pdomain-ocr-cli", "installer", ComponentProbe("python", item.identity, item.fingerprint), item.fingerprint()
)
PY
"""
    )
    tool_bin = tmp_path / "launchers"
    managed_uv_bin = tmp_path / "uv bin"
    python = tmp_path / "tools/pdomain-ocr-cli/bin/python"
    python.parent.mkdir(parents=True)
    (python.parents[1] / "uv-receipt.toml").touch()
    _ = python.write_text(
        """#!/bin/sh
shift
exec "$TEST_PYTHON" -c 'import os, sys
sys._base_executable = os.environ["TEST_BASE"]
sys.argv = sys.argv[1:]
exec(sys.stdin.read())' "$@"
"""
    )
    python.chmod(0o755)
    tool_bin.mkdir()
    launcher = tool_bin / "pdomain-ocr"
    _ = launcher.write_text('#!/bin/sh\n[ "$1" != --version ] || echo "pdomain-ocr 0.10.0"\n')
    launcher.chmod(0o755)
    fixture_bin = tmp_path / "fixture"
    fixture_bin.mkdir()
    curl = fixture_bin / "curl"
    _ = curl.write_text(
        """#!/bin/sh
cat > "$4" <<'INSTALL'
#!/bin/sh
cat > "$UV_UNMANAGED_INSTALL/uv" <<'UV'
#!/bin/sh
case "$*" in
    'tool dir') printf '%s\\n' "$TEST_TOOLS" ;;
    'tool dir --bin') printf '%s\\n' "$TEST_BIN" ;;
    'python dir') printf '%s\\n' "$TEST_PYTHON_ROOT" ;;
    'python find --no-project --no-python-downloads -- 3.13'|\
    'python find --no-project --no-python-downloads --managed-python -- 3.13')
        [ -x "$TEST_BASE" ] || exit 1
        printf '%s\\n' "$TEST_BASE"
        ;;
    '--color never python install --no-bin 3.13')
        mkdir -p "$(dirname "$TEST_BASE")"
        cp "$TEST_TOOLS/pdomain-ocr-cli/bin/python" "$TEST_BASE"
        printf '%s\\n' 'Installed Python 3.13.14 in 1s' ' + cpython-3.13.14-linux-x86_64-gnu'
        ;;
    'tool uninstall --offline pdomain-ocr-cli')
        tool="$TEST_TOOLS/pdomain-ocr-cli"
        rm -f "$tool/bin/python" "$tool/uv-receipt.toml" "$TEST_BIN/pdomain-ocr"
        rmdir "$tool/bin" "$tool"
        ;;
    "--offline python uninstall --install-dir $TEST_PYTHON_ROOT cpython-3.13.14-linux-x86_64-gnu")
        rm -f "$TEST_BASE"
        rmdir "$(dirname "$TEST_BASE")" "$(dirname "$(dirname "$TEST_BASE")")"
        ;;
    *) exit 2 ;;
esac
UV
chmod 700 "$UV_UNMANAGED_INSTALL/uv"
INSTALL
"""
    )
    curl.chmod(0o755)
    suite = tmp_path / "suite"
    python_root = tmp_path / "managed-python"
    base = python_root / "cpython-3.13.14-linux-x86_64-gnu/bin/python3.13"

    def run_worker(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/sh", str(worker), *args],
            env={
                "PATH": f"{fixture_bin}:/usr/bin:/bin",
                "HOME": str(tmp_path),
                "UV_UNMANAGED_INSTALL": str(managed_uv_bin),
                "TEST_TOOLS": str(python.parents[2]),
                "TEST_BIN": str(tool_bin),
                "TEST_PYTHON": sys.executable,
                "TEST_BASE": str(base),
                "TEST_PYTHON_ROOT": str(python_root),
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "PD_SUITE_DATA_DIR": str(suite),
            },
            capture_output=True,
            text=True,
            check=False,
        )

    result = run_worker("install", "skip", "disabled")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (managed_uv_bin / "uv").is_file()
    assert not list(managed_uv_bin.glob(".ocr-uv.*"))
    record = (suite / "components.json").read_text()
    assert '"installed_by": "pdomain-ocr-cli"' in record
    assert '"kind": "python"' in record
    preview = run_worker("remove-preview")
    assert preview.returncode == 0, preview.stderr
    marker = "OCR_SETUP_UV_TOKEN "
    (token,) = (
        line.removeprefix(marker) for line in preview.stdout.splitlines() if line.startswith(marker)
    )
    python_marker = "OCR_SETUP_PYTHON_TOKEN "
    (python_token,) = (
        line.removeprefix(python_marker)
        for line in preview.stdout.splitlines()
        if line.startswith(python_marker)
    )
    other_tool = python.parents[2] / "unrelated-tool"
    other_tool.mkdir()
    assert run_worker("remove", "keep-settings", "", token).returncode != 0
    assert (managed_uv_bin / "uv").is_file()
    other_tool.rmdir()
    removal = run_worker("remove", "keep-settings", "", token, python_token)
    assert removal.returncode == 0, removal.stderr
    assert not (managed_uv_bin / "uv").exists()
    assert not base.exists()
    assert not (suite / "components.json").exists()
