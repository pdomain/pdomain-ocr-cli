---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: process
Level: I1
---

# Issues

## Agent Index

- **Kind:** process
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Read when:** filing a bug / defect / investigation report, or looking up an
  open issue's status, evidence, or resolution.
- **Search terms:** issues folder, bug report, defect report, issue template,
  issue lifecycle, kind issue.

## Purpose

`docs/issues/` holds **governed, evidence-bearing issue reports** — bugs, silent
failures, regressions, and investigations that need a durable, citable record
(not a throwaway chat summary). Each report is a docgraph node so it is
retrievable, linkable from specs/plans/context, and carried in the repo rather
than in per-machine harness memory.

## Convention

- **Location:** `docs/issues/`
- **Filename:** `YYYY-MM-DD-short-slug.md` (creation date + a terse kebab slug).
- **Metadata:** YAML frontmatter **and** a matching `## Agent Index` block. Keep
  frontmatter `Status:` and Agent Index `Status:` identical — a mismatch trips a
  `field_conflict` (→ `status-reconciler`).
  - `Kind: issue`
  - `Level:` informational scope — `I1` repo-wide, `I2` narrow/local.
  - `Status:` governed lifecycle, **not** the issue's open/closed state (see below).
- **Issue state vs governed status:** the docgraph lifecycle is
  `draft → active → implemented → retired`. Express the *issue's* resolution state
  as a separate **`Resolution:`** line in the Agent Index (`Open` / `Resolved` /
  `Won't fix` / `Duplicate`) and a final `## Resolution` section. Map the governed
  `Status:`:
  - **Open** → `Status: active`.
  - **Resolved / Won't fix / Duplicate** → route through `doc-retirer`, which
    **deletes** the report. Promote any specific a reader still needs into the
    architecture or process doc that owns it, repoint inbound references at the
    resolving commit, drop the pointer below, and append a tombstone to
    `docs/context/decisions.md`. Git history keeps the report, so no resolved
    file stays in the tree and there is no resolved index to maintain.
- **Link it (no orphans):** reference every new issue from a governed doc — by
  default an **Open issues** bullet in
  [`docs/context/intent-map.md`](../context/intent-map.md), a Risk in
  [`docs/context/current-state.md`](../context/current-state.md), or the standing
  backlog in [`docs/roadmap.md`](../roadmap.md). This `README` also lists live
  governed issues below, which satisfies the no-orphan rule.
- **Stage + reindex:** under `mode = "git"` a new doc is invisible until
  `git add`ed; stage it, then `docgraph reindex` and `docgraph check --strict` the
  same turn (a new `dangling` blocks completion).
- **Template:** copy `TEMPLATE.md` in this folder. It is index-excluded (a
  top-of-file `<!-- docgraph: ignore -->` marker), so **do not markdown-link to
  it** from a governed doc — the link would dangle. Refer to it by path / inline
  code.

Standing CLI backlog (release, supply-chain, correctness chores) lives in
[`docs/roadmap.md`](../roadmap.md), not as one file per former GitHub number.
Use this folder for evidence-bearing bugs and investigations only. The GitHub
Issues feature is enabled but the remote tracker is kept empty; see
[`docs/decisions/2026-07-19-github-issues-cutover.md`](../decisions/2026-07-19-github-issues-cutover.md).

## Recommended structure

Summary · Impact · Environment/versions · Evidence (reproduction & diagnosis,
with commands/output) · Root-cause hypotheses (ranked) · Defects to fix ·
Recommended next steps · What is NOT broken (scopes the fix) · Resolution.

Lead with the **smallest decisive evidence**, separate **observation** from
**hypothesis**, and always include a **What is NOT broken** section.

## Open issues

- [Weekly dep-refresh branches and pull requests accumulate instead of landing](2026-08-08-dep-refresh-cannot-auto-land.md) (found 2026-08-08; Now)
- [Layout detection and illustration crops use the unrotated page image](2026-07-19-gh-18-layout-crops-ignore-rotation.md) (former GH #18; Now)
- [No multiset test that default layout reorganization preserves every OCR word](2026-07-19-gh-41-default-layout-word-preservation-test.md) (former GH #41; Now)
- [Installers do not pin pdomain packages against dependency confusion](2026-07-19-gh-24-installer-dependency-confusion.md) (former GH #24; Next)
- [Installers do not verify downloaded release wheel integrity](2026-07-19-gh-30-installer-artifact-verification.md) (former GH #30; Next)
- [Runtime dependency ranges have no upper bounds](2026-07-19-gh-31-runtime-dep-upper-bounds.md) (former GH #31; Next)
- [Build backend requirements are unpinned](2026-07-19-gh-50-pin-build-backends.md) (former GH #50; Next)
- [No resource limits for untrusted image inputs](2026-07-19-gh-38-untrusted-image-resource-limits.md) (former GH #38; Next)
- [Update-check failures are swallowed without diagnostics](2026-07-19-gh-35-update-check-diagnostics.md) (former GH #35; Next)
- [No rollback of sidecars if final .txt write fails](2026-07-19-gh-22-sidecar-rollback-on-txt-failure.md) (former GH #22; Next)
- [Pre-commit hook revisions use mutable version tags](2026-07-19-gh-45-pre-commit-immutable-pins.md) (former GH #45; Next)
- [Default OCR model revisions unpinned; safe torch.load blocked upstream](2026-07-19-gh-15-model-revision-pin-and-safe-load.md) (former GH #15; Blocked)
- [Deferred: --normalize-output flag after upstream glyph map](2026-07-19-normalize-output-flag-deferred.md) (deferred; Later)

Resolved reports are deleted, so this index tracks open work only. Past
resolutions live in the `docs/context/decisions.md` tombstones and in git
history.
