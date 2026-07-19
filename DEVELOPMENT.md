---
Status: active
Owner: CT
Created: 2026-05-03
Last verified: 2026-07-19
Kind: process
---

# Developing pdomain-ocr-cli

This document covers the developer workflows for `pdomain-ocr-cli`. End-user
install / usage docs live in [`README.md`](README.md).

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (Python package + tool manager)
- Python `>=3.11,<3.14` (uv will provision one if needed)
- `git`
- For local-dev workflows: `pdomain-book-tools` available as a sibling checkout
  at `../pdomain-book-tools`. `make local-setup` clones it for you.
- For local-dev workflows that edit `pdomain-ops` side-by-side: a sibling
  `../pdomain-ops` checkout. `make local-setup` clones it for you.
- Optional: NVIDIA GPU + CUDA Toolkit for GPU-accelerated OCR (see README).

## Quick start

Two paths depending on what you're doing.

### A. Just developing pdomain-ocr-cli (no pdomain-book-tools edits)

```sh
git clone https://github.com/pdomain/pdomain-ocr-cli.git
cd pdomain-ocr-cli
make setup
```

This syncs the dev deps from `pyproject.toml`, including `pdomain-book-tools`
at the pinned git tag, and installs pre-commit hooks. You can now run
`uv run pdomain-ocr ...` without installing globally.

### B. Editing pdomain repositories side-by-side

```sh
git clone https://github.com/pdomain/pdomain-ocr-cli.git
cd pdomain-ocr-cli
make local-setup
make local-dev
```

`local-setup` clones missing `pdomain-book-tools` and `pdomain-ops` sibling
repositories. `local-dev` then:

1. Installs both siblings editably into the canonical checkout's existing
   environment without syncing dependencies.
2. Writes the shared `.venv/.pdomain-local-mode` marker.
3. Prompts you to verify sibling resolution with `make local-check`.

If you also want pdomain-book-tools' own venv (to run its tests):

```sh
(cd ../pdomain-book-tools && make setup)
```

## Make targets

`make help` is authoritative. Highlights:

### General

| Target | Purpose |
| --- | --- |
| `setup` | Install dev deps + pre-commit hooks (uses pinned `pdomain-book-tools` tag). |
| `refresh-version` | Force-reinstall the editable package so `pdomain-ocr --version` re-derives from current git state (hatch-vcs bakes the version at install time, not at runtime — run this after `git pull` / new local tags). |
| `install` | Install `pdomain-ocr` as a `uv tool` from local source, auto-detecting CUDA. |
| `uninstall` | Remove the installed `pdomain-ocr` uv tool. |
| `lint` | Run ruff (with auto-fix). |
| `format` | Run ruff format, then lint. |
| `pre-commit-check` | Run pre-commit on all files. |
| `test` | Run the pytest suite (`tests/`). |
| `build` | `uv build` — produce sdist + wheel in `dist/`. |
| `wheel-smoke` | Build the wheel, install it into isolated Python 3.11 / 3.12 / 3.13 environments, and run `pdomain-ocr --version`. Override with `PYTHON_VERSIONS="3.13"` for a focused local run. |
| `wheel-smoke-one` | Focused wheel smoke for one interpreter. Set `PYTHON_VERSION=3.11`, `3.12`, or `3.13`. |
| `check-release-deps` | Fail release if runtime dependencies are path-sourced instead of package-index sourced. |
| `ci` | `setup` → `pre-commit-check` → `format-check` → `typecheck` → `coverage` → `installer-test` → `wheel-smoke`. |
| `ci-slow` | Full release-grade CI including slow integration coverage, build, and wheel smoke. |
| `clean` | Remove caches and `dist/`. |
| `reset` | `clean` + remove `.venv` + `setup`. |
| `upgrade-deps` | Upgrade the lockfile and sync the venv. Refuses in local-dev mode; use `local-upgrade-deps` instead. |
| `local-upgrade-deps` | Upgrade dependencies, sync to the canonical baseline, then restore editable siblings. |
| `upgrade-pdomain-book-tools` | Bump the `pdomain-book-tools` pin to the latest GitHub tag. |
| `release-{patch,minor,major}` | Run release preflight, tag, push `master` and the tag, then dispatch the release workflow. |

