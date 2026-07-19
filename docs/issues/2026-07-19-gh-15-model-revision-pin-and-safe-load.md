---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Default OCR model revisions unpinned; safe torch.load blocked upstream

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** High — mutable model defaults and unsafe deserialize residual
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #15 or related Blocked roadmap work
- **Search terms:** former GH #15, 2026-07-19-gh-15-model-revision-pin-and-safe-load, bug
- **Relates to:** [roadmap](../roadmap.md)

## Summary

Part 1: default model revision pin is not on master (may exist on `fix/security-15-torch-load-pinning`). Part 2: safe `weights_only` / torch.load hardening is blocked on upstream pdomain-book-tools work. Warn-side for user .pt paths shipped as former GH #16 (former GH #15).

Provenance: former GH #15. Roadmap priority: **Blocked**.

## Impact

- Defaults can float to unexpected model revisions.
- Unsafe deserialize path remains until upstream lands.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Roadmap Blocked section

`docs/roadmap.md` documents both parts and the upstream block.

### 2. Warn-side shipped separately

`_model_security.py` warns on custom .pt / mutable revision; tests cover
warnings. That does not pin defaults or enable weights_only.

## Root-cause hypotheses

1. **Most likely) Split work: CLI pin + upstream safe load** — part 2 cannot finish in this repo alone.

## Defects to fix

1. Land default revision pin on master when ready (part 1).
2. Add tripwire / integration once upstream safe load ships (part 2).

## Next steps

1. Track upstream safe-load issue; merge part 1 when reviewed.
2. Keep #16 warnings until stronger load policy exists.

## What is NOT broken (to scope the fix)

- User-supplied .pt warning path (former GH #16).

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
