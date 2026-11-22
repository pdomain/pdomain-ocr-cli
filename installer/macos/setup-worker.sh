#!/bin/sh
set -eu

payload=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
uv_bin=${UV_UNMANAGED_INSTALL:-${UV_INSTALL_DIR:-${XDG_BIN_HOME:-${XDG_DATA_HOME:+$XDG_DATA_HOME/../bin}}}}
uv_bin=${uv_bin:-$HOME/.local/bin}
export PATH="$uv_bin:$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.cargo/bin"
python_version=${PD_OCR_INSTALL_PYTHON:-3.13}
settings_dir="${XDG_CONFIG_HOME:-$HOME/.config}/pdomain-ocr"
preferences="$settings_dir/update.toml"
hf_home=${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}
model_cache=${HF_HUB_CACHE:-${HUGGINGFACE_HUB_CACHE:-$hf_home/hub}}

tool_paths() {
    tool_dir=$(uv tool dir) && bin_dir=$(uv tool dir --bin) || return 1
    case "$tool_dir" in /*) ;; *) return 1 ;; esac
    case "$bin_dir" in /*) ;; *) return 1 ;; esac
    tool_environment="$tool_dir/pdomain-ocr-cli"
    receipt="$tool_environment/uv-receipt.toml"
    launcher="$bin_dir/pdomain-ocr"
}

show_tool_paths() {
    printf 'CLI environment: %s\nCLI receipt: %s\nCLI launcher in the current uv bin directory: %s\n' \
        "$tool_environment" "$receipt" "$launcher"
}

show_data_paths() {
    printf 'CLI update settings: %s\nShared model cache: %s\n' "$preferences" "$model_cache"
}

remove_preview() {
    show_data_paths
    printf '%s\n' 'Removal keeps the shared model cache, uv and its Python installations.'
    if ! command -v uv >/dev/null 2>&1 || ! tool_paths; then
        printf '%s\n' 'Could not locate uv tool storage. Open Setup with the same uv environment used to install the CLI.' >&2
        return 1
    fi
    show_tool_paths
    if [ -L "$tool_environment" ] || [ -L "$receipt" ] ||
        { [ -e "$tool_environment" ] && [ ! -f "$receipt" ]; }; then
        printf 'Cannot verify the OCR CLI uv receipt at %s.\n' "$receipt" >&2
        return 1
    fi
    if [ -f "$receipt" ]; then
        printf '%s\n' 'Removal uses the launchers recorded in the OCR CLI uv receipt.'
    else
        printf '%s\n' 'OCR CLI is already absent from this uv tool directory.'
    fi
}

remove_cli() {
    case "$1" in keep-settings | remove-settings) ;; *) return 2 ;; esac
    remove_preview
    if [ "$1" = remove-settings ] && [ -L "$settings_dir" ]; then
        printf 'Cannot clear settings through the linked directory %s.\n' "$settings_dir" >&2
        return 1
    fi
    if [ -f "$receipt" ]; then
        printf '%s\n' 'OCR_SETUP_STAGE Removing OCR CLI'
        uv tool uninstall --offline pdomain-ocr-cli
    fi
    if [ "$1" = remove-settings ]; then
        rm -f -- "$preferences"
    fi
}

probe() {
    release=$(cat "$payload/release-tag")
    show_data_paths
    if ! command -v uv >/dev/null 2>&1; then
        printf '%s\n' 'uv: Setup will install it.' 'Python: uv will find or download a compatible version.'
        printf '%s\n' 'Setup will show the tool and launcher paths after uv is installed.'
    else
        printf '%s\n' 'uv: Already installed.'
        if uv python find --no-project --no-python-downloads -- "$python_version" >/dev/null 2>&1; then
            printf '%s\n' 'Python: A compatible version is already installed.'
        else
            printf '%s\n' 'Python: uv will find or download a compatible version.'
        fi
    fi
    if [ -f "$preferences" ] && grep -Eq '^[[:space:]]*auto_check[[:space:]]*=[[:space:]]*true([[:space:]]*(#.*)?)?$' "$preferences"; then
        printf '%s\n' 'OCR_SETUP_UPDATES enabled'
    fi
    command -v uv >/dev/null 2>&1 && tool_paths || return 0
    show_tool_paths
    python="$tool_environment/bin/python"
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

    release=$(cat "$payload/release-tag")
    printf '%s\n' 'OCR_SETUP_STAGE Installing OCR CLI'
    PDOMAIN_OCR_EXPECTED_RELEASE_TAG="$release" PD_OCR_INSTALL_AUTO_UPDATE_CHECK="$preference" \
        /bin/sh "$payload/install.sh" --skip-models
    if ! tool_paths; then
        printf '%s\n' 'uv did not report absolute tool and launcher paths.' >&2
        return 1
    fi
    show_tool_paths
    show_data_paths
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
    remove-preview:1) remove_preview ;;
    remove:2) remove_cli "$2" ;;
    *)
        printf '%s\n' 'Usage: setup-worker.sh probe | install {download|skip} {enabled|disabled} | remove-preview | remove {keep-settings|remove-settings}' >&2
        exit 2
        ;;
esac
