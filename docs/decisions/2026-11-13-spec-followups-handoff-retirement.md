---
Status: active
Owner: CT
Created: 2026-11-13
Last verified: 2026-11-13
Kind: decision
---

# Retire the completed spec-review handoff

The spec-review handoff is retired because its implementation commits are
already on local master. Its resume instructions no longer describe pending
work. This retirement does not release those commits.

## Context

The handoff at
`docs/handoff/2026-11-11-032239-spec-review-follow-ups-ready-for-review.md`
recorded the paused `fix/spec-review-followups` work. Commits `ddf6f3f`
through `211708f` are ancestors of `10cbac7`. Later commits `637570a`,
`318cb60`, and `4b50f8d` retired shipped specs, shared the quote/dash helpers,
and completed the batch-angle boundary.

The handoff had authored kind, status, owner, creation, branch, and base-commit
metadata. It is a handoff, not a spec or an implementation plan. The
normalize-output spec and plan remain active because the flag is not built.

## Decision

Retire and delete the completed handoff. The current behavior and verification
limits live in [CLI orchestration](../architecture/cli-orchestration.md),
[layout-aware OCR](../architecture/layout-aware-ocr.md), and
[test-suite architecture](../architecture/test-suite.md). Unfinished work and
owner choices remain in the [intent map](../context/intent-map.md).

The old handoff recorded CPU-only historical checks and a `/tmp` quota
workaround. It also recorded that its standalone readability editor did not
run. This pass does not retroactively claim that review. The existing
[current state](../context/current-state.md) retains the historical test
results and temporary-directory advice. Test-suite architecture retains the
unverified real Windows PowerShell 5.1 check.

## Consequences

The obsolete resume and merge instructions leave the working tree. Git keeps
the original record. There were no inbound graph edges: MCP neighbors returned
no indexed node for the handoff. Exact tracked-file searches for its path,
filename, and former worktree found no external references to repoint.

- Old path: `docs/handoff/2026-11-11-032239-spec-review-follow-ups-ready-for-review.md`
- Outcome: retired after implementation and local integration.
- Removal commit: the commit adding this decision and deleting the old path.
- Rationale kept: this decision and the three architecture documents above.
- Remaining work: normalization, owner choices, and Windows PowerShell 5.1
  verification remain open; no feature or compatibility work is closed here.

## Supersedes / Superseded-by

Supersedes the completed handoff's resume instructions. It does not supersede
its historical evidence, the live normalization spec or plan, or prior owner
decisions. No later decision supersedes this receipt.
