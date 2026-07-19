---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# No resource limits for untrusted image inputs

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Medium — huge or malicious images can exhaust resources
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #38 or related Next roadmap work
- **Search terms:** former GH #38, 2026-07-19-gh-38-untrusted-image-resource-limits, chore
- **Relates to:** [intent map](../context/intent-map.md)

## Summary

The CLI does not enforce file-size, decoded-pixel, or processing-time limits on image inputs. Intent-map still lists this as deferred (former GH #38).

Provenance: former GH #38. Roadmap priority: **Next**.

## Impact

- Hostile or accidental huge inputs can cause memory/CPU exhaustion.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. No limiters in CLI package

No file-size / decoded-pixel / decode-time guards under `pdomain_ocr_cli/`.

### 2. Decisions / intent still deferred

Authored context records image resource limits as remaining / deferred work.

## Root-cause hypotheses

1. **Most likely) Feature never scheduled after security review** — documented residual only.

## Defects to fix

1. Add resource limits (size / pixels / time boundary) and document them.

## Next steps

1. Decide whether limits live in CLI, book-tools, or both.
2. Implement and document in usage architecture.

## What is NOT broken (to scope the fix)

- Normal page-sized book scans are the intended input shape.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
