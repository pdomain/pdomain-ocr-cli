---
kind: plan
status: active
owner: CT
created: 2026-05-19
last_verified: 2026-07-19
disposition: Standing roadmap for CLI-owned work.
---

<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# pdomain-ocr-cli Roadmap

## Agent Index

- **Kind:** plan
- **Status:** active
- **Read when:** deciding what to work on next in `pdomain-ocr-cli`.
- **Search terms:** roadmap, backlog, now next later, open priorities, hardening, release, supply chain, security

This roadmap lists **open** CLI-owned work only. Implemented former GitHub items
live under **Shipped** and in architecture, usage, and tests. Provenance tags
use `former GH #NNN` (not live tracker links). The GitHub Issues tracker stays
empty; see
[`docs/decisions/2026-07-19-github-issues-cutover.md`](decisions/2026-07-19-github-issues-cutover.md).

## Goal

Maintain the standing list of open priorities owned by `pdomain-ocr-cli`. Track
CLI flags, defaults, help, documentation, orchestration, and caller-side glue
here while routing reusable primitives upstream.

## Architecture

`pdomain-ocr` wraps `pdomain-book-tools` OCR and layout primitives and uses
`pdomain-ops` for operational support. Shared processing logic belongs
upstream; this repository owns the command and its integration behavior.

## Tech Stack

The CLI supports Python 3.11 through 3.13 and uses Hatchling and hatch-vcs. It
depends on `pdomain-book-tools`, `pdomain-ops`, and `huggingface_hub`, with
development and verification through `uv`, pytest, Ruff, and basedpyright.

## Global Constraints

**Never silently drop OCR words** — output options may change roles or suppress
placeholder blocks, but caption and OCR text must survive unless an explicitly
experimental drop is enabled. Keep reusable primitives upstream, and run
`make ci AI=1` before committing. Where a CLI feature is a thin pass-through to
a library knob, the library work is tracked in
`pdomain-book-tools/docs/plans/roadmap.md` and the CLI item here covers only the
surfacing (flag name, help text, defaults, docs) and any caller-side glue.

## Work clusters (remaining open legs only)

- **Installer residual:** former GH #24 — dependency-confusion guard on the
  installer `uv tool install` path (wheel + index path already shipped).
- **Rotation + layout alignment:** former GH #18 — layout detect and illustration
  crops must use the rotated page image; default-layout word-preservation
  multiset coverage is former GH #41.
- **Release residual:** former GH #30 (installer artifact verification), #31
  upper bounds (wheel-smoke already shipped), #50 build-backend pins, #45
  immutable pre-commit revs (tag revs + `pre-commit-update` already present).

---

## Now — highest priority

### Correctness

