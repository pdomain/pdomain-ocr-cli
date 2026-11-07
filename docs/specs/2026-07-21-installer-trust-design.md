---
Status: implemented
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Bind installer indexes and verify release wheel digests

Both installers will bind private package names to the pdomain index and verify the CLI wheel before installation.

## Agent Index

- **Kind:** spec
- **Status:** implemented
- **Read when:** changing POSIX or PowerShell release installers
- **Search terms:** dependency confusion, artifact digest, uv index strategy, former GH 24, former GH 30
- **Relates to:** shipped in commit `23f263e` (v0.9.1); current behavior is [cli-orchestration.md](../architecture/cli-orchestration.md)

**Implementation plan:** retired after it shipped; see the 2026-11-07 tombstone in [decisions](../context/decisions.md).

## Adopted design

Installers will use uv's first-index resolution so a package found on the pdomain index cannot be replaced by a same-named PyPI package. The release wheel still comes from GitHub Releases.

The installers will read the wheel asset's `digest` from the GitHub Releases API. They will accept only `sha256:<64 lowercase hex characters>`, calculate the local SHA-256, compare in constant textual form, and stop before `uv tool install` on any error.

## Acceptance criteria

- Both installers use the same first-index policy.
- A secondary-index package cannot win for a pdomain name.
- Both installers verify the selected wheel against the API digest.
- Missing, malformed, and mismatched digests fail closed.
- Installer contract tests cover POSIX and PowerShell scripts.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** Implemented with deviations.

- Medium: `first-index` protects only names the pdomain index lists. PyPI stays in the index list, so an unlisted pdomain-* name can still resolve from PyPI. The architecture doc now says so. Restricting resolution further is a follow-up.
- Medium: on the `gh` path, a release record with no digest fails closed instead of falling back to the REST API, which would supply one. No test covers it. Follow-up.
- Medium: Windows PowerShell 5.1 is untested on a real host and does not force TLS 1.2. Follow-up.
- Medium: `install.sh` parses JSON with regexes over minimal fixtures; nested objects or several wheels could misparse. It fails closed. Follow-up.
- Low: the digest comes from the same API as the wheel, so it catches corruption, not a replaced asset, and dependencies are not hash-checked. Documented. `install.sh` overwrites `TMPDIR`, and a comment still cites the removed `release.yml`. Follow-up.
