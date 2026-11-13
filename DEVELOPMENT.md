---
Status: active
Owner: CT
Created: 2026-05-03
Last verified: 2026-11-07
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
at its exact pin from the self-hosted `pdomain-index-pip` index, and installs
pre-commit hooks. You can now run
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
| `setup` | Install dev deps + pre-commit hooks (uses the exact `pdomain-book-tools` pin from `pdomain-index-pip`). |
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
| `ci` | `setup` → `pre-commit-check` → `format-check` → `typecheck` → `coverage` → `installer-test` → `build` → `wheel-smoke`. |
| `ci-slow` | Full release-grade CI including slow integration coverage, build, and wheel smoke. |
| `clean` | Remove caches and `dist/`. |
| `reset` | `clean` + remove `.venv` + `setup`. |
| `upgrade-deps` | Upgrade the lockfile and sync the venv. Refuses in local-dev mode; use `local-upgrade-deps` instead. |
| `local-upgrade-deps` | Upgrade dependencies, sync to the canonical baseline, then restore editable siblings. |
| `update-pdomain-deps` | Bump the `>=` pins of `pdomain-book-tools` and `pdomain-ops` to the latest `pdomain-index-pip` version. It skips exact `==` pins, so bump `pdomain-book-tools==` by hand. |
| `upgrade-pdomain-book-tools` | Deprecated alias for `update-pdomain-deps`. |
| `release-{patch,minor,major}` | Run release preflight, tag, push `master` and the tag, then build the artifacts and create the GitHub Release. |

### Local-dev

`local-setup` clones missing siblings, and `local-dev` runs it first. The
other targets except `local-check` and `local-uninstall` are guarded: without
the local-dev marker they print an error and exit 1.

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
| `local-run` | Broken today: `scripts/local-run.sh` runs `make run`, which the Makefile does not define. Use `UV_NO_SYNC=1 uv run pdomain-ocr …` instead. |
| `local-test` | Run the fast suite against editable siblings. |
| `local-test-slow` | Run the full suite, including slow integration tests, against editable siblings. |

Examples:

```sh
UV_NO_SYNC=1 uv run pdomain-ocr page.png --layout-debug
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
├── _hf_models.py         # argparse adapters around pdomain_book_tools.hf model resolution
├── _image_limits.py      # size and pixel-count admission checks for input images
├── _pipeline.py          # pure pipeline helpers, including quote and dash cleanup
└── _update_check.py      # background GitHub-tag upgrade-notice check
```

Files prefixed with `_` are package-internal. The single public entry
point is `pdomain_ocr_cli.ocr_to_txt:main` (wired via `[project.scripts]`).

## Release

Releases are driven by `make release-patch`, `make release-minor`, or `make release-major`.
The release script requires a clean, up-to-date `master`. It then runs
`make ci-slow`, creates an annotated `vX.Y.Z` tag, and pushes `master` and the
tag. Finally it builds the artifacts and creates the GitHub Release itself,
attaching everything under `dist/`. The workflows were removed on 2026-09-13,
so the script is the whole path.

`pdomain-ops` and `pdomain-book-tools` resolve from the self-hosted pdomain pip index
for release builds. Do not commit path-based sibling sources for release.

`install.sh` / `install.ps1` resolve the latest non-prerelease GitHub Release
and download that wheel, so end users get the new release on their next
`curl | sh`.

Publishing to the pip index is a separate, manual step, with no scheduled
fallback:

```bash
(cd ../pdomain-index-pip && ./scripts/publish-index.sh)
```

Versioning is managed by `hatch-vcs` from git tags. `pyproject.toml`
has no hardcoded version.

## Known quirks

- `Makefile.local` is gitignored. The earlier separate-file pattern is now
  merged into the main `Makefile`: the `local-*` targets call
  `scripts/local-*.sh`, and the old `*-local` names are deprecation aliases.
  The `Makefile` does not include `Makefile.local`; add
  `-include Makefile.local` yourself for personal additions.
- Pylance / Pyright may flag `pdomain_book_tools.layout.adapters.pp_doclayout`
  and `transformers.utils` as unresolved. Those are intentional lazy
  imports (heavy dependencies loaded only when needed). Point your IDE at
  `.venv/bin/python` to silence them.
- `pyproject.toml`'s pytest `filterwarnings` still ignores the
  `defusedxml.cElementTree is deprecated` `DeprecationWarning` that
  `defusedxml` 0.7.1 raised on import. `defusedxml` is no longer in
  `uv.lock`, so the filter may now be unused.
