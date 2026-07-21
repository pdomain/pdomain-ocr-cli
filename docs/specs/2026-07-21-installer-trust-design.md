---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: spec
---

# Bind installer indexes and verify release wheel digests

Both installers will bind private package names to the pdomain index and verify the CLI wheel before installation.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** changing POSIX or PowerShell release installers
- **Search terms:** dependency confusion, artifact digest, uv index strategy, former GH 24, former GH 30
- **Relates to:** [dependency-confusion issue](../issues/2026-07-19-gh-24-installer-dependency-confusion.md), [artifact-verification issue](../issues/2026-07-19-gh-30-installer-artifact-verification.md)

**Implementation plan:** [installer trust plan](../plans/2026-07-21-installer-trust.md)

## Adopted design

Installers will use uv's first-index resolution so a package found on the pdomain index cannot be replaced by a same-named PyPI package. The release wheel still comes from GitHub Releases.

The installers will read the wheel asset's `digest` from the GitHub Releases API. They will accept only `sha256:<64 lowercase hex characters>`, calculate the local SHA-256, compare in constant textual form, and stop before `uv tool install` on any error.

## Acceptance criteria

- Both installers use the same first-index policy.
- A secondary-index package cannot win for a pdomain name.
- Both installers verify the selected wheel against the API digest.
- Missing, malformed, and mismatched digests fail closed.
- Installer contract tests cover POSIX and PowerShell scripts.
