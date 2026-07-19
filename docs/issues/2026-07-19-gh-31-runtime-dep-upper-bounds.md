---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Runtime dependency ranges have no upper bounds

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Medium — breaking upstream releases can install without a cap
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #31 or related Next roadmap work
- **Search terms:** former GH #31, 2026-07-19-gh-31-runtime-dep-upper-bounds, chore
- **Relates to:** [roadmap](../roadmap.md)

## Summary

Wheel-smoke for Python 3.11–3.13 ships, but pyproject runtime deps use lower floors only (no upper compatibility caps) for book-tools, ops, and related pins (former GH #31 residual).

Provenance: former GH #31. Roadmap priority: **Next**.

## Impact

- A major breaking release of a floor-only dependency can install on next refresh.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. pyproject lower floors only

Runtime requirements use `>=` floors without upper caps.

### 2. Wheel-smoke half is done

`make wheel-smoke` / CI install the built wheel on 3.11–3.13 and run
`pdomain-ocr --version`.

## Root-cause hypotheses

1. **Most likely) Intentional floors-only until compatibility policy decided** — intent-map still wants caps evaluated.

## Defects to fix

1. Decide and apply upper bounds or compatibility caps for runtime (and related) deps.

## Next steps

1. Review latest known-good ranges for pdomain packages and huggingface_hub.
2. Update pyproject + lock; keep wheel-smoke green.

## What is NOT broken (to scope the fix)

- Wheel-smoke multi-version install already exists.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
