---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# No multiset test that default layout reorganization preserves every OCR word

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** High — word-drop regression could slip under default layout
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #41 or related Now roadmap work
- **Search terms:** former GH #41, 2026-07-19-gh-41-default-layout-word-preservation-test, chore
- **Relates to:** [test-suite architecture](../architecture/test-suite.md)

## Summary

The no-silent-drop rule is policy and is tested for fakes / `--layout-model none` paths and caption-placeholder behavior. There is still no multiset oracle that every OCR word survives under default layout reorganization (former GH #41).

Provenance: former GH #41. Roadmap priority: **Now**.

## Impact

- A regression that drops words only when default layout reorg runs may not fail CI.
- Slow default-layout tests prove the path runs, not bag-of-words preservation.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Architecture documents the coverage gap

`docs/architecture/test-suite.md` § Word preservation states that fast cases
often force `--layout-model none` or use `FakePage`, and slow default-layout
tests do not assert a multiset oracle.

### 2. Existing preservation tests avoid default layout reorg

Word-preservation style tests in the fast suite use controlled fakes or
layout-none configuration rather than production default layout reorg.

## Root-cause hypotheses

1. **Most likely) Gap is pure test debt** — implementation may already preserve words; CI does not prove it for default layout.
2. **Alternative) Real reorg has edge cases not covered by FakePage** — slow multiset test would catch them.

## Defects to fix

1. Add assertion (fast layout-enabled reorg and/or slow default layout) that every OCR word is preserved as a multiset.

## Next steps

1. Design oracle (bag-of-words / validate_word_preservation) on a fixture page.
2. Land test under fast if deterministic, else slow with pinned models.

## What is NOT broken (to scope the fix)

- Caption preservation with `--no-illustration-placeholders` is tested (former GH #42).
- Default-layout slow path smoke exists (former GH #43).

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
