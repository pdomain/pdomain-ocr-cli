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
    if [ -n "${PDOMAIN_OCR_EXPECTED_TOOL_ENV:-}" ] &&
        [ "$tool_environment" != "$PDOMAIN_OCR_EXPECTED_TOOL_ENV" ]; then
        return 1
    fi
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

show_model_ownership() {
    python="$tool_environment/bin/python"
    [ -x "$python" ] || return 1
    "$python" -I - "$model_cache" "$tool_dir" "$bin_dir" "${1:-}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

try:
    from pdomain_ops.suite.component_siblings import macos_ocr_sibling_absent
    from pdomain_ops.suite.components import ComponentRegistry
    from pdomain_ops.suite.model_components import preview_cached_models, remove_model_entry
    from pdomain_ops.suite.paths import installed_toml_path
except ModuleNotFoundError:
    raise SystemExit(1)

app = "pdomain-ocr-cli"
expected = sys.argv[4]

def siblings_safe():
    return macos_ocr_sibling_absent(
        app,
        home=Path.home(),
        tool_dir=Path(sys.argv[2]),
        bin_dir=Path(sys.argv[3]),
        installed_apps=installed_toml_path(),
    )

if not siblings_safe():
    print("Setup keeps these models because another OCR app may use them.")
    raise SystemExit(1 if expected else 0)

registry = ComponentRegistry()
entries = preview_cached_models(registry, app, Path(sys.argv[1]))
if not entries:
    raise SystemExit(1)
selection = json.dumps(sorted((str(entry.path), entry.fingerprint) for entry in entries))
token = hashlib.sha256(selection.encode()).hexdigest()
if expected:
    if token != expected:
        raise SystemExit("Model entries changed. Reopen the uninstall preview before removing them.")
    for entry in entries:
        if not remove_model_entry(registry, app, entry, siblings_safe=siblings_safe):
            raise SystemExit("Model ownership changed. Reopen the uninstall preview.")
        print(f"Removed model cache entry: {entry.path}")
    raise SystemExit(0)
print("Model cache entries claimed only by OCR CLI:")
for entry in entries:
    print(f"  {entry.path}")
print(f"OCR_SETUP_MODEL_TOKEN {token}")
PY
}

remove_preview() {
    show_data_paths
    printf '%s\n' 'Removal keeps OCR inputs and outputs. Model, uv, and Python cleanup are optional.'
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
        remove_cli_tool preview
    else
        printf '%s\n' 'OCR CLI is already absent from this uv tool directory.'
    fi
    if ! show_model_ownership; then
        printf '%s\n' 'Setup has no ownership record for entries in this cache.'
    fi
}

