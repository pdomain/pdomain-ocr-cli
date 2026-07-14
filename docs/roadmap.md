---
kind: plan
status: active
owner: CT
created: 2026-05-19
last_verified: 2026-07-14
disposition: Standing roadmap for CLI-owned work.
---

<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# pdomain-ocr-cli Roadmap

## Agent Index

- **Kind:** plan
- **Status:** active
- **Read when:** deciding what to work on next in `pdomain-ocr-cli`.
- **Search terms:** roadmap, backlog, now next later, open priorities, hardening, release, supply chain, security

Standing list of open, CLI-owned work, ordered by priority within theme. This
file is the source of truth for planned work; it absorbs the former
`docs/plans/roadmap.md` and the repo's GitHub issue backlog (migrated
2026-07-14, each item tagged with its originating `#NNN`).

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

Several open items are one piece of work split across issues. Do them together:

- **`install.ps1` parity:** [#23](https://github.com/pdomain/pdomain-ocr-cli/issues/23) (Now), [#49](https://github.com/pdomain/pdomain-ocr-cli/issues/49), [#24](https://github.com/pdomain/pdomain-ocr-cli/issues/24) — one rewrite of the PowerShell installer to mirror `install.sh` (release-wheel path, pd-index-pip, dependency-confusion guard, installer-arg tests).
- **Workflow supply-chain hardening:** [#37](https://github.com/pdomain/pdomain-ocr-cli/issues/37), [#26](https://github.com/pdomain/pdomain-ocr-cli/issues/26), [#27](https://github.com/pdomain/pdomain-ocr-cli/issues/27), [#28](https://github.com/pdomain/pdomain-ocr-cli/issues/28), [#29](https://github.com/pdomain/pdomain-ocr-cli/issues/29) — one hardening pass over `ci.yml` / `release.yml` (pin actions + uv by SHA, drop persisted creds, remove template injection, cache). Note #37 (ci.yml) is `high` and #26 (release.yml) is `medium` per their labels, but the edit is the same.
- **Durable artifact transaction:** [#17](https://github.com/pdomain/pdomain-ocr-cli/issues/17) → [#21](https://github.com/pdomain/pdomain-ocr-cli/issues/21) → [#22](https://github.com/pdomain/pdomain-ocr-cli/issues/22) — one design: exclusive non-symlink temp files, route all writes through the atomic helper, all-or-nothing promotion with rollback.
- **Release wheel-smoke:** shared sub-task of [#25](https://github.com/pdomain/pdomain-ocr-cli/issues/25), [#30](https://github.com/pdomain/pdomain-ocr-cli/issues/30), [#31](https://github.com/pdomain/pdomain-ocr-cli/issues/31), [#50](https://github.com/pdomain/pdomain-ocr-cli/issues/50) — smoke-install from the built wheel once, referenced by all four.
- **Startup sequencing (`ocr_to_txt`):** [#18](https://github.com/pdomain/pdomain-ocr-cli/issues/18), [#20](https://github.com/pdomain/pdomain-ocr-cli/issues/20), [#39](https://github.com/pdomain/pdomain-ocr-cli/issues/39), [#40](https://github.com/pdomain/pdomain-ocr-cli/issues/40) — adjacent edits to the same input-validation / model-load / layout path; sequence to avoid rework.

---

## Now — highest priority

### Release & CI supply-chain

- [chore/high] Run server-side tests before publishing tag-triggered releases ([#25](https://github.com/pdomain/pdomain-ocr-cli/issues/25))
- [chore/high] Remove template-injection risk from the release-dispatch shell block ([#27](https://github.com/pdomain/pdomain-ocr-cli/issues/27))
- [chore/high] Pin CI workflow actions and uv to immutable versions ([#37](https://github.com/pdomain/pdomain-ocr-cli/issues/37))
- [bug/high] Rewrite `install.ps1` to resolve pd-book-tools from pd-index-pip ([#23](https://github.com/pdomain/pdomain-ocr-cli/issues/23))

### Correctness

- [bug/high] Run layout detection and illustration crops on the rotated page image ([#18](https://github.com/pdomain/pdomain-ocr-cli/issues/18))

### Tests

- [chore/high] Assert default layout reorganization preserves every OCR word ([#41](https://github.com/pdomain/pdomain-ocr-cli/issues/41))

## Next — medium priority

### Release & CI supply-chain

- [chore/medium] Pin release workflow actions and uv to immutable versions ([#26](https://github.com/pdomain/pdomain-ocr-cli/issues/26))
- [chore/medium] Verify downloaded release artifacts in installers ([#30](https://github.com/pdomain/pdomain-ocr-cli/issues/30))
- [bug/medium] Prevent dependency confusion for pd-book-tools installs ([#24](https://github.com/pdomain/pdomain-ocr-cli/issues/24))
- [bug/medium] Make the PowerShell installer use the release wheel path ([#49](https://github.com/pdomain/pdomain-ocr-cli/issues/49))
- [chore/medium] Test all supported Python versions in CI ([#47](https://github.com/pdomain/pdomain-ocr-cli/issues/47))

### Dependency hygiene

- [chore/medium] Bound runtime dependency ranges and smoke-test released installs ([#31](https://github.com/pdomain/pdomain-ocr-cli/issues/31))
- [chore/medium] Add integrity hashes for pd-book-tools lock entries ([#46](https://github.com/pdomain/pdomain-ocr-cli/issues/46))
- [chore/medium] Pin build backend versions used for releases ([#50](https://github.com/pdomain/pdomain-ocr-cli/issues/50))
- [chore/medium] Upgrade the vulnerable idna lock entry ([#51](https://github.com/pdomain/pdomain-ocr-cli/issues/51))

### Runtime security & safety

- [bug/medium] Warn or guard when users supply arbitrary `.pt` model checkpoints ([#16](https://github.com/pdomain/pdomain-ocr-cli/issues/16))
- [bug/medium] Use exclusive, non-symlink temp files for atomic writes ([#17](https://github.com/pdomain/pdomain-ocr-cli/issues/17))
- [chore/medium] Constrain the update-check URL opener to HTTPS-only ([#34](https://github.com/pdomain/pdomain-ocr-cli/issues/34))
- [chore/medium] Add resource limits for untrusted image inputs ([#38](https://github.com/pdomain/pdomain-ocr-cli/issues/38))

### Correctness bugs

- [bug/medium] Skip layout loading and inference for plain `--no-reorg` runs ([#20](https://github.com/pdomain/pdomain-ocr-cli/issues/20))
- [bug/medium] Make JSON and crop writes use the durable atomic-write path ([#21](https://github.com/pdomain/pdomain-ocr-cli/issues/21))
- [bug/medium] Roll back sidecars and crops when the final `.txt` write fails ([#22](https://github.com/pdomain/pdomain-ocr-cli/issues/22))
- [bug/medium] Validate inputs before resolving and loading models ([#39](https://github.com/pdomain/pdomain-ocr-cli/issues/39))
- [bug/medium] Turn startup model and layout failures into clean CLI errors ([#40](https://github.com/pdomain/pdomain-ocr-cli/issues/40))

### Tests

- [chore/medium] Assert `--no-illustration-placeholders` preserves caption text ([#42](https://github.com/pdomain/pdomain-ocr-cli/issues/42))
- [chore/medium] Cover the default layout-enabled end-to-end path ([#43](https://github.com/pdomain/pdomain-ocr-cli/issues/43))

## Later — low priority

### Release & CI

- [chore/low] Disable persisted checkout credentials where not needed ([#28](https://github.com/pdomain/pdomain-ocr-cli/issues/28))
- [chore/low] Disable or harden the setup-uv cache in the release workflow ([#29](https://github.com/pdomain/pdomain-ocr-cli/issues/29))
- [chore/low] Pin pre-commit hooks or enforce reviewed hook updates ([#45](https://github.com/pdomain/pdomain-ocr-cli/issues/45))

### Runtime security & observability

- [chore/low] Avoid shell-interpolated `ARGS` passthrough in local Make targets ([#33](https://github.com/pdomain/pdomain-ocr-cli/issues/33))
- [chore/low] Make best-effort update-check failures diagnosable ([#35](https://github.com/pdomain/pdomain-ocr-cli/issues/35))
- [chore/low] Execute the resolved `nvidia-smi` path for the GPU-nudge probe ([#36](https://github.com/pdomain/pdomain-ocr-cli/issues/36))

### Docs

- [bug/low] Document all accepted image suffixes, including JPEG 2000 ([#44](https://github.com/pdomain/pdomain-ocr-cli/issues/44))
- [bug/low] Align release instructions with `do-release` push behavior ([#48](https://github.com/pdomain/pdomain-ocr-cli/issues/48))

### Deferred features

- Add `--normalize-output {none|ascii|...}` (default `none`) after
  `pdomain-book-tools` provides shared normalization logic and a glyph map. CLI
  work covers the pass-through flag and applying normalization between
  reorganization and text output.

## Blocked

- [bug/high, blocked] Pin default OCR model revisions and avoid unsafe `torch.load` ([#15](https://github.com/pdomain/pdomain-ocr-cli/issues/15)) — **two parts.** Part 1 (pin default model revisions to `v0.6`) is implemented on the local branch `fix/security-15-torch-load-pinning`. Part 2 (`weights_only=True` / safe load) is **blocked upstream on `pd-book-tools#205`**; a tripwire test flips red once that ships. Issue stays open until then. Related trust-boundary work: [#16](https://github.com/pdomain/pdomain-ocr-cli/issues/16) (user-supplied `.pt`).

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
- All 15 slow integration tests pass, including `rotated_page` legitimately.

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
