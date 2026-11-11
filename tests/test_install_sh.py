from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# The fake `curl` below writes exactly these bytes to the wheel file it is
# asked to download, so tests can assert digest verification against a known
# hash without hardcoding a magic value.
FAKE_WHEEL_BYTES = b"fake wheel"
FAKE_WHEEL_DIGEST = f"sha256:{hashlib.sha256(FAKE_WHEEL_BYTES).hexdigest()}"
MISMATCHED_DIGEST = f"sha256:{hashlib.sha256(b'different bytes').hexdigest()}"
SDIST_DIGEST = f"sha256:{hashlib.sha256(b'sdist bytes').hexdigest()}"


def _release_json(digest_clause: str = "") -> str:
    """Build the mocked GitHub Releases API JSON body for one wheel asset.

    `digest_clause` is inserted verbatim before the download-url field, e.g.
    `"digest":"sha256:...",` — pass "" to omit the digest field entirely.
    This mirrors the real GitHub Releases API field order, where `digest`
    precedes `browser_download_url` in each asset object (verified against
    a live `pdomain/pdomain-ocr-cli` release).
    """
    return (
        '{"tag_name":"v9.9.9","assets":[{'
        f"{digest_clause}"
        '"browser_download_url":'
        '"https://example.invalid/pdomain_ocr_cli-9.9.9-py3-none-any.whl"'
        "}]}"
    )


def _gh_release_json(
    sdist_digest_clause: str,
    wheel_digest_clause: str,
    asset_separator: str = "},{",
) -> str:
    """Build a `gh release view --json tagName,assets` shaped body.

    Two assets, sdist first (matching real release-workflow upload order),
    each asset shaped like real `gh` output: `apiUrl`, `digest`, `name`,
    `url` (the browser-download form `install.sh` actually reads).
    `*_digest_clause` is inserted verbatim before each asset's `"name"`
    field, e.g. `"digest":"sha256:...",` — pass "" to omit it.
    `asset_separator` is the literal text joining the two asset objects —
    default `"},{"`; pass e.g. `"}\\r\\n,\\r\\n{"` to reproduce a
    CRLF-formatted response body.
    """
    return (
        '{"assets":['
        "{"
        '"apiUrl":"https://api.github.com/repos/pdomain/pdomain-ocr-cli/releases/assets/1",'
        f"{sdist_digest_clause}"
        '"name":"pdomain_ocr_cli-9.9.9.tar.gz",'
        '"url":"https://example.invalid/pdomain_ocr_cli-9.9.9.tar.gz"'
        f"{asset_separator}"
        '"apiUrl":"https://api.github.com/repos/pdomain/pdomain-ocr-cli/releases/assets/2",'
        f"{wheel_digest_clause}"
        '"name":"pdomain_ocr_cli-9.9.9-py3-none-any.whl",'
        '"url":"https://example.invalid/pdomain_ocr_cli-9.9.9-py3-none-any.whl"'
        "}"
        '],"tagName":"v9.9.9"}'
    )


def _write_fake_bin(
    bin_dir: Path,
    uv_log: Path,
    release_json: str,
    gh_release_json: str | None = None,
    cuda: bool = False,
) -> None:
    bin_dir.mkdir()

    _ = (bin_dir / "uv").write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {uv_log}\n"
        f"printf '%s' \"$TMPDIR\" > {uv_log}.tmpdir\nexit 0\n",
        encoding="utf-8",
    )
    (bin_dir / "uv").chmod(0o755)
    _ = (bin_dir / "curl").write_text(
        f"""#!/bin/sh
out=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then shift; out="$1"; fi
  shift || true
done
if [ -n "$out" ]; then
  printf 'fake wheel' > "$out"
else
  cat <<'JSON'
{release_json}
JSON
fi
exit 0
""",
        encoding="utf-8",
    )
    (bin_dir / "curl").chmod(0o755)

    if gh_release_json is not None:
        _ = (bin_dir / "gh").write_text(
            f"""#!/bin/sh
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "release" ] && [ "$2" = "view" ]; then
  cat <<'JSON'
{gh_release_json}
JSON
  exit 0
fi
exit 1
""",
            encoding="utf-8",
        )
    else:
        _ = (bin_dir / "gh").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (bin_dir / "gh").chmod(0o755)

    if cuda:
        # install.sh parses the PLAIN `nvidia-smi` header line (colon
        # immediately after "Version", unlike the padded `nvidia-smi -q`
        # form), e.g.: "| ... Driver Version: 550.54.15  CUDA Version: 12.4 |"
        smi_line = "| NVIDIA-SMI 550.54.15   Driver Version: 550.54.15   CUDA Version: 12.4    |"
        _ = (bin_dir / "nvidia-smi").write_text(
            f"#!/bin/sh\nprintf '%s\\n' '{smi_line}'\nexit 0\n",
            encoding="utf-8",
        )
    else:
        _ = (bin_dir / "nvidia-smi").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (bin_dir / "nvidia-smi").chmod(0o755)


