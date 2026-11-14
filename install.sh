#!/bin/sh
set -e

# Install pdomain-ocr as a standalone tool using uv.
#
# Pulls the wheel from the latest non-prerelease GitHub Release of
# pdomain/pdomain-ocr-cli and installs it via `uv tool install`. Uses
# `gh` if available (and authenticated); otherwise falls back to the
# public GitHub Releases API via curl.
#
# GPU auto-enable:
#   The CUDA >= 13 branch below passes `--with pdomain-book-tools[gpu]` to
#   pull in cupy-cuda13x. pdomain-book-tools 0.31.0 makes that extra CUDA 13
#   only. CUDA 12 still gets the matching PyTorch wheel, without the extra.
#
# pdomain-book-tools is published on a self-hosted PEP 503 index (pdomain-index-pip) so
# the wheel's Requires-Dist entry resolves automatically when we bind that
# index to uv via a named --index — no manual git-pin fetch needed.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh | sh

REPO="pdomain/pdomain-ocr-cli"
PYTHON_VERSION="${PD_OCR_INSTALL_PYTHON:-3.13}"

# Install uv if not already present
if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found — installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    # A failed download pipes nothing into sh, which then exits 0.
    if ! command -v uv >/dev/null 2>&1; then
        echo "❌ uv could not be installed; see the message above." >&2
        echo "   Install it yourself: https://docs.astral.sh/uv/getting-started/installation/" >&2
        exit 1
    fi
fi

EXTRA_INDEX=""
PD_BOOK_TOOLS_EXTRAS=""
PD_INDEX_URL="https://pdomain.github.io/pdomain-index-pip/simple/"
# "first-index" makes uv stop looking once a package name resolves on an
# index, in index-URL order. The pdomain index is always passed first (see
# `set --` below) via a named `--index`, not the deprecated
# `--extra-index-url`: uv ranks --index/UV_INDEX strictly above
# --extra-index-url, and passing --index explicitly on the CLI replaces
# (rather than merges with) any UV_INDEX the environment supplies — so a
# hostile UV_INDEX env var, a same-named package on PyPI, or a later
# user-supplied index can never shadow the pdomain one. Verified against
# real uv 0.11.32 with local decoy indexes; --extra-index-url does not have
# this property (a hostile UV_INDEX beats it).
UV_INDEX_STRATEGY="first-index"

# Auto-detect NVIDIA CUDA
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    CUDA_VER=$(nvidia-smi 2>/dev/null | sed -n 's/.*CUDA Version: \([0-9]*\.[0-9]*\).*/\1/p' | head -1)
    if [ -n "$CUDA_VER" ]; then
        CUDA_TAG="cu$(echo "$CUDA_VER" | tr -d '.')"
        EXTRA_INDEX="https://download.pytorch.org/whl/${CUDA_TAG}"
        echo "Detected CUDA ${CUDA_VER} — will install PyTorch with ${CUDA_TAG} support."

        # cupy-cuda13x needs CUDA 13. CUDA 12 still gets the matching
        # PyTorch wheel, without the [gpu] extra.
        # POSIX-sh version compare — no `sort -V`, no `awk`.
        CUDA_MAJOR=${CUDA_VER%.*}
        if [ "$CUDA_MAJOR" -ge 13 ]; then
            PD_BOOK_TOOLS_EXTRAS="[gpu]"
            echo "CUDA ${CUDA_VER} >= 13 — enabling pdomain-book-tools[gpu] (cupy-cuda13x)."
        else
            echo "CUDA ${CUDA_VER} < 13 — installing CPU-only book-tools (cupy-cuda13x needs CUDA 13)."
        fi
    else
        echo "nvidia-smi found but could not detect CUDA version — falling back to CPU."
    fi
