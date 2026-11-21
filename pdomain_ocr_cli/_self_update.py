"""Explicit release checks and updates for uv-managed OCR CLI installs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import cast

from pdomain_ops.suite.update import compare_versions, is_editable_install

from pdomain_ocr_cli._startup_notices import save_auto_update_check
from pdomain_ocr_cli._update_check import VERSION, UrlopenResponse, parse_stable_tag

_DIST = "pdomain-ocr-cli"
_RELEASE_URL = "https://api.github.com/repos/pdomain/pdomain-ocr-cli/releases/latest"
_INSTALLERS = Path(__file__).with_name("_installers")
_WINDOWS_HANDOFF = """\
param([int]$CliPid, [int]$LauncherPid)
$ErrorActionPreference = 'Stop'
try {
    $launcher = Get-Process -Id $LauncherPid -ErrorAction SilentlyContinue
    $cli = Get-Process -Id $CliPid -ErrorAction SilentlyContinue
    if ($cli -and -not $cli.WaitForExit(60000)) {
        throw 'The OCR CLI did not exit. Run the update again.'
    }
    if ($launcher -and $launcher.ProcessName -eq 'pdomain-ocr' -and
        -not $launcher.WaitForExit(60000)) {
        throw 'The OCR launcher did not exit. Run the update again.'
    }
    & (Join-Path $PSScriptRoot 'install.ps1')
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
} finally {
    Remove-Item -LiteralPath $PSScriptRoot -Recurse -Force
}
"""


def _latest_release_tag() -> str:
    request = urllib.request.Request(
        _RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{_DIST}/{VERSION}",
        },
    )
    opened = cast("UrlopenResponse", urllib.request.urlopen(request, timeout=10))  # noqa: S310  # Fixed HTTPS endpoint.
    with opened as response:
        payload = cast("object", json.loads(response.read()))
    if not isinstance(payload, dict):
        raise TypeError("GitHub did not return a release object.")
    release = cast("dict[str, object]", payload)
    tag = release.get("tag_name")
    if not isinstance(tag, str) or parse_stable_tag(tag) is None:
        raise ValueError("GitHub did not return a stable release tag.")
    return tag


def _program(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise FileNotFoundError(f"{name} is not on PATH.")
    return executable


def _is_managed_install() -> bool:
    if is_editable_install(_DIST):
        return False
    result = subprocess.run(  # noqa: S603  # Resolved uv executable, fixed arguments.
        [_program("uv"), "tool", "dir"],
        check=True,
        capture_output=True,
        text=True,
    )
    tool_dir = result.stdout.strip()
    prefix = Path(sys.prefix).resolve()
    return (
        bool(tool_dir)
        and prefix == (Path(tool_dir) / _DIST).resolve()
        and (prefix / "uv-receipt.toml").is_file()
    )


def _apply_windows(installer: Path, env: dict[str, str]) -> int:
    shell = _program("powershell.exe")
    directory = Path(tempfile.mkdtemp(prefix="pdomain-ocr-update-"))
    try:
        _ = shutil.copyfile(installer, directory / installer.name)
        handoff = directory / "handoff.ps1"
        _ = handoff.write_text(_WINDOWS_HANDOFF, encoding="utf-8")
        # The launcher and interpreter must exit before uv can replace them.
        _ = subprocess.Popen(  # noqa: S603  # Fixed command and local bundled scripts.
            [
                shell,
                "-NoProfile",
                "-ExecutionPolicy",
                "RemoteSigned",
                "-File",
                str(handoff),
                str(os.getpid()),
                str(os.getppid()),
            ],
            env=env,
        )
    except OSError:
        shutil.rmtree(directory)
        raise
    print("Update handed off. The installer will run after this command exits.", flush=True)  # noqa: T201
    return 0


def _apply_release(tag: str) -> int:
    env = os.environ.copy()
    _ = env.pop("PD_OCR_INSTALL_AUTO_UPDATE_CHECK", None)
    env["PDOMAIN_OCR_EXPECTED_RELEASE_TAG"] = tag
    _ = env.setdefault(
        "PD_OCR_INSTALL_PYTHON", f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    windows = sys.platform == "win32"
    installer = _INSTALLERS / ("install.ps1" if windows else "install.sh")
    if not installer.is_file():
        raise FileNotFoundError("The bundled installer is missing. Reinstall pdomain-ocr.")
    if windows:
        return _apply_windows(installer, env)
    return subprocess.run(  # noqa: S603  # Fixed shell and locally bundled installer.
        [_program("sh"), str(installer)],
        env=env,
        check=False,
    ).returncode


def _fail(message: object) -> int:
    print(f"Update failed: {message}", file=sys.stderr)  # noqa: T201
    return 1


def run_update(argv: list[str]) -> int:
    """Check for an update and apply it only after approval."""
    parser = argparse.ArgumentParser(prog="pdomain-ocr update", description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    _ = mode.add_argument("--check", action="store_true", help="Check without installing.")
    _ = mode.add_argument("--yes", action="store_true", help="Install without prompting.")
    _ = mode.add_argument(
        "--auto-check", choices=("on", "off"), help="Save a preference for automatic checks."
    )
    args = parser.parse_args(argv)
    try:
        preference = cast("str | None", args.auto_check)
        if preference is not None:
            path = save_auto_update_check(enabled=preference == "on")
            print(f"Automatic update checks: {preference}. Preference saved in {path}.")  # noqa: T201
            return 0
        tag = _latest_release_tag()
        latest = tag.removeprefix("v")
        available = compare_versions(current=VERSION, latest=latest)
        print(f"Installed: {VERSION}. Latest release: {latest}.", flush=True)  # noqa: T201
        if not available:
            print("pdomain-ocr is up to date.")  # noqa: T201
            return 0
        if cast("bool", args.check):
            print("An update is available. Run pdomain-ocr update to install it.")  # noqa: T201
            return 0
        if not _is_managed_install():
            return _fail(
                "Use the original installer or package manager to update this installation."
            )
        if not cast("bool", args.yes):
            if not sys.stdin.isatty():
                return _fail("Use --yes to update without an interactive terminal.")
            if input(f"Install {tag}? [y/N] ").strip().lower() not in {"y", "yes"}:
                print("Update canceled.")  # noqa: T201
                return 0
        return _apply_release(tag)
    except (EOFError, KeyboardInterrupt):
        print("Update canceled.", file=sys.stderr)  # noqa: T201
        return 130
    except (OSError, ValueError, TypeError, subprocess.CalledProcessError) as exc:
        return _fail(exc)
