---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Installers do not verify downloaded release wheel integrity

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** Medium — tampered wheel would install without checksum check
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #30 or related Next roadmap work
- **Search terms:** former GH #30, 2026-07-19-gh-30-installer-artifact-verification, chore
- **Relates to:** [intent map](../context/intent-map.md)

## Summary

install.sh and install.ps1 download the latest release wheel over HTTPS but do not verify a published checksum, GitHub artifact digest, or Sigstore attestation (former GH #30).

Provenance: former GH #30. Roadmap priority: **Next**.

## Impact

- Integrity depends solely on transport and GitHub asset authenticity.
- Intent-map still lists installer verification as deferred work.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Download path has no digest step

Installers use curl / Invoke-WebRequest to fetch the wheel asset, then
`uv tool install` the file. No sha256 comparison against a published sum.

### 2. Intent-map keeps the item deferred

`docs/context/intent-map.md` Deferred work still lists checksums or
attestations for installer-downloaded wheels.

## Root-cause hypotheses

1. **Most likely) Verification never implemented after wheel path landed** — docs still track it as residual.

## Defects to fix

1. Verify downloaded wheels against published checksums or attestations before install.

## Next steps

1. Pick verification source (release asset sidecar, GH API digests, or Sigstore).
2. Implement on both installers with contract tests.

## What is NOT broken (to scope the fix)

- Wheel is taken from GitHub Releases (not git+ install) for normal path.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
