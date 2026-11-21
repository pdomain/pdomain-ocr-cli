from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable


class UpdateArgs(Protocol):
    no_update_check: bool


def env_truthy(name: str) -> bool:
    """True when an environment variable uses a common opt-in value."""
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def update_check_disabled(args: UpdateArgs) -> bool:
    if args.no_update_check or env_truthy("PD_OCR_NO_UPDATE_CHECK"):
        return True

    override = os.environ.get("PD_OCR_AUTO_UPDATE_CHECK", "").strip().lower()
    if override in ("1", "true", "yes", "on"):
        return False
    if override in ("0", "false", "no", "off"):
        return True

    try:
        with _update_settings_path().open("rb") as settings:
            return tomllib.load(settings).get("auto_check") is not True
    except (OSError, ValueError):
        return True


def _update_settings_path() -> Path:
    base = os.environ.get("APPDATA" if sys.platform == "win32" else "XDG_CONFIG_HOME")
    if base:
        return Path(base) / "pdomain-ocr" / "update.toml"
    home = Path.home()
    config_dir = home / "AppData" / "Roaming" if sys.platform == "win32" else home / ".config"
    return config_dir / "pdomain-ocr" / "update.toml"


def save_auto_update_check(*, enabled: bool) -> Path:
    """Persist the automatic update check preference."""
    path = _update_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        temporary = Path(directory) / path.name
        _ = temporary.write_text(f"auto_check = {str(enabled).lower()}\n", encoding="utf-8")
        _ = temporary.replace(path)
    return path


def start_update_check_thread(
    *,
    disabled: bool,
    check_for_update: Callable[[], None],
) -> threading.Thread | None:
    if disabled:
        return None
    thread = threading.Thread(target=check_for_update, daemon=True)
    thread.start()
    return thread


# Process-cached so repeated main() calls do not respawn nvidia-smi.
GPU_NUDGE_CACHE: dict[str, bool] = {}


def _cuda_torch_installed() -> bool | None:
    """Return whether this install can run OCR on CUDA.

    ``False`` means PyTorch is missing or has no CUDA build. ``None`` means
    the import itself failed for a reason other than ``ImportError``.
    """
    try:
        import torch
    except ImportError:
        return False
    except BaseException:  # noqa: BLE001  # a broken torch install must not crash startup
        return None
    try:
        cuda = getattr(torch, "cuda", None)
        is_available = getattr(cuda, "is_available", None)
        if not callable(is_available):
            return False
        return bool(is_available())
    except BaseException:  # noqa: BLE001  # a broken CUDA probe must not crash startup
        return None


def should_nudge_gpu_install(cache: dict[str, bool] | None = None) -> bool:
    """Return True when an NVIDIA host has the CPU build of PyTorch."""
    cache = GPU_NUDGE_CACHE if cache is None else cache
    if "result" in cache:
        return cache["result"]

    def _probe() -> bool:
        if env_truthy("PD_OCR_NO_GPU_NUDGE"):
            return False
        cuda_torch = _cuda_torch_installed()
        if cuda_torch is None or cuda_torch:
            return False

        if shutil.which("nvidia-smi") is None:
            return False
        try:
            proc = subprocess.run(
                ["nvidia-smi"],  # noqa: S607  # nvidia-smi is intentionally resolved from PATH
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0

    try:
        result = _probe()
    except BaseException:  # noqa: BLE001  # the nudge helper must never break OCR startup
        result = False
    cache["result"] = result
    return result


def maybe_print_gpu_nudge(
    should_nudge: Callable[[], bool] = should_nudge_gpu_install,
) -> None:
    """Print the GPU-install nudge when applicable, never raising."""
    try:
        if should_nudge():
            print(  # noqa: T201  # CLI output
                (
                    "pdomain-ocr: NVIDIA GPU detected but PyTorch is the CPU build.\n"
                    + "        Re-run the install script to install the CUDA build of PyTorch:\n"
                    + "          curl -sSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh | sh\n"
                    + "        Set PD_OCR_NO_GPU_NUDGE=1 to silence this message."
                ),
                file=sys.stderr,
            )
    except BaseException:  # noqa: BLE001 S110  # notice helper must never crash pdomain-ocr
        pass
