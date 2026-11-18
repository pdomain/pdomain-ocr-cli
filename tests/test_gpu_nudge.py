"""Tests for the GPU-install nudge helpers in ``ocr_to_txt``.

The nudge fires on hosts that have an NVIDIA GPU (``nvidia-smi`` present
and exiting 0) but have the CPU build of PyTorch. It is opt-out via
``PD_OCR_NO_GPU_NUDGE=1`` and must NEVER raise — a bug in a printing
helper must not break ``pdomain-ocr`` itself.
"""

from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from pdomain_ocr_cli import ocr_to_txt


@pytest.fixture(autouse=True)
def _reset_nudge_cache(monkeypatch):
    """Clear the process-level cache between tests so each one starts fresh."""
    monkeypatch.setattr(ocr_to_txt, "_GPU_NUDGE_CACHE", {})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _install_fake_torch(monkeypatch: pytest.MonkeyPatch, *, cuda: bool) -> None:
    """Make ``import torch`` report a chosen CUDA availability."""
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: cuda))
    monkeypatch.setitem(sys.modules, "torch", torch)


def _hide_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``import torch`` raise ``ImportError``."""
    sys.modules.pop("torch", None)
    real_import = __import__

    def _import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch" or name.startswith("torch."):
            raise ImportError("no torch in this test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _import)


# ---------------------------------------------------------------------------
# _should_nudge_gpu_install
# ---------------------------------------------------------------------------


def test_nudge_skipped_when_cuda_torch_is_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """CUDA PyTorch means OCR already runs on the GPU."""
    _install_fake_torch(monkeypatch, cuda=True)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    def _no_subprocess(*args: object, **kwargs: object) -> object:
        raise AssertionError("subprocess.run must not be called when CUDA PyTorch is installed")

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _no_subprocess)

    assert ocr_to_txt._should_nudge_gpu_install() is False


def test_nudge_skipped_when_no_nvidia_smi(monkeypatch: pytest.MonkeyPatch) -> None:
    """No GPU on the host → no nudge."""
    _hide_torch(monkeypatch)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: None)
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    def _no_subprocess(*args: object, **kwargs: object) -> object:
        raise AssertionError("subprocess.run must not be called when nvidia-smi is absent")

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _no_subprocess)

    assert ocr_to_txt._should_nudge_gpu_install() is False


def test_nudge_fires_when_gpu_present_and_torch_is_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    """nvidia-smi present + CPU PyTorch → nudge."""
    _install_fake_torch(monkeypatch, cuda=False)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    def _ok_subprocess(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _ok_subprocess)

    assert ocr_to_txt._should_nudge_gpu_install() is True


def test_nudge_skipped_when_env_opt_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """``PD_OCR_NO_GPU_NUDGE=1`` short-circuits everything."""
    _install_fake_torch(monkeypatch, cuda=False)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.setenv("PD_OCR_NO_GPU_NUDGE", "1")

    def _no_subprocess(*args: object, **kwargs: object) -> object:
        raise AssertionError("subprocess.run must not be called when env opt-out is set")

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _no_subprocess)

    assert ocr_to_txt._should_nudge_gpu_install() is False


def test_nudge_skipped_when_subprocess_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """nvidia-smi exits non-zero (driver broken) → no nudge."""
    _install_fake_torch(monkeypatch, cuda=False)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    monkeypatch.setattr(
        ocr_to_txt.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=9),
    )

    assert ocr_to_txt._should_nudge_gpu_install() is False


def test_nudge_skipped_when_subprocess_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A subprocess error (TimeoutExpired, OSError) is treated as "no GPU"."""
    _install_fake_torch(monkeypatch, cuda=False)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    def _raise(*args: object, **kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="nvidia-smi", timeout=2)

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _raise)

    assert ocr_to_txt._should_nudge_gpu_install() is False


