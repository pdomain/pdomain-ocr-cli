"""Enter the bundled POSIX uninstall flow from the CLI launcher."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NoReturn


def run_terminal_uninstall(
    arguments: list[str],
    *,
    execute: Callable[[str, list[str], dict[str, str]], NoReturn] = os.execve,
) -> int:
    """Replace the CLI process before removing its uv tool environment."""
    if os.name != "posix":
        print("Terminal uninstall is currently available on macOS and Linux.", file=sys.stderr)  # noqa: T201
        return 2
    prefix = Path(sys.prefix).resolve()
    if prefix.name != "pdomain-ocr-cli" or not (prefix / "uv-receipt.toml").is_file():
        print("Run this command from the OCR CLI installed by uv.", file=sys.stderr)  # noqa: T201
        return 2
    worker = Path(__file__).resolve().parent / "_installers/setup-worker.sh"
    environment = {**os.environ, "PDOMAIN_OCR_EXPECTED_TOOL_ENV": str(prefix)}
    return execute("/bin/sh", ["sh", str(worker), "terminal-uninstall", *arguments], environment)
