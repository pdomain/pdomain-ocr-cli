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

This roadmap lists open, CLI-owned work by priority within each theme. This
file is the source of truth for planned work; it absorbs the former
`docs/plans/roadmap.md` and the repo's former GitHub issue backlog (migrated
2026-07-14). Each item keeps a `former GH #NNN` provenance tag. Those numbers
are not live tracker links. The GitHub Issues tracker is kept empty; see
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

## Work clusters

Several open items belong to one piece of work split across issues. Do them together:

- **`install.ps1` parity:** former GH #23 (Now), former GH #49, former GH #24 — one rewrite of the PowerShell installer to mirror `install.sh` (release-wheel path, pd-index-pip, dependency-confusion guard, installer-arg tests).
- **Workflow supply-chain hardening:** former GH #37, former GH #26, former GH #27, former GH #28, former GH #29 — one hardening pass over `ci.yml` / `release.yml` (pin actions + uv by SHA, drop persisted creds, remove template injection, cache). Note #37 (ci.yml) is `high` and #26 (release.yml) is `medium` per their labels, but the edit is the same.
- **Durable artifact transaction:** former GH #17 → former GH #21 → former GH #22 — one design: exclusive non-symlink temp files, route all writes through the atomic helper, all-or-nothing promotion with rollback.
- **Release wheel-smoke:** shared sub-task of former GH #25, former GH #30, former GH #31, former GH #50 — smoke-install from the built wheel once, referenced by all four.
- **Startup sequencing (`ocr_to_txt`):** former GH #18, former GH #20, former GH #39, former GH #40 — adjacent edits to the same input-validation / model-load / layout path; sequence to avoid rework.

---

## Now — highest priority

### Release & CI supply-chain

- [chore/high] Run server-side tests before publishing tag-triggered releases (former GH #25)
- [chore/high] Remove template-injection risk from the release-dispatch shell block (former GH #27)
- [chore/high] Pin CI workflow actions and uv to immutable versions (former GH #37)
- [bug/high] Rewrite `install.ps1` to resolve pd-book-tools from pd-index-pip (former GH #23)

### Correctness

- [bug/high] Run layout detection and illustration crops on the rotated page image (former GH #18)

### Tests

- [chore/high] Assert default layout reorganization preserves every OCR word (former GH #41)

## Next — medium priority

### Release & CI supply-chain

- [chore/medium] Pin release workflow actions and uv to immutable versions (former GH #26)
- [chore/medium] Verify downloaded release artifacts in installers (former GH #30)
- [bug/medium] Prevent dependency confusion for pd-book-tools installs (former GH #24)
- [bug/medium] Make the PowerShell installer use the release wheel path (former GH #49)
- [chore/medium] Test all supported Python versions in CI (former GH #47)

### Dependency hygiene

- [chore/medium] Bound runtime dependency ranges and smoke-test released installs (former GH #31)
- [chore/medium] Add integrity hashes for pd-book-tools lock entries (former GH #46)
- [chore/medium] Pin build backend versions used for releases (former GH #50)
- [chore/medium] Upgrade the vulnerable idna lock entry (former GH #51)

### Runtime security & safety

- [bug/medium] Warn or guard when users supply arbitrary `.pt` model checkpoints (former GH #16)
- [bug/medium] Use exclusive, non-symlink temp files for atomic writes (former GH #17)
- [chore/medium] Constrain the update-check URL opener to HTTPS-only (former GH #34)
- [chore/medium] Add resource limits for untrusted image inputs (former GH #38)

### Correctness bugs

- [bug/medium] Skip layout loading and inference for plain `--no-reorg` runs (former GH #20)
- [bug/medium] Make JSON and crop writes use the durable atomic-write path (former GH #21)
- [bug/medium] Roll back sidecars and crops when the final `.txt` write fails (former GH #22)
- [bug/medium] Validate inputs before resolving and loading models (former GH #39)
- [bug/medium] Turn startup model and layout failures into clean CLI errors (former GH #40)

### Tests

- [chore/medium] Assert `--no-illustration-placeholders` preserves caption text (former GH #42)
- [chore/medium] Cover the default layout-enabled end-to-end path (former GH #43)

## Later — low priority

### Release & CI

- [chore/low] Disable persisted checkout credentials where not needed (former GH #28)
- [chore/low] Disable or harden the setup-uv cache in the release workflow (former GH #29)
- [chore/low] Pin pre-commit hooks or enforce reviewed hook updates (former GH #45)

### Runtime security & observability

- [chore/low] Avoid shell-interpolated `ARGS` passthrough in local Make targets (former GH #33)
- [chore/low] Make best-effort update-check failures diagnosable (former GH #35)
- [chore/low] Execute the resolved `nvidia-smi` path for the GPU-nudge probe (former GH #36)

### Docs

- [bug/low] Document all accepted image suffixes, including JPEG 2000 (former GH #44)
- [bug/low] Align release instructions with `do-release` push behavior (former GH #48)

### Deferred features

- Add `--normalize-output {none|ascii|...}` (default `none`) after
  `pdomain-book-tools` provides shared normalization logic and a glyph map. CLI
  work covers the pass-through flag and applying normalization between
  reorganization and text output.

## Blocked

- [bug/high, blocked] Pin default OCR model revisions and avoid unsafe `torch.load` (former GH #15) — **two parts.** Part 1 (pin default model revisions to `v0.6`) is implemented on the local branch `fix/security-15-torch-load-pinning`. Part 2 (`weights_only=True` / safe load) is **blocked upstream on `pd-book-tools#205`**; a tripwire test flips red once that ships. Item stays on the roadmap until then. Related trust-boundary work: former GH #16 (user-supplied `.pt`).

## Ideas

_No untriaged requests._

---

## Shipped

Preserved from the former `docs/plans/roadmap.md`. Durable behavior also lives
in architecture, decisions, usage, and process docs.

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
