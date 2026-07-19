---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Installers do not pin pdomain packages against dependency confusion

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Medium — malicious public package could shadow private name
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #24 or related Next roadmap work
- **Search terms:** former GH #24, 2026-07-19-gh-24-installer-dependency-confusion, bug
- **Relates to:** [CLI orchestration architecture](../architecture/cli-orchestration.md)

## Summary

install.sh and install.ps1 pass the pdomain index as an extra index and install a release wheel, but they do not bind `pdomain-book-tools` (and related names) so a same-named package on public PyPI cannot win resolution (former GH #24).

Provenance: former GH #24. Roadmap priority: **Next**.

## Impact

- Supply-chain risk on end-user install if a confusing public package exists.
- Dev uv sources with explicit indexes are not the installer contract.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Installers use extra-index-url only

`install.sh` and `install.ps1` pass `--extra-index-url` for pdomain-index-pip.
Contract tests assert the URL presence, not exclusive index binding.

### 2. Dev lock uses explicit sources; installers do not

`pyproject.toml` `[tool.uv.sources]` with `explicit = true` applies to the
dev/project uv environment, not to `uv tool install` of the downloaded wheel.

## Root-cause hypotheses

1. **Most likely) Install path never got the named-index / package-index pin** — parity work stopped at wheel + extra-index.

## Defects to fix

1. Harden installer uv invocation (named index + package binding or equivalent) for pdomain packages.
2. Extend install.sh / install.ps1 contract tests for the guard.

## Next steps

1. Choose uv flag strategy that cannot resolve private names from PyPI first.
2. Implement on both POSIX and PowerShell installers.

## What is NOT broken (to scope the fix)

- Release-wheel install path and pd-index-pip URL are implemented (former GH #23, #49).

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
