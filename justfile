set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set positional-arguments

# Copy this wrapper and install-hooks with the shell setting to sibling justfiles.
[private]
_ai +args:
    #!/usr/bin/env bash
    set -euo pipefail
    if env AI= just --quiet "$@" > .ci-ai.log 2>&1; then
        printf 'PASS: %s\n' "$*"
    else
        result=$?
        printf 'FAIL: %s (exit %s)\n' "$*" "$result"
        if [[ -f scripts/ai_filter_log.py ]]; then
            uv run python scripts/ai_filter_log.py .ci-ai.log
        else
            tail -50 .ci-ai.log
        fi
        exit "$result"
    fi

install-hooks:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai install-hooks; fi
    if [[ -f .git ]]; then
        echo "hooks: worktree checkout - the canonical repo owns them, skipping"
    elif [[ -n "$(git config --get core.hooksPath || true)" ]]; then
        echo "hooks: core.hooksPath is set - leaving it alone, skipping"
    else
        uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
    fi

help:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai help; fi
    just --list

setup:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai setup; fi
    echo "📦 Installing dependencies..."
    uv sync --locked --group dev
    echo "🔧 Ensuring PowerShell (pwsh) is available for install-script tests..."
    ./scripts/ensure-pwsh.sh
    echo "🪝 Setting up pre-commit hooks..."
    just --quiet install-hooks
    just --quiet refresh-version
    echo "✅ Setup complete!"

refresh-version:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai refresh-version; fi
    echo "🔄 Reinstalling pdomain-ocr-cli so hatch-vcs picks up the current HEAD / tags..."
    uv sync --locked --reinstall-package pdomain-ocr-cli
    echo "✅ Version now reports as:"
    uv run pdomain-ocr --version

install:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai install; fi
    ./scripts/install-uv-tool.sh

uninstall:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai uninstall; fi
    echo "🗑️  Uninstalling pdomain-ocr..."
    uv tool uninstall pdomain-ocr-cli || true
    echo "✅ pdomain-ocr uninstalled."

remove-venv:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai remove-venv; fi
    VENV="${UV_PROJECT_ENVIRONMENT:-.venv}"
    echo "🗑️  Removing existing virtual environment..."
    rm -rf "$VENV"
    echo "✅ Virtual environment removed!"

reset:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai reset; fi
    just --quiet clean
    just --quiet remove-venv
    just --quiet setup
    echo "✅ Environment Reset!"

upgrade-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai upgrade-deps; fi
    VENV="${UV_PROJECT_ENVIRONMENT:-.venv}"
    if ( uv pip show pdomain-book-tools 2>/dev/null | grep -q "^Editable project location:" ) || [ -f "$VENV/.pdomain-local-mode" ]; then \
        echo ""; \
        echo "❌ local-dev install detected (editable siblings present)."; \
        echo "    Running 'uv sync' here would revert the venv to the canonical baseline."; \
        echo "   Use 'just local-upgrade-deps' to upgrade and restore editable siblings."; \
        echo ""; \
        exit 1; \
    fi
    echo "Upgrading dependency lockfile..."
    uv lock --upgrade
    echo "Syncing upgraded dependencies..."
    uv sync --group dev
    just --quiet update-hooks
    echo "Dependencies upgraded and environment synced!"

update-pdomain-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai update-pdomain-deps; fi
    ./scripts/update-pdomain-deps.sh

upgrade-pdomain-book-tools:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai upgrade-pdomain-book-tools; fi
    echo "⚠️  upgrade-pdomain-book-tools is deprecated; use 'just update-pdomain-deps' instead."
    just --quiet update-pdomain-deps

lint:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai lint; fi
    echo "🔍 Running linting checks..."
    uv run ruff check --select I --fix
    uv run ruff check --fix

format:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai format; fi
    uv run ruff format

format-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai format-check; fi
    uv run ruff format --check .

pre-commit-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai pre-commit-check; fi
    echo "🪝 Running pre-commit on all files..."
    uv run pre-commit run --all-files

