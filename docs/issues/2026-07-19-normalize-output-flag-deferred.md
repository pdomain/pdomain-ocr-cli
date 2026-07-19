---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Deferred: --normalize-output flag after upstream glyph map

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Low — feature not implemented; blocked on upstream
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on deferred feature (no former GH number) or related Later roadmap work
- **Search terms:** deferred feature (no former GH number), 2026-07-19-normalize-output-flag-deferred, feature
- **Relates to:** [usage future proposal](../usage/cli-usage.md)

## Summary

Add `--normalize-output {none|ascii|...}` (default none) only after pdomain-book-tools provides shared normalization logic and a glyph map. CLI owns flag name, help, defaults, and applying normalization between reorg and text output.

Provenance: deferred feature (no former GH number). Roadmap priority: **Later**.

## Impact

- No user-facing normalize mode until upstream is ready.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Documented as not implemented

`docs/usage/cli-usage.md` Future proposal and roadmap Deferred features
describe the flag without argparse support.

### 2. Intent-map active bet

Normalization is deferred until shared upstream logic exists.

## Root-cause hypotheses

1. **Most likely) Correctly blocked on upstream library work** — no CLI-only implementation yet.

## Defects to fix

1. None until upstream ships; then add thin CLI pass-through.

## Next steps

1. Watch pdomain-book-tools for glyph map / normalize API.
2. Then implement flag + tests + usage docs.

## What is NOT broken (to scope the fix)

- Existing `--straight-quotes` / em-dash helpers remain separate small tools.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
