"""Prepare an isolated uv environment for relocation during a CLI update."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tomllib
from configparser import ConfigParser
from configparser import Error as ConfigError
from pathlib import Path
from typing import cast
from zipfile import BadZipFile, ZipFile

_DIST = "pdomain-ocr-cli"
_COMMAND = "pdomain-ocr"
_ENTRY_POINT = "pdomain_ocr_cli.ocr_to_txt:main"
_INDEX = "pdomain=https://pdomain.github.io/pdomain-index-pip/simple/"
_WHEEL_NAME = re.compile(r"pdomain_ocr_cli-[a-zA-Z0-9_.+]+-[a-zA-Z0-9_.+-]+\.whl")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_INSTALL_PATH = re.compile(
    r'(?<![\w-])install-path[ \t]*=[ \t]*(?P<value>"(?:[^"\\\r\n]|\\.)*"' + r"|'[^'\r\n]*')"
)


def _run(argv: list[str], *, env: dict[str, str], directory: Path, timeout: int) -> None:
    try:
        # The shell and uv are resolved executables. Arguments refer to the private stage.
        _ = subprocess.run(  # noqa: S603
            argv, env=env, cwd=directory, check=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as err:
        raise OSError(f"Update preparation timed out after {timeout} seconds.") from err


def _installer_command(installer: Path, env: dict[str, str], *, windows: bool) -> list[str]:
    shell_name = "powershell.exe" if windows else "sh"
    shell = shutil.which(shell_name, path=env.get("PATH"))
    if shell is None:
        raise FileNotFoundError(f"{shell_name} is not on PATH.")
    if windows:
        return [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "RemoteSigned",
            "-File",
            str(installer),
        ]
    return [shell, str(installer)]


def _read_release(release: Path, expected_python: str) -> tuple[Path, bool]:
    record = release / "candidate"
    if release.is_symlink() or record.is_symlink():
        raise ValueError("Unexpected link in the update candidate record.")
    values = record.read_text(encoding="ascii").splitlines()
    if len(values) != 4:
        raise ValueError("Invalid update candidate record.")
    name, python, backend, digest = values
    if (
        not _WHEEL_NAME.fullmatch(name)
        or python != expected_python
        or backend not in {"", "auto"}
        or not _SHA256.fullmatch(digest)
    ):
        raise ValueError("Invalid update candidate record.")
    wheel = release / name
    if wheel.is_symlink() or not wheel.is_file():
        raise ValueError("Missing or unsupported wheel in the update candidate record.")
    with wheel.open("r+b") as contents:
        actual = hashlib.file_digest(contents, "sha256").hexdigest()
        os.fsync(contents.fileno())
    if actual != digest:
        raise ValueError("Staged wheel digest mismatch.")
    return wheel, backend == "auto"


def _check_launcher_target(wheel: Path) -> None:
    distribution, version, _ = wheel.name.split("-", 2)
    filename = f"{distribution}-{version}.dist-info/entry_points.txt"
    entry_points = ConfigParser(interpolation=None)
    entry_points.optionxform = lambda optionstr: optionstr
    try:
        with ZipFile(wheel) as archive:
            if archive.namelist().count(filename) != 1:
                raise ValueError("Expected one console entry point record in the update wheel.")
            entry_points.read_string(archive.read(filename).decode("utf-8"))
    except (BadZipFile, ConfigError, UnicodeDecodeError) as err:
        raise ValueError("Could not read the update wheel's console entry point.") from err
    if not entry_points.has_section("console_scripts") or dict(entry_points["console_scripts"]) != {
        _COMMAND: _ENTRY_POINT
    }:
        raise ValueError("The update wheel changed the retained console entry point.")


def _entrypoint(data: dict[str, object]) -> dict[str, object]:
    tool = data.get("tool")
    if not isinstance(tool, dict):
        raise TypeError("Missing tool in the staged uv receipt.")
    raw = cast("dict[str, object]", tool).get("entrypoints")
    if not isinstance(raw, list):
        raise TypeError("Expected an entry point list in the staged uv receipt.")
    records = cast("list[object]", raw)
    if len(records) != 1:
        raise ValueError("Expected one entry point in the staged uv receipt.")
    entry = records[0]
    if not isinstance(entry, dict):
        raise TypeError("Invalid entry point in the staged uv receipt.")
    return cast("dict[str, object]", entry)


def _retarget_receipt(receipt: Path, staged_launcher: Path, live_launcher: Path) -> None:
    if receipt.is_symlink():
        raise ValueError("Unexpected link in the staged uv receipt.")
    raw = receipt.read_bytes().decode("utf-8")
    data: dict[str, object] = tomllib.loads(raw)
    entry = _entrypoint(data)
    installed = entry.get("install-path")
    if (
        entry.get("name") != _COMMAND
        or entry.get("from") != _DIST
        or not isinstance(installed, str)
        or Path(installed) != staged_launcher
    ):
        raise ValueError("Unexpected entry point in the staged uv receipt.")

    matches = list(_INSTALL_PATH.finditer(raw))
    if len(matches) != 1:
        raise ValueError("Unsupported install-path syntax in the staged uv receipt.")
    start, end = matches[0].span("value")
    live_path = str(live_launcher)
    updated = raw[:start] + json.dumps(live_path, ensure_ascii=False) + raw[end:]
    entry["install-path"] = live_path
    if tomllib.loads(updated) != data:
        raise ValueError("Failed to retarget the staged uv receipt.")
    with receipt.open("wb") as contents:
        _ = contents.write(updated.encode("utf-8"))
        contents.flush()
        os.fsync(contents.fileno())


def prepare_candidate(
    uv: str, installer: Path, directory: Path, env: dict[str, str], live_launcher: Path
) -> Path:
    """Install a verified wheel in an isolated relocatable environment."""
    if not env.get("PDOMAIN_OCR_EXPECTED_RELEASE_TAG"):
        raise ValueError("Candidate preparation requires an approved release tag.")
    if not directory.is_absolute() or not directory.is_dir() or directory.is_symlink():
        raise ValueError("Candidate preparation requires a private staging directory.")
    if not live_launcher.is_absolute() or live_launcher.name not in {_COMMAND, f"{_COMMAND}.exe"}:
        raise ValueError("Expected an absolute path to the installed OCR launcher.")
    release = directory / "release"
    tools = directory / "tools"
    launchers = directory / "bin"
    if any(path.exists() or path.is_symlink() for path in (release, tools, launchers)):
        raise ValueError("Candidate staging paths already exist.")

    windows = installer.suffix == ".ps1"
    isolated = env | {"UV_TOOL_DIR": str(tools), "UV_TOOL_BIN_DIR": str(launchers)}
    command = _installer_command(installer, env, windows=windows)
    flag = "-PrepareUpdate" if windows else "--prepare-update"
    _run([*command, flag, str(release)], env=isolated, directory=directory, timeout=300)
    python = env.get("PD_OCR_INSTALL_PYTHON") or "3.13"
    wheel, auto_backend = _read_release(release, python)
    _check_launcher_target(wheel)

    environment = tools / _DIST
    _run(
        [uv, "venv", "--relocatable", "--python", python, str(environment)],
        env=isolated,
        directory=directory,
        timeout=300,
    )
    install = [
        uv,
        "tool",
        "install",
        "--python",
        python,
        "--index-strategy",
        "first-index",
        "--index",
        _INDEX,
        str(wheel),
    ]
    if auto_backend:
        install.extend(("--torch-backend", "auto"))
    _run(install, env=isolated, directory=directory, timeout=1800)

    config = (environment / "pyvenv.cfg").read_text(encoding="utf-8")
    settings = {
        key.strip(): value.strip()
        for line in config.splitlines()
        for key, _, value in [line.partition("=")]
    }
    if settings.get("relocatable") != "true":
        raise ValueError("uv did not retain the relocatable candidate environment.")
    _retarget_receipt(
        environment / "uv-receipt.toml", launchers / live_launcher.name, live_launcher
    )
    if windows:
        _run(
            [*command, "-CheckStagedRuntime", str(environment)],
            env=isolated,
            directory=directory,
            timeout=300,
        )
    return environment