remove_cli_tool() {
    python="$tool_environment/bin/python"
    if [ -x "$python" ] && uv_command=$(command -v uv); then
        result=0
        "$python" -I - "$uv_command" "$receipt" "$bin_dir" "${1:-}" "${2:-}" <<'PY' || result=$?
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from pdomain_ops.suite.component_files import ComponentFile
    from pdomain_ops.suite.component_siblings import macos_ocr_sibling_absent, other_uv_tools_absent
    from pdomain_ops.suite.components import ComponentRegistry
    from pdomain_ops.suite.paths import installed_toml_path
    from pdomain_ops.suite.python_components import ManagedPython
except ModuleNotFoundError:
    raise SystemExit(77)

receipt = Path(sys.argv[2])
tool_root = receipt.parent.parent.resolve()
default_root = (Path.home() / ".local/share/uv/tools").resolve()
xdg_data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
uv = Path(sys.argv[1])
option = sys.argv[4]
python_option = sys.argv[5]
app = "pdomain-ocr-cli"
registry = ComponentRegistry()
scope_safe = tool_root == default_root or bool(os.environ.get("PD_SUITE_DATA_DIR"))

def tools_safe(departing=None):
    return macos_ocr_sibling_absent(
        app,
        home=Path.home(),
        tool_dir=tool_root,
        bin_dir=Path(sys.argv[3]),
        installed_apps=installed_toml_path(),
    ) and other_uv_tools_absent(
        (tool_root, default_root, xdg_data / "uv/tools"), departing_tool=departing,
    )

def uv_selections():
    if not scope_safe or not tools_safe(app):
        return []
    known = {
        item.identity: item.fingerprint
        for item in registry.list()
        if item.kind == "uv" and item.claims == (app,)
    }
    selections = []
    for path in (uv, uv.with_name("uvx")):
        item = ComponentFile(path)
        expected = known.get(item.identity)
        if expected is not None and item.fingerprint() == expected:
            selections.append((item, expected))
    return selections

def consent(selections):
    payload = json.dumps([(item.identity, fingerprint) for item, fingerprint in selections])
    return hashlib.sha256(payload.encode()).hexdigest()

def python_selection():
    if not scope_safe or not tools_safe(app):
        return []
    known = {
        item.identity: item.fingerprint
        for item in registry.list()
        if item.kind == "python" and item.claims == (app,)
    }
    if not known:
        return []
    try:
        directory = subprocess.run(
            [str(uv), "python", "dir"], check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if not directory:
            return []
        root = Path(directory).resolve()
        base = Path(sys._base_executable).resolve()
        relative = base.relative_to(root)
        if len(relative.parts) < 2:
            return []
        item = ManagedPython(root, relative.parts[0], base)
        expected = known.get(item.identity)
        if expected is not None and item.fingerprint() == expected:
            return [(item, expected)]
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return []

selections = uv_selections() if option else []
python_selections = python_selection() if option == "preview" or python_option else []
if option == "preview":
    if selections:
        print("uv files claimed only by OCR CLI:")
        for item, _ in selections:
            print(f"  {item.path}")
        print(f"OCR_SETUP_UV_TOKEN {consent(selections)}")
    if python_selections:
        print(f"Managed Python claimed only by OCR CLI: {python_selections[0][0].path}")
        print(f"OCR_SETUP_PYTHON_TOKEN {consent(python_selections)}")
    raise SystemExit(0)
if option and (not selections or consent(selections) != option):
    raise SystemExit("uv ownership changed. Reopen the uninstall preview.")
if python_option and (not python_selections or consent(python_selections) != python_option):
    raise SystemExit("Python ownership changed. Reopen the uninstall preview.")

def uninstall():
    subprocess.run(
        [sys.argv[1], "tool", "uninstall", "--offline", "pdomain-ocr-cli"],
        check=True,
    )
    if receipt.exists() or receipt.is_symlink():
        raise RuntimeError("uv did not remove the OCR CLI receipt")

def cleanup():
    for item, fingerprint in python_selections:
        if registry.remove(
            "python", item.identity, app, item.fingerprint,
            lambda: item.remove(uv, fingerprint, run=lambda argv: subprocess.run(argv, check=True, timeout=60)),
            expected_fingerprint=fingerprint, siblings_safe=tools_safe,
        ):
            print(f"Removed managed Python: {item.path}")
        else:
            print(f"Kept Python because its ownership changed: {item.path}")
    for item, fingerprint in selections:
        if registry.remove(
            "uv", item.identity, app, item.fingerprint, lambda: item.remove(fingerprint),
            expected_fingerprint=fingerprint, siblings_safe=tools_safe,
        ):
            print(f"Removed uv file: {item.path}")
        else:
            print(f"Kept uv file because its ownership changed: {item.path}")

if scope_safe:
    registry.release(app, uninstall=uninstall, cleanup=cleanup if selections or python_selections else None)
else:
    uninstall()
    print("Shared claims were kept for possible OCR CLI installs in other tool directories.")
PY
        case "$result" in
            0) return 0 ;;
            77) [ "${1:-}" != preview ] || return 0 ;;
            *) return "$result" ;;
        esac
    fi
    [ "${1:-}" != preview ] || return 0
    [ -z "${1:-}${2:-}" ] || return 1
    uv tool uninstall --offline pdomain-ocr-cli
}

remove_cli() {
    case "$1" in keep-settings | remove-settings) ;; *) return 2 ;; esac
    remove_preview
    if [ "$1" = remove-settings ] && [ -L "$settings_dir" ]; then
        printf 'Cannot clear settings through the linked directory %s.\n' "$settings_dir" >&2
        return 1
    fi
    if [ -f "$receipt" ]; then
        if [ -n "${2:-}" ]; then
            printf '%s\n' 'OCR_SETUP_STAGE Removing selected model cache entries'
            if ! show_model_ownership "$2"; then
                printf '%s\n' 'The model cleanup could not be verified. Reopen the uninstall preview.' >&2
                return 1
            fi
        fi
        printf '%s\n' 'OCR_SETUP_STAGE Removing OCR CLI'
        remove_cli_tool "${3:-}" "${4:-}"
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