def _run_install_sh(
    tmp_path: Path,
    release_json: str,
    gh_release_json: str | None = None,
    cuda: bool = False,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    bin_dir = tmp_path / "bin"
    uv_log = tmp_path / "uv.log"
    _write_fake_bin(bin_dir, uv_log, release_json, gh_release_json, cuda)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["PD_OCR_INSTALL_PYTHON"] = "3.12"
    env["TMPDIR"] = str(tmp_path)
    result = subprocess.run(
        ["sh", str(REPO / "install.sh")],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, uv_log


def test_install_sh_uses_release_wheel_and_pdomain_index(tmp_path: Path) -> None:
    result, uv_log = _run_install_sh(tmp_path, _release_json(f'"digest":"{FAKE_WHEEL_DIGEST}",'))

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


def test_install_sh_pdomain_index_precedes_cuda_extra_index(tmp_path: Path) -> None:
    result, uv_log = _run_install_sh(
        tmp_path, _release_json(f'"digest":"{FAKE_WHEEL_DIGEST}",'), cuda=True
    )

    assert result.returncode == 0, result.stderr + result.stdout
    args = uv_log.read_text(encoding="utf-8")
    assert "--index\npdomain=https://pdomain.github.io/pdomain-index-pip/simple/" in args
    assert "--index\npytorch-cuda=https://download.pytorch.org/whl/cu124" in args
    assert "--with\npdomain-book-tools[gpu]" in args
    # The pdomain index must be listed (and therefore checked, under
    # first-index) before the CUDA/PyTorch extra index.
    assert args.index("pdomain=") < args.index("pytorch-cuda=")


def test_install_sh_uses_first_index_strategy() -> None:
    script = (REPO / "install.sh").read_text(encoding="utf-8")
    assert 'UV_INDEX_STRATEGY="first-index"' in script
    assert '--index-strategy "$UV_INDEX_STRATEGY"' in script


def test_install_sh_aborts_when_digest_is_missing(tmp_path: Path) -> None:
    result, uv_log = _run_install_sh(tmp_path, _release_json())

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_sh_aborts_when_digest_is_malformed(tmp_path: Path) -> None:
    result, uv_log = _run_install_sh(tmp_path, _release_json('"digest":"sha256:not-hex",'))

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_sh_aborts_when_digest_does_not_match_downloaded_bytes(
    tmp_path: Path,
) -> None:
    result, uv_log = _run_install_sh(tmp_path, _release_json(f'"digest":"{MISMATCHED_DIGEST}",'))

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_sh_aborts_when_digest_is_uppercase_hex(tmp_path: Path) -> None:
    # The spec requires exactly 64 LOWERCASE hex characters. Uppercase must
    # be rejected here even though it names the same bytes as
    # FAKE_WHEEL_DIGEST, so both installers agree on what they accept.
    uppercase_digest = f"sha256:{hashlib.sha256(FAKE_WHEEL_BYTES).hexdigest().upper()}"
    result, uv_log = _run_install_sh(tmp_path, _release_json(f'"digest":"{uppercase_digest}",'))

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_sh_aborts_when_digest_has_surrounding_whitespace(tmp_path: Path) -> None:
    padded_digest = f" {FAKE_WHEEL_DIGEST} "
    result, uv_log = _run_install_sh(tmp_path, _release_json(f'"digest":"{padded_digest}",'))

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_sh_aborts_when_digest_is_63_hex_chars(tmp_path: Path) -> None:
    truncated_digest = f"sha256:{hashlib.sha256(FAKE_WHEEL_BYTES).hexdigest()[:-1]}"
    result, uv_log = _run_install_sh(tmp_path, _release_json(f'"digest":"{truncated_digest}",'))

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_sh_gh_path_verifies_correct_digest(tmp_path: Path) -> None:
    """The `gh` CLI path (not just the curl/REST fallback) is exercised."""
    gh_json = _gh_release_json(
        sdist_digest_clause=f'"digest":"{SDIST_DIGEST}",',
        wheel_digest_clause=f'"digest":"{FAKE_WHEEL_DIGEST}",',
    )
    result, uv_log = _run_install_sh(tmp_path, _release_json(), gh_release_json=gh_json)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Digest verified" in result.stdout
    args = uv_log.read_text(encoding="utf-8")
    assert "pdomain_ocr_cli-9.9.9-py3-none-any.whl" in args


def test_install_sh_gh_path_never_leaks_sdist_digest_onto_wheel(tmp_path: Path) -> None:
    """Finding 1's blast path: sdist (listed first) carries a real digest,
    the wheel (selected asset) carries none of its own. The old
    implementation carried the sdist's digest across into the wheel via a
    sticky awk variable and installed the wheel unverified. The fixed
    per-asset-scoped extractor must instead treat this as a missing digest
    and refuse to install.
    """
    gh_json = _gh_release_json(
        sdist_digest_clause=f'"digest":"{SDIST_DIGEST}",',
        wheel_digest_clause="",
    )
    result, uv_log = _run_install_sh(tmp_path, _release_json(), gh_release_json=gh_json)

    assert result.returncode != 0
    assert "Digest verified" not in result.stdout
    assert not uv_log.exists()


def test_install_sh_gh_path_crlf_between_assets_does_not_leak_sdist_digest(
    tmp_path: Path,
) -> None:
    """`tr '\\n' ' '` alone normalizes LF but not CR. RFC 8259 permits CR as
    insignificant JSON whitespace, so a CRLF-formatted response body used to
    merge both asset objects into a single chunk at the `}<sep>{` boundary,
    and `head -1` then paired the sdist's digest with the wheel's URL —
    reopening finding 1 through a different byte.

    The sdist's digest is deliberately set to FAKE_WHEEL_DIGEST — the hash
    of the bytes actually served for the wheel — exactly matching the
    reviewer's reproduction. This is what makes the test discriminating: if
    it merged and leaked, the leaked digest would still verify successfully
    against the downloaded bytes, so a weaker assertion (any failure) could
    pass for the wrong reason (e.g. a digest *mismatch*) instead of proving
    the leak itself is closed. Only a real fix makes this fail *closed* on
    a missing digest rather than *succeed* on a leaked one.
    """
    gh_json = _gh_release_json(
        sdist_digest_clause=f'"digest":"{FAKE_WHEEL_DIGEST}",',
        wheel_digest_clause="",
        asset_separator="}\r\n,\r\n{",
    )
    result, uv_log = _run_install_sh(tmp_path, _release_json(), gh_release_json=gh_json)

    assert result.returncode != 0
    assert "Digest verified" not in result.stdout
    assert not uv_log.exists()


def test_install_sh_gh_path_crlf_between_assets_verifies_wheel_digest(
    tmp_path: Path,
) -> None:
    """Second impact of the CR gap: with a CRLF body where BOTH assets carry
    a digest, the merged-chunk bug would pick the sdist's (first) digest and
    falsely reject a wheel whose own digest is actually correct. The fix
    must still isolate the wheel's own digest and succeed.
    """
    gh_json = _gh_release_json(
        sdist_digest_clause=f'"digest":"{SDIST_DIGEST}",',
        wheel_digest_clause=f'"digest":"{FAKE_WHEEL_DIGEST}",',
        asset_separator="}\r\n,\r\n{",
    )
    result, uv_log = _run_install_sh(tmp_path, _release_json(), gh_release_json=gh_json)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Digest verified" in result.stdout
    args = uv_log.read_text(encoding="utf-8")
    assert "pdomain_ocr_cli-9.9.9-py3-none-any.whl" in args


def test_install_sh_gh_path_aborts_on_wrong_digest(tmp_path: Path) -> None:
    gh_json = _gh_release_json(
        sdist_digest_clause=f'"digest":"{SDIST_DIGEST}",',
        wheel_digest_clause=f'"digest":"{MISMATCHED_DIGEST}",',
    )
    result, uv_log = _run_install_sh(tmp_path, _release_json(), gh_release_json=gh_json)

    assert result.returncode != 0
    assert not uv_log.exists()


def test_install_sh_gh_path_without_digest_falls_back_to_rest_api(tmp_path: Path) -> None:
    gh_json = _gh_release_json(sdist_digest_clause="", wheel_digest_clause="")
    rest_json = _release_json(f'"digest":"{FAKE_WHEEL_DIGEST}",')

    result, uv_log = _run_install_sh(tmp_path, rest_json, gh_release_json=gh_json)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "via GitHub API" in result.stdout
    assert "Digest verified" in result.stdout
    assert "pdomain_ocr_cli-9.9.9-py3-none-any.whl" in uv_log.read_text(encoding="utf-8")


def test_install_sh_aborts_when_gh_and_rest_api_both_lack_a_digest(tmp_path: Path) -> None:
    gh_json = _gh_release_json(sdist_digest_clause="", wheel_digest_clause="")

    result, uv_log = _run_install_sh(tmp_path, _release_json(), gh_release_json=gh_json)

    assert result.returncode != 0
    assert "did not report a digest" in result.stderr
    assert not uv_log.exists()


def test_install_sh_leaves_callers_tmpdir_for_uv(tmp_path: Path) -> None:
    rest_json = _release_json(f'"digest":"{FAKE_WHEEL_DIGEST}",')

    result, uv_log = _run_install_sh(tmp_path, rest_json)

    assert result.returncode == 0, result.stderr + result.stdout
    recorded = Path(f"{uv_log}.tmpdir").read_text(encoding="utf-8")
    assert recorded == str(tmp_path)
