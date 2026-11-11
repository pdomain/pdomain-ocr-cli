from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The fake Invoke-WebRequest below writes exactly these bytes (no trailing
# newline: -NoNewline) to the wheel file it is asked to download, so tests
# can assert digest verification against a known hash without hardcoding a
# magic value.
FAKE_WHEEL_BYTES = b"fake wheel"
FAKE_WHEEL_DIGEST = f"sha256:{hashlib.sha256(FAKE_WHEEL_BYTES).hexdigest()}"
MISMATCHED_DIGEST = f"sha256:{hashlib.sha256(b'different bytes').hexdigest()}"


def _write_fake_exe(path: Path, body: str) -> None:
    _ = path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _run_install_ps1(
    tmp_path: Path, digest_property: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    result, uv_log, _perm_log = _run_install_ps1_full(tmp_path, digest_property)
    return result, uv_log


def _run_install_ps1_full(
    tmp_path: Path, digest_property: str, umask: int | None = None
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    """Run install.ps1 through pwsh with mocked GitHub API + uv + nvidia-smi.

    `digest_property` is inserted verbatim as a property assignment inside
    the mocked asset's `[pscustomobject]@{ ... }` literal, e.g.
    `digest = "sha256:..."` — pass "" to omit the digest property entirely
    (PowerShell then reports `$asset.digest` as `$null`).

    `umask`, if given, is set on the pwsh subprocess before exec (POSIX
    only), to prove a permission fix doesn't merely inherit a strict
    default from the test environment.

    Returns (result, uv_log, perm_log). `perm_log`, written by the fake
    `uv`, holds the octal permission bits of the temp dir holding the wheel
    file at the moment `uv` was invoked (before install.ps1's `finally`
    block deletes it) — the last point at which those permissions matter.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv_log = tmp_path / "uv.log"
    perm_log = tmp_path / "perm.log"

    _write_fake_exe(
        bin_dir / "uv",
        f"""#!/bin/sh
printf '%s\\n' "$@" > {uv_log}
for a in "$@"; do
  if [ -f "$a" ]; then
    stat -c '%a' "$(dirname "$a")" > {perm_log} 2>/dev/null || true
    break
  fi
done
exit 0
""",
    )
    _write_fake_exe(
        bin_dir / "nvidia-smi",
        """#!/bin/sh
printf '%s\\n' 'CUDA Version                          : 12.4'
exit 0
""",
    )

    script = (REPO / "install.ps1").read_text(encoding="utf-8")
    escaped_script = script.replace("'@", "' + \"@\" + '")
    harness = tmp_path / "run.ps1"
    _ = harness.write_text(
        f"""
$ErrorActionPreference = "Stop"
function Invoke-RestMethod {{
  param([string]$Uri)
  if ($Uri -like "*api.github.com/repos/pdomain/pdomain-ocr-cli/releases/latest*") {{
    return [pscustomobject]@{{
      tag_name = "v9.9.9"
      assets = @([pscustomobject]@{{
        name = "pdomain_ocr_cli-9.9.9-py3-none-any.whl"
        browser_download_url = "https://example.invalid/pdomain_ocr_cli-9.9.9-py3-none-any.whl"
        {digest_property}
      }})
    }}
  }}
  throw "unexpected Invoke-RestMethod: $Uri"
}}
function Invoke-WebRequest {{
  param([string]$Uri, [string]$OutFile)
  if ($Uri -ne "https://example.invalid/pdomain_ocr_cli-9.9.9-py3-none-any.whl") {{
    throw "unexpected Invoke-WebRequest: $Uri"
  }}
  Set-Content -Path $OutFile -Value "fake wheel" -NoNewline
}}
function irm {{
  param([string]$Uri)
  throw "unexpected irm: $Uri"
}}
$InstallerText = @'
{escaped_script}
'@
Invoke-Expression $InstallerText
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["PD_OCR_INSTALL_PYTHON"] = "3.12"
    preexec_fn = (lambda: os.umask(umask)) if umask is not None else None
    result = subprocess.run(
        ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        preexec_fn=preexec_fn,
    )
    return result, uv_log, perm_log


def test_install_ps1_piped_mode_is_self_contained_and_uses_release_wheel(
    tmp_path: Path,
) -> None:
    result, uv_log = _run_install_ps1(tmp_path, f'digest = "{FAKE_WHEEL_DIGEST}"')

    assert result.returncode == 0, result.stderr + result.stdout
    args = uv_log.read_text(encoding="utf-8")
    assert "--python\n3.12" in args
    # Runtime proof (not just a text grep): --index-strategy first-index and
    # the pdomain binding actually reach `uv`, via a named --index (not the
    # deprecated --extra-index-url, which a hostile UV_INDEX env var beats).
    assert "--index-strategy\nfirst-index" in args
    assert "--index\npdomain=https://pdomain.github.io/pdomain-index-pip/simple/" in args
    assert "--extra-index-url" not in args
    assert "pdomain_ocr_cli-9.9.9-py3-none-any.whl" in args
    assert "git+https://github.com/pdomain/pdomain-ocr-cli" not in args
    # This harness's fake nvidia-smi always reports CUDA 12.4, so the CUDA
    # extra index is also present. The pdomain index must be listed (and
    # therefore checked, under first-index) before it.
    assert "--index\npytorch-cuda=https://download.pytorch.org/whl/cu124" in args
    assert args.index("pdomain=") < args.index("pytorch-cuda=")


def test_install_ps1_uses_first_index_strategy() -> None:
    script = (REPO / "install.ps1").read_text(encoding="utf-8")
    assert '"--index-strategy", "first-index"' in script


def test_install_ps1_unix_file_mode_skips_windows_powershell_5() -> None:
    """Windows PowerShell 5.1 leaves $IsWindows unset. The Unix mode branch
    must require PowerShell 6+ as well, or the installer aborts before download.
    """
    script = (REPO / "install.ps1").read_text(encoding="utf-8")
    assert "if ($PSVersionTable.PSVersion.Major -ge 6 -and -not $IsWindows)" in script


def test_install_ps1_aborts_when_digest_is_missing(tmp_path: Path) -> None:
    result, uv_log = _run_install_ps1(tmp_path, "")

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_ps1_aborts_when_digest_is_malformed(tmp_path: Path) -> None:
    result, uv_log = _run_install_ps1(tmp_path, 'digest = "sha256:not-hex"')

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_ps1_aborts_when_digest_does_not_match_downloaded_bytes(
    tmp_path: Path,
) -> None:
    result, uv_log = _run_install_ps1(tmp_path, f'digest = "{MISMATCHED_DIGEST}"')

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_ps1_aborts_when_digest_is_uppercase_hex(tmp_path: Path) -> None:
    # PowerShell's `-notmatch` is case-INSENSITIVE, so a naive regex check
    # would accept uppercase hex here even though install.sh's `grep` (case
    # sensitive) rejects it for the same bytes. The spec requires exactly 64
    # lowercase hex characters, and both installers must agree.
    uppercase_digest = f"sha256:{hashlib.sha256(FAKE_WHEEL_BYTES).hexdigest().upper()}"
    result, uv_log = _run_install_ps1(tmp_path, f'digest = "{uppercase_digest}"')

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_ps1_aborts_when_digest_has_surrounding_whitespace(tmp_path: Path) -> None:
    padded_digest = f" {FAKE_WHEEL_DIGEST} "
    result, uv_log = _run_install_ps1(tmp_path, f'digest = "{padded_digest}"')

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_ps1_aborts_when_digest_is_63_hex_chars(tmp_path: Path) -> None:
    truncated_digest = f"sha256:{hashlib.sha256(FAKE_WHEEL_BYTES).hexdigest()[:-1]}"
    result, uv_log = _run_install_ps1(tmp_path, f'digest = "{truncated_digest}"')

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_ps1_temp_dir_has_restrictive_permissions(tmp_path: Path) -> None:
    """MINOR C: New-Item's directory mode follows umask (could be as open as
    0777), unlike `mktemp -d`'s unconditional 0700. On a POSIX pwsh host,
    that would let another local user replace the wheel between the
    Get-FileHash check and `uv tool install`, defeating digest verification.

    Runs pwsh itself under umask 0 (the most permissive umask, 0777) to
    prove the installer sets the mode explicitly rather than merely
    happening to inherit a strict one from this test environment.
    """
    result, _uv_log, perm_log = _run_install_ps1_full(
        tmp_path, f'digest = "{FAKE_WHEEL_DIGEST}"', umask=0
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert perm_log.exists(), "fake uv never observed the wheel file's temp dir"
    assert perm_log.read_text(encoding="utf-8").strip() == "700"


def test_install_ps1_enables_tls12_before_any_web_request() -> None:
    """Windows PowerShell 5.1 may default to TLS versions GitHub refuses."""
    lines = (REPO / "install.ps1").read_text(encoding="utf-8").splitlines()
    code = [line.strip() for line in lines if not line.strip().startswith("#")]
    tls = next(i for i, line in enumerate(code) if "[Net.SecurityProtocolType]::Tls12" in line)
    web = next(i for i, line in enumerate(code) if "irm " in line or "Invoke-" in line)
    assert "-bor" in code[tls]
    assert tls < web