def test_nudge_skipped_when_subprocess_raises_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    """An OSError from subprocess.run (e.g. ENOENT under a race) is also swallowed."""
    _install_fake_torch(monkeypatch, cuda=False)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    def _raise(*args: object, **kwargs: object) -> object:
        raise OSError(2, "race lost: nvidia-smi vanished")

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _raise)

    assert ocr_to_txt._should_nudge_gpu_install() is False


def test_nudge_skipped_when_torch_import_explodes(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-ImportError raised by ``import torch`` is swallowed."""
    sys.modules.pop("torch", None)
    real_import = __import__

    def _import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch":
            raise RuntimeError("torch installed but its native lib fails on import")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _import)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    assert ocr_to_txt._should_nudge_gpu_install() is False


def test_nudge_fires_when_cuda_probe_is_not_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A torch install with no callable ``cuda.is_available`` counts as CPU-only."""
    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=None))
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    def _ok_subprocess(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _ok_subprocess)

    assert ocr_to_txt._should_nudge_gpu_install() is True


def test_nudge_skipped_when_cuda_probe_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A CUDA probe that raises is unknown, so the nudge stays off."""

    def _boom() -> bool:
        raise RuntimeError("cuda probe failed")

    torch = SimpleNamespace(cuda=SimpleNamespace(is_available=_boom))
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    def _no_subprocess(*args: object, **kwargs: object) -> object:
        raise AssertionError("subprocess.run must not be called when the CUDA probe fails")

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _no_subprocess)

    assert ocr_to_txt._should_nudge_gpu_install() is False


def test_nudge_result_cached_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """The probe runs at most once per process — second call uses the cache."""
    _install_fake_torch(monkeypatch, cuda=False)
    monkeypatch.setattr(ocr_to_txt.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    call_count = {"n": 0}

    def _counting_run(*args: object, **kwargs: object) -> SimpleNamespace:
        call_count["n"] += 1
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ocr_to_txt.subprocess, "run", _counting_run)

    assert ocr_to_txt._should_nudge_gpu_install() is True
    assert ocr_to_txt._should_nudge_gpu_install() is True
    assert call_count["n"] == 1, "second call must hit the cache, not re-spawn nvidia-smi"


def test_nudge_outer_guard_swallows_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """If ``shutil.which`` itself raises, the helper still returns False."""
    _install_fake_torch(monkeypatch, cuda=False)

    def _boom(name: str) -> str:
        raise RuntimeError("PATH is on fire")

    monkeypatch.setattr(ocr_to_txt.shutil, "which", _boom)
    monkeypatch.delenv("PD_OCR_NO_GPU_NUDGE", raising=False)

    assert ocr_to_txt._should_nudge_gpu_install() is False


# ---------------------------------------------------------------------------
# _maybe_print_gpu_nudge
# ---------------------------------------------------------------------------


def test_maybe_print_emits_to_stderr_when_nudging(monkeypatch, capsys):
    monkeypatch.setattr(ocr_to_txt, "_should_nudge_gpu_install", lambda: True)

    ocr_to_txt._maybe_print_gpu_nudge()

    err = capsys.readouterr().err
    assert "NVIDIA GPU detected" in err
    # The canonical install path is the install script (not pip); the
    # nudge points the user at re-running install.sh to swap CPU→GPU.
    assert "install.sh" in err
    assert "PD_OCR_NO_GPU_NUDGE" in err


def test_maybe_print_silent_when_not_nudging(monkeypatch, capsys):
    monkeypatch.setattr(ocr_to_txt, "_should_nudge_gpu_install", lambda: False)

    ocr_to_txt._maybe_print_gpu_nudge()

    assert capsys.readouterr().err == ""


def test_maybe_print_swallows_helper_exceptions(monkeypatch, capsys):
    """A bug in ``_should_nudge_gpu_install`` must not break ``pdomain-ocr``."""

    def _broken():
        raise RuntimeError("nudge helper bug")

    monkeypatch.setattr(ocr_to_txt, "_should_nudge_gpu_install", _broken)

    # Must not raise.
    ocr_to_txt._maybe_print_gpu_nudge()
    assert capsys.readouterr().err == ""