update-hooks:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai update-hooks; fi
    echo "⬆️  Updating pre-commit hook revisions (frozen to commit SHAs)..."
    uv run pre-commit autoupdate --freeze
    echo "✅ Hook revisions updated — review upstream release notes and the .pre-commit-config.yaml diff."

typecheck:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai typecheck; fi
    uv run basedpyright pdomain_ocr_cli --level error

test:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai test; fi
    echo "🧪 Running tests..."
    uv run pytest tests/ -v -n auto

test-slow:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai test-slow; fi
    echo "🧪 Running tests (including slow)..."
    uv run pytest -n auto tests/ -v --run-slow

test-integration:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai test-integration; fi
    uv run pytest -n auto --no-cov tests/test_pipeline_integration.py -v --run-slow

test-layout-integration:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai test-layout-integration; fi
    uv run pytest -n auto --no-cov tests/test_pipeline_integration.py -v --run-slow -k "default_layout"

installer-test:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai installer-test; fi
    echo "🧪 Running installer contract tests..."
    PYTEST_ADDOPTS=--no-cov uv run pytest -n auto tests/test_install_sh.py tests/test_install_ps1.py tests/test_install_ps1_cuda.py -v

coverage:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai coverage; fi
    COV_FAIL_UNDER="${COV_FAIL_UNDER:-100}"
    echo "🧪 Running tests with coverage (threshold: ${COV_FAIL_UNDER}%)..."
    uv run pytest -n auto tests/ --cov=pdomain_ocr_cli --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=${COV_FAIL_UNDER}
    echo "📊 Coverage report: htmlcov/index.html"

coverage-slow:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai coverage-slow; fi
    COV_FAIL_UNDER="${COV_FAIL_UNDER:-100}"
    COV_FAIL_UNDER_SLOW="${COV_FAIL_UNDER_SLOW:-100}"
    echo "🧪 Running tests with coverage including slow integration (threshold: ${COV_FAIL_UNDER_SLOW}%)..."
    uv run pytest -n auto tests/ --run-slow --cov=pdomain_ocr_cli --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=${COV_FAIL_UNDER_SLOW}
    echo "📊 Coverage report: htmlcov/index.html"

build:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai build; fi
    echo "🔨 Building project..."
    uv build

wheel-smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai wheel-smoke; fi
    PYTHON_VERSIONS="${PYTHON_VERSIONS:-3.11 3.12 3.13}"
    just --quiet build
    for py in $PYTHON_VERSIONS; do
        PYTHON_VERSION="$py" just --quiet wheel-smoke-one
    done

