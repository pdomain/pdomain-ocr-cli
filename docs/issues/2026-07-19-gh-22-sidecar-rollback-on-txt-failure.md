---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# No rollback of sidecars if final .txt write fails

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Medium — partial artifact set possible when .txt write fails late
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #22 or related Next roadmap work
- **Search terms:** former GH #22, 2026-07-19-gh-22-sidecar-rollback-on-txt-failure, bug
- **Relates to:** [CLI orchestration architecture](../architecture/cli-orchestration.md)

## Summary

JSON/crops use exclusive temps and atomic replace; `.txt` is written last as the completeness signal. If that final write fails after sidecars were promoted, the CLI does not delete those sidecars (former GH #22 residual).

Provenance: former GH #22. Roadmap priority: **Next**.

## Impact

- A failed run can leave JSON/crops without the matching .txt.
- Callers treating any sidecar as success may mis-handle partial sets.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Architecture documents write-last, not full rollback

`docs/architecture/cli-orchestration.md` and layout-aware artifact lifecycle
state that write-last is the completeness signal and sidecar rollback is not
implemented.

### 2. PageOutputTransaction is thin

Production path relies on ordering + atomic helpers rather than tracking all
promoted paths for rollback.

## Root-cause hypotheses

1. **Most likely) Write-last was chosen as the shipped design** — full rollback remains optional residual.

## Defects to fix

1. Optional: track promoted sidecars and remove them if final .txt write fails.
2. Or close as won't-fix if write-last completeness is accepted permanently.

## Next steps

1. Owner decision: implement rollback vs accept write-last only.
2. If implementing: transaction list + tests for mid-failure cleanup.

## What is NOT broken (to scope the fix)

- Exclusive temps and atomic JSON/crop/text writes (former GH #17, #21).
- Failure before .txt does not leave a success .txt.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