- [bug/high] Run layout detection and illustration crops on the rotated page
  image (former GH #18). Report:
  [`docs/issues/2026-07-19-gh-18-layout-crops-ignore-rotation.md`](issues/2026-07-19-gh-18-layout-crops-ignore-rotation.md).

### Tests

- [chore/high] Assert default layout reorganization preserves every OCR word
  (former GH #41). Report:
  [`docs/issues/2026-07-19-gh-41-default-layout-word-preservation-test.md`](issues/2026-07-19-gh-41-default-layout-word-preservation-test.md).

## Next — medium priority

### Release & install residual

- [chore/medium] Verify downloaded release artifacts in installers (former GH #30).
  Report: [`docs/issues/2026-07-19-gh-30-installer-artifact-verification.md`](issues/2026-07-19-gh-30-installer-artifact-verification.md)
- [bug/medium] Prevent dependency confusion for pd-book-tools on the **installer**
  tool-install path (former GH #24). Report:
  [`docs/issues/2026-07-19-gh-24-installer-dependency-confusion.md`](issues/2026-07-19-gh-24-installer-dependency-confusion.md)
- [chore/medium] Bound runtime dependency ranges (upper caps); wheel-smoke for
  3.11–3.13 already ships (former GH #31). Report:
  [`docs/issues/2026-07-19-gh-31-runtime-dep-upper-bounds.md`](issues/2026-07-19-gh-31-runtime-dep-upper-bounds.md)
- [chore/medium] Pin build backend versions used for releases (former GH #50).
  Report: [`docs/issues/2026-07-19-gh-50-pin-build-backends.md`](issues/2026-07-19-gh-50-pin-build-backends.md)

### Runtime residual

- [chore/medium] Add resource limits for untrusted image inputs (former GH #38).
  Report: [`docs/issues/2026-07-19-gh-38-untrusted-image-resource-limits.md`](issues/2026-07-19-gh-38-untrusted-image-resource-limits.md)
- [chore/medium] Make best-effort update-check failures diagnosable (former GH #35).
  Report: [`docs/issues/2026-07-19-gh-35-update-check-diagnostics.md`](issues/2026-07-19-gh-35-update-check-diagnostics.md)
- [bug/medium] Optional sidecar rollback if final `.txt` write fails (former GH #22).
  Report: [`docs/issues/2026-07-19-gh-22-sidecar-rollback-on-txt-failure.md`](issues/2026-07-19-gh-22-sidecar-rollback-on-txt-failure.md)

### Tests / tooling

- [chore/medium] Pin pre-commit hook revisions to immutable commit SHAs, or
  formally accept version tags plus `pre-commit-update` (former GH #45). Report:
  [`docs/issues/2026-07-19-gh-45-pre-commit-immutable-pins.md`](issues/2026-07-19-gh-45-pre-commit-immutable-pins.md)

## Later — low priority

### Deferred features

- Add `--normalize-output {none|ascii|...}` (default `none`) after
  `pdomain-book-tools` provides shared normalization logic and a glyph map.
  Report: [`docs/issues/2026-07-19-normalize-output-flag-deferred.md`](issues/2026-07-19-normalize-output-flag-deferred.md)

## Blocked

- [bug/high, blocked] Pin default OCR model revisions and avoid unsafe
  `torch.load` (former GH #15). Report:
  [`docs/issues/2026-07-19-gh-15-model-revision-pin-and-safe-load.md`](issues/2026-07-19-gh-15-model-revision-pin-and-safe-load.md)

## Ideas

_No untriaged requests._

---

## Shipped

Durable behavior also lives in architecture, decisions, usage, and tests.
Items below were removed from the open backlog after evidence review
(2026-07-19).

### 2026-07-19 — backlog reconcile (code already on master)

| Former GH | Outcome | Evidence anchor |
| --- | --- | --- |
| #25 | Local `make ci-slow` preflight + dispatch-only publish (supersedes server-side slow CI in publish workflow) | `scripts/release-common.sh`, `release.yml`, `cli-orchestration.md` Release boundary, `test_workflows_static.py` |
| #27 | Release shell uses env for tag (no template injection) | `release.yml`, static workflow tests |
| #37 / #26 | CI and release actions + uv pinned to full SHAs / version | `ci.yml`, `release.yml`, static tests |
| #28 / #29 | `persist-credentials: false`; release setup-uv does not enable cache | workflows |
| #47 | Python 3.11–3.13 CI matrix | `ci.yml` |
| #46 / #51 | Lock hashes for book-tools; `idna` at safe pin | `uv.lock` |
| #23 / #49 | `install.ps1` pd-index-pip + release-wheel path | `install.ps1`, `test_install_ps1.py` |
| #16 | Warn on arbitrary / mutable model inputs | `_model_security.py`, `test_model_security.py` |
| #17 / #21 | Exclusive temps + atomic JSON/crop/text writes | `_artifacts.py`, artifact tests |
| #34 | HTTPS-only update check URL | `_update_check.py`, decisions log |
| #33 | No shell-interpolated Make `ARGS` passthrough | `Makefile` / `local-run.sh` |
| #20 | Plain `--no-reorg` skips layout load | `_policy.py`, main/layout tests |
| #39 / #40 | Plan/validate before model load; clean startup errors | `ocr_to_txt.py`, `test_main_errors.py` |
| #42 / #43 | Caption preservation with flag; default-layout slow path | tests + `test-suite.md` |
| #44 | Document full accepted image suffixes (incl. JPEG 2000 family) | `docs/usage/cli-usage.md` (this pass) |
| #48 | Release docs say `master` (match `do-release`) | `DEVELOPMENT.md` (this pass) |
| #36 | **Won't fix** — ADR keeps PATH-based `nvidia-smi` probe | `decisions.md`, lint-deviations |

### 2026-06-01 — book-tools 0.18 / pdomain-ops 0.7.2 + HF model v0.7

- Bumped `pdomain-book-tools` floor to `>=0.18.0`; batch OCR now auto-rotates,
  correcting `rotated_page` fixture without any fixture modification.
- Bumped `pdomain-ops` floor to `>=0.7.2`; both resolve from `pdomain-index-pip`.
- Pinned integration-test HF model to `v0.7` (post-pdomain rename, `pdomain-`-prefixed files).
- All 15 slow integration tests pass. The `rotated_page` test passes legitimately.

### 2026-06-01 — book-tools 0.17 / pdomain-ops 0.7 compatibility

- Bumped `pdomain-book-tools` floor to `>=0.17.0` and `pdomain-ops` floor to `>=0.7.0`; both resolve from `pdomain-index-pip`.
- Adopted `from_image_ocr_via_doctr` tuple return (`tuple[Document, int]`) in
  `_run_doctr_batch_single_image_compat`; added `_SingleImageDocResultLike` protocol.
- Dropped the stale "pdomain-ops path source" note (ops is now in the index).

### 2026-05-29 — review remediation

- Added `RunPolicy`, `BatchPlan`, `RuntimeSession`, artifact transaction
  helpers, model trust warnings, and startup notice seams.
- Added installer contract tests, real OCR/default-layout slow coverage,
  workflow static checks, and wheel smoke for Python 3.11, 3.12, and 3.13.
- Hardened release gating so path-sourced runtime dependencies block release
  until they resolve from `pdomain-index-pip`.
