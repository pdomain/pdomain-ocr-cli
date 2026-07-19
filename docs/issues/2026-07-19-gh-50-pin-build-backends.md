---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Build backend requirements are unpinned

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Medium — hatchling/hatch-vcs float at release build time
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #50 or related Next roadmap work
- **Search terms:** former GH #50, 2026-07-19-gh-50-pin-build-backends, chore
- **Relates to:** [roadmap](../roadmap.md)

## Summary

`[build-system] requires` lists `hatchling` and `hatch-vcs` without version pins. Release builds use `uv build` with that floating set (former GH #50).

Provenance: former GH #50. Roadmap priority: **Next**.

## Impact

- Release reproducibility can change when hatch releases break builds.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. pyproject build-system is unpinned

`requires = ["hatchling", "hatch-vcs"]` with no version constraints.

## Root-cause hypotheses

1. **Most likely) Pins never added after hatch-vcs adoption** — tracked as residual hygiene.

## Defects to fix

1. Pin hatchling and hatch-vcs versions used for releases.

## Next steps

1. Choose known-good versions; pin in pyproject; verify `uv build` and wheel-smoke.

## What is NOT broken (to scope the fix)

- hatch-vcs version derivation from git tags works with current floors.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
