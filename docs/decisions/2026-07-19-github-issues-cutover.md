---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: decision
---

# GitHub Issues cutover to governed docs

## Agent Index

- **Kind:** decision
- **Status:** active
- **Read when:** tracing a former GitHub issue number, confirming the tracker is
  empty, or checking what the cutover preserved and what it skipped.
- **Search terms:** GitHub issues cutover, migration, delete issues, tombstone,
  completed-issue ledger, former GH, issue archive, hasIssuesEnabled.

This repository does not use GitHub Issues for planning. Open work lives in
[`docs/roadmap.md`](../roadmap.md). Evidence-bearing defects use
[`docs/issues/`](../issues/README.md). The GitHub Issues **feature is enabled**
so the repo can accept issues later if needed, but the remote tracker holds
**zero** issues (open or closed). Former issue text is recoverable from Git
history only.

## Context

Through mid-July 2026 this repository tracked CLI work in GitHub Issues under
`pdomain/pdomain-ocr-cli`. Cross-repo work stayed in
`ConcaveTrillion/ocr-container-meta`.

On 2026-07-14, 35 open issues were consolidated into
[`docs/roadmap.md`](../roadmap.md) (merge `b2cfd49`, content commit `1c5046f`).
Each item kept its former `#NNN` tag as provenance.

On 2026-07-16, all 50 closed issues were archived into
`docs/decisions/2026-07-16-closed-issues-archive.md` (commit `9498407`), then
removed from the tree so Git history is the tombstone (commit `165013d`). Those
issues were permanently deleted from GitHub the same day. The archive covered
numbers #1–#3 and #5–#51 (#4 was a pull request, not an issue).

The shared runbook at
`shared-devtools/docs/runbooks/github-issues-to-docgraph-migration-prompt.md`
asks for raw SHA digests, per-issue architecture ledgers, an append-only
deletion journal, `docs/issues/` templates, and optionally disabling Issues.
The July cutover shipped a shorter path: roadmap for open work, git tombstone
for closed bodies, and permanent GitHub deletion without those extra artifacts.

Closeout first disabled Issues, then re-enabled the feature with an empty
tracker so the UI stays available while planning remains in-repo.

## Decision

1. **Keep the GitHub Issues feature enabled** on `pdomain/pdomain-ocr-cli`, and
   keep the remote issue count at **zero** (no open and no closed issues). Do
   not restore deleted historical issues.
2. **Treat `docs/roadmap.md` as the standing backlog** for CLI-owned open work.
   Tags like `former GH #25` are provenance only; they are not live tracker
   links.
3. **Use `docs/issues/`** only for governed, evidence-bearing bug and
   investigation reports (template: `docs/issues/TEMPLATE.md`). Do not recreate
   one file per former GitHub chore.
4. **Do not file routine backlog items on GitHub Issues** for this repo. If an
   issue is filed on GitHub by mistake, either move it into the roadmap or a
   governed `docs/issues/` report and delete the GitHub issue so the count
   returns to zero—or deliberately keep it only after an owner decision to
   resume GitHub tracking.
5. **Accept residual runbook gaps as known risk**, documented in the ledger
   below, rather than re-deriving digests that GitHub can no longer supply.
6. **Recover closed-issue text** with:

   ```bash
   git show 9498407:docs/decisions/2026-07-16-closed-issues-archive.md
   ```

## Consequences

- Former issue URLs under `github.com/pdomain/pdomain-ocr-cli/issues/N` no longer
  resolve (issues were deleted, not merely closed).
- Agents and humans plan from the roadmap, intent map, and architecture docs.
- Cross-cut work still uses `ConcaveTrillion/ocr-container-meta` when a milestone
  points there.
- The Issues tab can appear empty; that is intentional until an owner chooses
  otherwise.
- Strict runbook auditors must read the residual-gap section; this decision is
  the durable statement that digests and a pre-delete journal were not produced.

## Supersedes / Superseded-by

Supersedes the former populated GitHub Issues backlog for this repository. Does
not supersede `docs/roadmap.md` or architecture docs.

## Completed-issue ledger (compact)

| Former GH | State at cutover | Local destination | Deletion |
| --- | --- | --- | --- |
| #15–#51 open set (35 issues) consolidated 2026-07-14 | open → planned | [`docs/roadmap.md`](../roadmap.md) (Now / Next / Later / Blocked) with `former GH #NNN` tags | Deleted from GitHub with the rest of the tracker |
| #1–#3, #5–#51 closed set (50 issues) | closed COMPLETED | Git tombstone commit `9498407` path `docs/decisions/2026-07-16-closed-issues-archive.md` (removed in `165013d`) | Deleted from GitHub 2026-07-16 |

Exact open-item titles and priority order live only in the roadmap (not restated
here). Exact closed bodies live only in the tombstone commit.

Open-item numbers still referenced from the roadmap include at least former GH
15–18, 20–31, 33–51 (and work-cluster cross-refs among them).

## Residual gaps vs the shared runbook

| Runbook expectation | Status after closeout |
| --- | --- |
| Raw per-issue API exports + SHA-256 digests | Not produced; GitHub issues already deleted |
| Per-closed-issue architecture coverage + adversarial review | Not produced; product behavior remains in architecture, usage, code, and tests |
| Append-only deletion journal before each delete batch | Not produced; this decision is the post-hoc record |
| `docs/issues/` README + template | Installed in this closeout |
| Empty remote tracker | Zero open + zero closed issues verified after re-enable |
| One governed issue file per open GH item | Rejected; roadmap is the backlog |

## Migration manifest (closeout)

```text
GITHUB ISSUE MIGRATION MANIFEST
  Repository: pdomain/pdomain-ocr-cli
  Worktree / branch: docs/github-issues-cutover-closeout (merged to master a9169ca)
  Merged default-branch commits (prior cutover):
    1c5046f / b2cfd49  open issues → docs/roadmap.md
    9498407            closed-issue archive added
    165013d            archive removed (git tombstone)
    a9169ca            cutover closeout docs
  Open issues discovered at consolidation: 35
  Closed issues archived: 50
  Active issue documents created from GH: 0 (roadmap used instead)
  Completed-issue ledger: this document (compact)
  Architecture documents created by cutover: none (existing architecture kept)
  Decisions and intent updated: this decision; current-state; intent-map; docs README
  Owner decisions remaining: none for cutover itself
  Residual risk: no raw digests or pre-delete journal
  GitHub issues remaining: 0 open, 0 closed
  GitHub Issues feature enabled: yes (empty tracker)
```
