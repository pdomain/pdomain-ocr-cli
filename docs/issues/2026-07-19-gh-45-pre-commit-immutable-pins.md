---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Pre-commit hook revisions use mutable version tags

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Medium — hook tags can move; not full commit SHAs
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #45 or related Next roadmap work
- **Search terms:** former GH #45, 2026-07-19-gh-45-pre-commit-immutable-pins, chore
- **Relates to:** [intent map](../context/intent-map.md)

## Summary

`.pre-commit-config.yaml` pins hooks with version tags (e.g. v0.15.22) and runs `pre-commit-update` for reviewed bumps. Immutable full commit SHA pins are not used (former GH #45 residual).

Provenance: former GH #45. Roadmap priority: **Next**.

## Impact

- Tag mutability is a residual supply-chain concern if tags were rewritten.
- Weekly dep-refresh and local commits can fight pin policy if inconsistent.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Config uses tag revs

`.pre-commit-config.yaml` `rev:` fields are version tags, not 40-char SHAs.

### 2. Auto-update hook present

`pre-commit-update` rewrites revs when newer tags exist.

## Root-cause hypotheses

1. **Most likely) Tags + pre-commit-update accepted as maintainable compromise** — intent still allows SHA pins if workflow supports them.

## Defects to fix

1. Either pin revs to full SHAs with a maintainable update path, or formally accept tags + pre-commit-update in decisions.

## Next steps

1. Owner decision on tags vs SHAs.
2. Align dep-refresh so CI does not fail on pre-commit-update churn.

## What is NOT broken (to scope the fix)

- Hooks run in CI and local pre-commit; versions are not floating `main`.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
