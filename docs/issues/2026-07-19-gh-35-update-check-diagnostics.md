---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Update-check failures are swallowed without diagnostics

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Medium — broken update check fails closed with no signal
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #35 or related Next roadmap work
- **Search terms:** former GH #35, 2026-07-19-gh-35-update-check-diagnostics, chore
- **Relates to:** [roadmap](../roadmap.md)

## Summary

`check_for_update` ends with a bare `except Exception: pass`, so network/parse failures are silent. There is no env flag or debug log for diagnosis (former GH #35).

Provenance: former GH #35. Roadmap priority: **Next**.

## Impact

- Users cannot tell update-check is broken vs up-to-date.
- Support debugging of the best-effort path is harder.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Bare except in update check

`pdomain_ocr_cli/_update_check.py` swallows all exceptions at the end of
`check_for_update` with no log line.

## Root-cause hypotheses

1. **Most likely) Best-effort design intentionally silent** — needs opt-in diagnostics without noisy default.

## Defects to fix

1. Surface failures under a debug env (or similar) while keeping quiet default.

## Next steps

1. Add `PD_OCR_UPDATE_CHECK_DEBUG` (or reuse existing notice flags) and tests.

## What is NOT broken (to scope the fix)

- HTTPS-only URL constraint for the check is implemented (former GH #34).

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