wheel-smoke-one:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai wheel-smoke-one; fi
    PDOMAIN_INDEX_URL="${PDOMAIN_INDEX_URL:-https://pdomain.github.io/pdomain-index-pip/simple/}"
    just --quiet build
    test -n "${PYTHON_VERSION:-}" || (echo "PYTHON_VERSION is required"; exit 2)
    echo "🧪 Wheel smoke: Python ${PYTHON_VERSION:-}"
    tmpdir=$(mktemp -d); \
    trap 'rm -rf "$tmpdir"' EXIT; \
    uv venv "$tmpdir/venv" --python "${PYTHON_VERSION:-}"; \
    wheel=$(ls -t dist/*.whl | head -n 1); \
    if [ -z "$wheel" ]; then \
        echo "No wheel found in dist/"; \
        exit 1; \
    fi; \
    if python3 -c 'import tomllib; p=tomllib.load(open("pyproject.toml","rb")); src=p.get("tool",{}).get("uv",{}).get("sources",{}).get("pdomain-ops",{}); raise SystemExit(0 if "path" in src else 1)'; then \
        ops_path=$(python3 -c 'import pathlib, tomllib; p=tomllib.load(open("pyproject.toml","rb")); src=p["tool"]["uv"]["sources"]["pdomain-ops"]; print(pathlib.Path(src["path"]))'); \
        if [ ! -d "$ops_path" ]; then \
            echo "pdomain-ops is path-sourced but $ops_path is missing; publish it to ${PDOMAIN_INDEX_URL} or provide the sibling checkout."; \
            exit 1; \
        fi; \
        echo "pdomain-ops is path-sourced; preinstalling local sibling for non-release wheel smoke."; \
        uv pip install --python "$tmpdir/venv/bin/python" "$ops_path" --extra-index-url ${PDOMAIN_INDEX_URL}; \
        uv pip install --python "$tmpdir/venv/bin/python" "$wheel" --no-deps; \
    else \
        uv pip install --python "$tmpdir/venv/bin/python" "$wheel" --extra-index-url ${PDOMAIN_INDEX_URL}; \
    fi; \
    "$tmpdir/venv/bin/pdomain-ocr" --version

check-release-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai check-release-deps; fi
    python3 -c 'import sys, tomllib; p=tomllib.load(open("pyproject.toml","rb")); src=p.get("tool",{}).get("uv",{}).get("sources",{}).get("pdomain-ops",{}); sys.exit("pdomain-ops must not be path-sourced for release") if "path" in src else None'

[default]
ci:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai ci; fi
    just --quiet setup pre-commit-check lint-check typecheck coverage installer-test build wheel-smoke
    docgraph check --strict

ci-slow:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai ci-slow; fi
    just --quiet ci coverage-slow

ci-against-master:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai ci-against-master; fi
    ./scripts/ci-against-master.sh

clean:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai clean; fi
    echo "🧹 Cleaning Python cache files..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    echo "🧹 Cleaning coverage artifacts..."
    rm -rf htmlcov/ 2>/dev/null || true
    rm -f coverage.xml .coverage 2>/dev/null || true
    echo "🧹 Cleaning build artifacts..."
    rm -rf dist/ 2>/dev/null || true
    echo "✅ Cleanup complete!"

release-patch:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai release-patch; fi
    BUMP=patch ./scripts/do-release.sh

release-minor:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai release-minor; fi
    BUMP=minor ./scripts/do-release.sh

release-major:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai release-major; fi
    BUMP=major ./scripts/do-release.sh

_do-release:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai _do-release; fi
    BUMP=${BUMP:-minor} ./scripts/do-release.sh

local-setup:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-setup; fi
    ./scripts/local-setup.sh

local-dev:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-dev; fi
    ./scripts/local-dev.sh

local-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-check; fi
    ./scripts/local-check.sh

local-upgrade-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-upgrade-deps; fi
    ./scripts/local-upgrade-deps.sh

local-install:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-install; fi
    ./scripts/local-install.sh

local-uninstall:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-uninstall; fi
    ./scripts/local-uninstall.sh

local-run:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-run; fi
    ./scripts/local-run.sh

local-test:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-test; fi
    ./scripts/local-test.sh

local-test-slow:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-test-slow; fi
    ./scripts/local-test-slow.sh

dev-local:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai dev-local; fi
    echo "warning: 'dev-local' is deprecated; use 'local-dev'"
    just --quiet local-dev

install-local:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai install-local; fi
    echo "warning: 'install-local' is deprecated; use 'local-install'"
    just --quiet local-install

uninstall-local:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai uninstall-local; fi
    echo "warning: 'uninstall-local' is deprecated; use 'local-uninstall'"
    just --quiet local-uninstall

check-local-editable:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai check-local-editable; fi
    echo "warning: 'check-local-editable' is deprecated; use 'local-check'"
    just --quiet local-check

upgrade-deps-local:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai upgrade-deps-local; fi
    echo "warning: 'upgrade-deps-local' is deprecated; use 'local-upgrade-deps'"
    just --quiet local-upgrade-deps

run-local:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai run-local; fi
    echo "warning: 'run-local' is deprecated; use 'local-run'"
    just --quiet local-run

lint-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai lint-check; fi
    uv run ruff format --check .
    uv run ruff check .