# Detect Apple Silicon (MPS)
elif [ "$(uname)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
    echo "Detected Apple Silicon — MPS acceleration will be used automatically."
else
    echo "No GPU detected — installing CPU-only PyTorch."
fi

# ---------------------------------------------------------------------------
# Resolve the latest non-prerelease GitHub Release and find the wheel asset.
# ---------------------------------------------------------------------------
# We pin to the asset URL of the .whl on the "latest" Release. The local
# release recipe (`just release-*`) attaches both .whl and .tar.gz; we
# install the .whl directly so end users don't need a build toolchain.

# Extract the value from a single grep -Eo match shaped like
# `"key"  :  "value"` (whitespace optional). Structural, not positional, so
# it's safe even when the value itself contains a colon (e.g. "sha256:...").
# Always emits exactly one line — including an empty line for empty/absent
# input — so callers can rely on positional `sed -n 'Np'` extraction.
_json_string_value() {
    printf '%s\n' "$1" | sed 's/^"[^"]*"[ \t]*:[ \t]*"//; s/"$//'
}

# Scan a JSON asset list (pretty-printed or compact) for the first *.whl
# asset and print its digest then its download URL, one per line.
# Handles both `gh release view --json` asset shape (key "url") and the raw
# GitHub REST API shape (key "browser_download_url").
#
# Splits the input into one chunk per asset object *before* looking at any
# field, so "digest" is only ever read from the SAME asset object as the
# winning .whl URL — never carried over from a sibling asset (e.g. the
# .tar.gz, or any asset ahead of the wheel in the array) that happens to
# have its own digest. This also makes extraction independent of field
# order within the object.
select_whl_digest() {
    # The trailing `printf '\n'` guarantees the LAST chunk is newline
    # terminated even when the input JSON has no trailing newline of its
    # own (the common case for compact single-line JSON): POSIX `read`
    # returns non-zero — and skips the loop body entirely — for a final
    # line with no terminating newline, which would otherwise silently
    # drop a single-asset (or last-asset) match.
    { printf '%s' "$1" | tr '\n\r' '  ' | sed 's/}[ \t]*,[ \t]*{/}\n{/g'; printf '\n'; } \
        | while IFS= read -r asset; do
            if printf '%s' "$asset" | grep -Eq '"(url|browser_download_url)"[ \t]*:[ \t]*"[^"]*\.whl"'; then
                digest_match=$(printf '%s' "$asset" | grep -Eo '"digest"[ \t]*:[ \t]*"[^"]*"' | head -1)
                url_match=$(printf '%s' "$asset" | grep -Eo '"(url|browser_download_url)"[ \t]*:[ \t]*"[^"]*\.whl"' | head -1)
                _json_string_value "$digest_match"
                _json_string_value "$url_match"
                break
            fi
        done
}

WHEEL_URL=""
WHEEL_DIGEST=""
RELEASE_TAG=""

# `command` skips a shell function named gh. Bash exports functions into
# this script, and that function would hide the gh binary on PATH.
if command -v gh >/dev/null 2>&1 && command gh auth status >/dev/null 2>&1; then
    echo "Resolving latest release via gh..."
    # `gh release view --json` returns assets with their download URLs.
    RELEASE_JSON=$(command gh release view --repo "$REPO" --json tagName,assets 2>/dev/null || true)
    if [ -n "$RELEASE_JSON" ]; then
        RELEASE_TAG=$(printf '%s' "$RELEASE_JSON" | grep -o '"tagName":"[^"]*"' | head -1 | sed 's/.*"tagName":"\([^"]*\)".*/\1/')
        SELECTED=$(select_whl_digest "$RELEASE_JSON")
        WHEEL_DIGEST=$(printf '%s\n' "$SELECTED" | sed -n '1p')
        WHEEL_URL=$(printf '%s\n' "$SELECTED" | sed -n '2p')
    fi
fi

# A gh build whose asset JSON has no digest would otherwise fail closed below;
# the REST API reports one.
if [ -z "$WHEEL_URL" ] || [ -z "$WHEEL_DIGEST" ]; then
    echo "Resolving latest release via GitHub API..."
    RELEASE_JSON=$(curl -sSfL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null || true)
    if [ -z "$RELEASE_JSON" ]; then
        echo "❌ Could not query the GitHub Releases API for ${REPO}." >&2
        echo "   Check your network, or install manually with:" >&2
        echo "     uv tool install git+https://github.com/${REPO}" >&2
        exit 1
    fi
    RELEASE_TAG=$(printf '%s' "$RELEASE_JSON" \
        | grep '"tag_name"' | head -1 \
        | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')
    SELECTED=$(select_whl_digest "$RELEASE_JSON")
    WHEEL_DIGEST=$(printf '%s\n' "$SELECTED" | sed -n '1p')
    WHEEL_URL=$(printf '%s\n' "$SELECTED" | sed -n '2p')
fi

if [ -z "$WHEEL_URL" ]; then
    echo "❌ Latest release ${RELEASE_TAG:-?} has no wheel asset attached." >&2
    echo "   Cannot install. Please check https://github.com/${REPO}/releases" >&2
    echo "   and report the missing wheel — or install from source with:" >&2
    echo "     uv tool install git+https://github.com/${REPO}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Fail closed on any missing or malformed digest, before downloading.
# ---------------------------------------------------------------------------
if [ -z "$WHEEL_DIGEST" ]; then
    echo "❌ GitHub did not report a digest for ${WHEEL_URL}." >&2
    echo "   Refusing to install an unverified wheel." >&2
    exit 1
fi

case "$WHEEL_DIGEST" in
    sha256:*) WHEEL_DIGEST_HEX=${WHEEL_DIGEST#sha256:} ;;
    *)
        echo "❌ Unsupported digest algorithm for ${WHEEL_URL}: ${WHEEL_DIGEST}" >&2
        echo "   Expected sha256:<64 lowercase hex characters>." >&2
        exit 1
        ;;
esac

if ! printf '%s' "$WHEEL_DIGEST_HEX" | grep -Eq '^[0-9a-f]{64}$'; then
    echo "❌ Malformed sha256 digest for ${WHEEL_URL}: ${WHEEL_DIGEST}" >&2
    echo "   Expected sha256:<64 lowercase hex characters>." >&2
    exit 1
fi

echo "Latest release: ${RELEASE_TAG:-(unknown tag)}"
echo "Wheel asset:    ${WHEEL_URL}"
echo "Wheel digest:   ${WHEEL_DIGEST}"
echo "pdomain-index-pip:       ${PD_INDEX_URL}"

# ---------------------------------------------------------------------------
# Download the wheel to a temp dir and install.
# ---------------------------------------------------------------------------
WHEEL_DIR=$(mktemp -d)
# shellcheck disable=SC2064
trap "rm -rf '$WHEEL_DIR'" EXIT

WHEEL_FILE="$WHEEL_DIR/$(basename "$WHEEL_URL")"
echo "Downloading wheel..."
# `gh release view --json assets` asset objects carry two different URLs:
# `apiUrl` (api.github.com/repos/.../assets/<id>, needs an Accept header to
# receive the binary) and `url` (the public browser_download_url form, no
# header needed). select_whl_digest reads the `url` field, so this Accept
# header isn't strictly required for the gh path — but it's harmless to
# send for both forms, so we always send it.
if ! curl -sSfL \
        -H "Accept: application/octet-stream" \
        -o "$WHEEL_FILE" "$WHEEL_URL"; then
    echo "❌ Failed to download wheel from ${WHEEL_URL}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Verify the downloaded wheel against the digest GitHub reported for it,
# BEFORE calling `uv tool install`. A digest that doesn't match the bytes we
# actually fetched means the download was tampered with or corrupted; either
# way, installing it would be worse than failing here.
# ---------------------------------------------------------------------------
if command -v sha256sum >/dev/null 2>&1; then
    WHEEL_ACTUAL_HEX=$(sha256sum "$WHEEL_FILE" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
    WHEEL_ACTUAL_HEX=$(shasum -a 256 "$WHEEL_FILE" | awk '{print $1}')
else
    echo "❌ Neither sha256sum nor shasum is available to verify the wheel digest." >&2
    exit 1
fi

if [ "$WHEEL_ACTUAL_HEX" != "$WHEEL_DIGEST_HEX" ]; then
    echo "❌ Wheel digest mismatch for ${WHEEL_URL}." >&2
    echo "   expected: sha256:${WHEEL_DIGEST_HEX}" >&2
    echo "   actual:   sha256:${WHEEL_ACTUAL_HEX}" >&2
    exit 1
fi
echo "Digest verified: sha256:${WHEEL_ACTUAL_HEX}"

echo "Installing pdomain-ocr ${RELEASE_TAG:-} from $(basename "$WHEEL_FILE")..."
# Build the install command incrementally so we only emit flags when relevant.
# POSIX sh has no arrays — use `set --` to manage args.
#
# pdomain-book-tools is published on the self-hosted pdomain-index-pip
# (GitHub Pages PEP 503 index); bind it via a named `--index` (not the
# deprecated --extra-index-url) so uv can resolve the Requires-Dist entry
# that the wheel's METADATA carries, and so a hostile UV_INDEX env var can't
# outrank it (see the UV_INDEX_STRATEGY comment above). When CUDA >= 13
# was detected above, $PD_BOOK_TOOLS_EXTRAS is "[gpu]"; we pass --with to
# pull that extra in. The pdomain --index is always listed before the CUDA
# extra --index, so it's still checked first under first-index.
set -- --reinstall "$WHEEL_FILE" --index-strategy "$UV_INDEX_STRATEGY" --index "pdomain=${PD_INDEX_URL}"
if [ -n "$PD_BOOK_TOOLS_EXTRAS" ]; then
    set -- "$@" --with "pdomain-book-tools${PD_BOOK_TOOLS_EXTRAS}"
fi
if [ -n "$EXTRA_INDEX" ]; then
    set -- "$@" --index "pytorch-cuda=${EXTRA_INDEX}"
fi
# Run `uv tool install`, retrying only uv-reported network failures. uv
# already retried each request three times and then printed "Request failed
# after N retries"; the extra attempts wait longer, for an index that is down
# for a minute rather than a moment. A resolver failure ("No solution
# found"), including one caused by a 401/403 index, is never retried.
attempt=1
max_attempts=3
while :; do
    { status=0; uv tool install --python "$PYTHON_VERSION" "$@" 2>&1 || status=$?; echo "$status" > "$WHEEL_DIR/uv.status"; } \
        | tee "$WHEEL_DIR/uv.log"
    status=$(cat "$WHEEL_DIR/uv.status")
    if [ "$status" -eq 0 ]; then
        break
    fi
    if grep -q "No solution found" "$WHEEL_DIR/uv.log" \
        || ! grep -Eq "Request failed after [0-9]+ retr" "$WHEEL_DIR/uv.log"; then
        echo "❌ uv tool install failed with exit code ${status}. pdomain-ocr was not installed." >&2
        exit "$status"
    fi
    if [ "$attempt" -ge "$max_attempts" ]; then
        echo "❌ uv tool install failed with exit code ${status} after ${max_attempts} attempts because of network errors." >&2
        echo "   pdomain-ocr was not installed. Check your connection, then run the installer again." >&2
        exit "$status"
    fi
    if [ "$attempt" -eq 1 ]; then delay=15; else delay=45; fi
    echo ""
    echo "uv could not reach a package index (attempt ${attempt} of ${max_attempts}). Trying again in ${delay} seconds..."
    sleep "$delay"
    attempt=$((attempt + 1))
done

echo ""
echo "Done! Run: pdomain-ocr page.png"
echo "If 'pdomain-ocr' is not found, add uv's tool bin to your PATH:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
