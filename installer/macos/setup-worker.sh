#!/bin/sh
set -eu

payload=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
release=$(cat "$payload/release-tag")
uv_bin=${UV_UNMANAGED_INSTALL:-${UV_INSTALL_DIR:-${XDG_BIN_HOME:-${XDG_DATA_HOME:+$XDG_DATA_HOME/../bin}}}}
uv_bin=${uv_bin:-$HOME/.local/bin}
export PATH="$uv_bin:$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.cargo/bin"
python_version=${PD_OCR_INSTALL_PYTHON:-3.13}

probe() {
    if ! command -v uv >/dev/null 2>&1; then
        printf '%s\n' 'uv: Setup will install it.' 'Python: uv will find or download a compatible version.'
    else
        printf '%s\n' 'uv: Already installed.'
        if uv python find --no-project --no-python-downloads -- "$python_version" >/dev/null 2>&1; then
            printf '%s\n' 'Python: A compatible version is already installed.'
        else
            printf '%s\n' 'Python: uv will find or download a compatible version.'
        fi
    fi
    preferences="${XDG_CONFIG_HOME:-$HOME/.config}/pdomain-ocr/update.toml"
    if [ -f "$preferences" ] && grep -Eq '^[[:space:]]*auto_check[[:space:]]*=[[:space:]]*true([[:space:]]*(#.*)?)?$' "$preferences"; then
        printf '%s\n' 'OCR_SETUP_UPDATES enabled'
    fi
    command -v uv >/dev/null 2>&1 || return 0
    root=$(uv tool dir 2>/dev/null) || return 0
    [ -n "$root" ] || return 0
    python="$root/pdomain-ocr-cli/bin/python"
    [ -x "$python" ] || return 0
    "$python" -I - "$release" 2>/dev/null <<'PY' || :
import sys
from importlib.metadata import version
from pathlib import Path
from huggingface_hub import try_to_load_from_cache
from pdomain_book_tools import hf as models
from pdomain_ocr_cli.ocr_to_txt import DEFAULT_LAYOUT_MODEL, DEFAULT_MODEL_REVISION

if version("pdomain-ocr-cli") != sys.argv[1].removeprefix("v"):
    raise SystemExit(0)
files = [
    (models.DEFAULT_HF_REPO, name, DEFAULT_MODEL_REVISION)
    for name in (models.DEFAULT_DET_FILENAME, models.DEFAULT_RECO_FILENAME)
]
repo, revision, _ = models.resolve_layout_source(DEFAULT_LAYOUT_MODEL)
if repo:
    files.extend((repo, name, revision) for name in models.LAYOUT_MODEL_FILES)
for repo, name, revision in files:
    cached = try_to_load_from_cache(repo, name, revision=revision)
    if not isinstance(cached, str) or not Path(cached).is_file():
        break
else:
    print("OCR_SETUP_MODELS cached")
PY
}

install_cli() {
    case "$1" in download | skip) ;; *) return 2 ;; esac
    case "$2" in enabled) preference=1 ;; disabled) preference=0 ;; *) return 2 ;; esac

    printf '%s\n' 'OCR_SETUP_STAGE Installing OCR CLI'
    PDOMAIN_OCR_EXPECTED_RELEASE_TAG="$release" PD_OCR_INSTALL_AUTO_UPDATE_CHECK="$preference" \
        /bin/sh "$payload/install.sh" --skip-models
    bin=$(uv tool dir --bin)
    case "$bin" in
        /*) ;;
        *)
            printf '%s\n' 'uv did not report an absolute launcher path.' >&2
            return 1
            ;;
    esac
    launcher="$bin/pdomain-ocr"
    installed=$("$launcher" --version)
    if [ "$installed" != "pdomain-ocr ${release#v}" ]; then
        printf 'Expected pdomain-ocr %s, got %s\n' "${release#v}" "$installed" >&2
        return 1
    fi
    printf '%s\n' 'OCR_SETUP_STAGE Checking the installed OCR runtime'
    "$launcher" --check-runtime
    if [ "$1" = download ]; then
        printf '%s\n' 'OCR_SETUP_STAGE Downloading OCR models'
        if ! "$launcher" download-models; then
            printf '%s\n' 'OCR CLI is installed. Retry setup to download the models again, or skip the download.' >&2
            return 1
        fi
    fi
    printf 'OCR_SETUP_LAUNCHER %s\n' "$launcher"
}

case "${1:-}:$#" in
    probe:1) probe ;;
    install:3) install_cli "$2" "$3" ;;
    *)
        printf '%s\n' 'Usage: setup-worker.sh probe | install {download|skip} {enabled|disabled}' >&2
        exit 2
        ;;
esac