### Local-dev

These targets are guarded: if the sibling is missing, they print a clear
message and exit 1.

None of them mutate `pyproject.toml`. Instead, they swap the pinned
dependency for an editable install in the venv (or in the `uv tool`
install).

| Target | Purpose |
| --- | --- |
| `local-setup` | Clone any missing sibling pd-* repositories. |
| `local-dev` | Switch to local-dev mode with editable siblings and the shared marker. |
| `local-check` | Print local-dev mode and per-sibling resolution. |
| `local-upgrade-deps` | Upgrade dependencies, then restore editable siblings. |
| `local-install` | Install `pdomain-ocr` as a `uv tool` with editable `pdomain-book-tools`; direct `pdomain-ops` resolves from the registry. |
| `local-uninstall` | Remove the `uv tool` install. |
| `local-run` | Run `pdomain-ocr` against the editable workspace. Pass args via `ARGS="…"`. |
| `local-test` | Run the fast suite against editable siblings. |
| `local-test-slow` | Run the full suite, including slow integration tests, against editable siblings. |

Examples:

```sh
make local-run ARGS='page.png --layout-debug'
make local-check
```

After `local-install`, run `pdomain-ocr page.png`. The tool tracks this checkout
and editable `pdomain-book-tools`. Direct `pdomain-ops` uses the registry instead.

To revert to the published version:

```sh
make local-uninstall
curl -sSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh | sh
```

## Project layout

```text
pdomain_ocr_cli/
├── ocr_to_txt.py         # CLI parser and high-level orchestration
├── _policy.py            # effective flag policy and no-op warnings
├── _batch_plan.py        # image expansion, output planning, collision checks
├── _runtime.py           # predictor/session setup and batch runtime errors
├── _artifacts.py         # atomic page artifact writes and transactions
├── _model_security.py    # model trust-boundary warnings
├── _startup_notices.py   # update-check and GPU-nudge startup behavior
├── _hf_download.py       # generic hf_hub_download wrapper (sidecar opt-in)
├── _hf_models.py         # OCR + layout model resolution / prefetch / descriptors
├── _text_normalize.py    # curly-quote and em-dash post-processing
└── _update_check.py      # background GitHub-tag upgrade-notice check
```

Files prefixed with `_` are package-internal. The single public entry
point is `pdomain_ocr_cli.ocr_to_txt:main` (wired via `[project.scripts]`).

## Release

Releases are driven by `make release-patch`, `make release-minor`, or `make release-major`.
The release script requires a clean, up-to-date `master`. It then runs
`make ci-slow`, creates an annotated `vX.Y.Z` tag, and pushes `master` and the
tag. Finally, it
dispatches `.github/workflows/release.yml` with the tag input.

`pdomain-ops` and `pdomain-book-tools` resolve from the self-hosted pdomain pip index
for release builds. Do not commit path-based sibling sources for release.

When the release workflow passes, it builds and publishes release artifacts as
GitHub Release assets. `install.sh` / `install.ps1` resolve the latest
non-prerelease GitHub Release and download that wheel. End users get the new
release on their next `curl | sh`.

Versioning is managed by `hatch-vcs` from git tags. `pyproject.toml`
has no hardcoded version.

## Known quirks

- `Makefile.local` is gitignored. The earlier separate-file pattern is now
  merged into the main `Makefile`, with peer-existence guards on the
  `*-local` targets. You can still add `-include Makefile.local` for
  personal additions if you want them.
- Pylance / Pyright may flag `pdomain_book_tools.layout.adapters.pp_doclayout`
  and `transformers.utils` as unresolved. Those are intentional lazy
  imports (heavy dependencies loaded only when needed). Point your IDE at
  `.venv/bin/python` to silence them.
- `pytest` prints a `DeprecationWarning: defusedxml.cElementTree is deprecated`
  originating from `defusedxml/__init__.py`. This is a bug in `defusedxml`
  itself: its own `__init__.py` imports the deprecated submodule. Watch for
  a `defusedxml` release that fixes it and bump the pin when one appears.