stage_uv() {
    case "$uv_bin" in /*) ;; *) return 1 ;; esac
    mkdir -p "$uv_bin" || return 1
    uv_stage=$(mktemp -d "$uv_bin/.ocr-uv.XXXXXX") || return 1
    trap 'rm -rf "$uv_stage"' EXIT
    trap 'exit 1' HUP INT TERM
    curl -LsSf https://astral.sh/uv/install.sh -o "$uv_stage/install.sh" || return 1
    UV_UNMANAGED_INSTALL="$uv_stage" /bin/sh "$uv_stage/install.sh" || return 1
    [ -x "$uv_stage/uv" ] || return 1
    export PATH="$uv_stage:$PATH"
}

publish_uv() {
    result=0
    "$tool_environment/bin/python" -I - "$uv_stage" "$uv_bin" <<'PY' || result=$?
import sys
from pathlib import Path

try:
    from pdomain_ops.suite.component_files import install_staged_uv
    from pdomain_ops.suite.components import ComponentRegistry
except ModuleNotFoundError:
    raise SystemExit(77)

stage, destination = map(Path, sys.argv[1:])
registry = ComponentRegistry()
for name in ("uv", "uvx"):
    if (stage / name).is_file():
        install_staged_uv(registry, "pdomain-ocr-cli", stage / name, destination / name)
PY
    if [ "$result" -eq 77 ]; then
        for file in uv uvx; do
            [ -f "$uv_stage/$file" ] || continue
            if [ ! -e "$uv_bin/$file" ] && [ ! -L "$uv_bin/$file" ]; then
                ln "$uv_stage/$file" "$uv_bin/$file" || [ -x "$uv_bin/$file" ] || return 1
            fi
        done
    elif [ "$result" -ne 0 ]; then
        return "$result"
    fi
    [ -x "$uv_bin/uv" ]
}

install_cli() {
    case "$1" in download | skip) ;; *) return 2 ;; esac
    case "$2" in enabled) preference=1 ;; disabled) preference=0 ;; *) return 2 ;; esac

    release=$(cat "$payload/release-tag")
    uv_stage=
    if ! command -v uv >/dev/null 2>&1; then
        printf '%s\n' 'OCR_SETUP_STAGE Preparing uv'
        stage_uv
    fi
    printf '%s\n' 'OCR_SETUP_STAGE Installing OCR CLI'
    PDOMAIN_OCR_EXPECTED_RELEASE_TAG="$release" PD_OCR_INSTALL_AUTO_UPDATE_CHECK="$preference" \
        /bin/sh "$payload/install.sh" --skip-models
    if ! tool_paths; then
        printf '%s\n' 'uv did not report absolute tool and launcher paths.' >&2
        return 1
    fi
    if [ -n "$uv_stage" ]; then
        publish_uv
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
        if ! PDOMAIN_OCR_MODEL_SOURCE=installer "$launcher" download-models; then
            printf '%s\n' 'OCR CLI is installed. Retry setup to download the models again, or skip the download.' >&2
            return 1
        fi
    fi
    printf 'OCR_SETUP_LAUNCHER %s\n' "$launcher"
}

terminal_uninstall() {
    settings_choice=keep-settings
    model_choice=keep
    uv_choice=keep
    python_choice=keep
    preview_only=0
    for option in "$@"; do
        case "$option" in
            --preview) preview_only=1 ;;
            --remove-settings) settings_choice=remove-settings ;;
            --remove-models) model_choice=remove ;;
            --remove-uv) uv_choice=remove ;;
            --remove-python) python_choice=remove ;;
            -h | --help)
                printf '%s\n' 'Usage: pdomain-ocr uninstall [--preview] [--remove-settings] [--remove-models] [--remove-uv] [--remove-python]'
                return 0
                ;;
            *)
                printf 'Unknown uninstall option: %s\n' "$option" >&2
                return 2
                ;;
        esac
    done

    preview=$(remove_preview) || return 1
    printf '%s\n' "$preview" | sed '/^OCR_SETUP_/d'
    [ "$preview_only" -eq 0 ] || return 0

    model_selection=
    uv_selection=
    python_selection=
    if [ "$model_choice" = remove ]; then
        model_selection=$(printf '%s\n' "$preview" | sed -n 's/^OCR_SETUP_MODEL_TOKEN //p')
        [ -n "$model_selection" ] || {
            printf '%s\n' 'No eligible model entries.' >&2
            return 1
        }
    fi
    if [ "$uv_choice" = remove ]; then
        uv_selection=$(printf '%s\n' "$preview" | sed -n 's/^OCR_SETUP_UV_TOKEN //p')
        [ -n "$uv_selection" ] || {
            printf '%s\n' 'No eligible uv files.' >&2
            return 1
        }
    fi
    if [ "$python_choice" = remove ]; then
        python_selection=$(printf '%s\n' "$preview" | sed -n 's/^OCR_SETUP_PYTHON_TOKEN //p')
        [ -n "$python_selection" ] || {
            printf '%s\n' 'No eligible managed Python build.' >&2
            return 1
        }
    fi
    printf '%s' 'Type REMOVE to uninstall OCR CLI with the selected options: '
    if ! IFS= read -r answer || [ "$answer" != REMOVE ]; then
        printf '%s\n' 'Uninstall canceled.'
        return 0
    fi
    remove_cli "$settings_choice" "$model_selection" "$uv_selection" "$python_selection"
}

if [ "${1:-}" = terminal-uninstall ]; then
    shift
    terminal_uninstall "$@"
    exit
fi

case "${1:-}:$#" in
    probe:1) probe ;;
    install:3) install_cli "$2" "$3" ;;
    remove-preview:1) remove_preview ;;
    remove:2) remove_cli "$2" ;;
    remove:3) remove_cli "$2" "$3" ;;
    remove:4) remove_cli "$2" "$3" "$4" ;;
    remove:5) remove_cli "$2" "$3" "$4" "$5" ;;
    *)
        printf '%s\n' 'Usage: setup-worker.sh probe | install {download|skip} {enabled|disabled} | remove-preview | remove {keep-settings|remove-settings}' >&2
        exit 2
        ;;
esac
