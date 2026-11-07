---
Status: implemented
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Report update-check failures only in debug mode

The update checker will remain silent by default and explain failures when `PD_OCR_DEBUG` is enabled.

## Agent Index

- **Kind:** spec
- **Status:** implemented
- **Read when:** changing startup notices or update-check errors
- **Search terms:** PD_OCR_DEBUG, update check diagnostics, former GH 35
- **Relates to:** shipped in commit `b9e1f02` (v0.9.1); current behavior is [cli-orchestration.md](../architecture/cli-orchestration.md)

**Implementation plan:** retired after it shipped; see the 2026-11-07 tombstone in [decisions](../context/decisions.md).

## Adopted design

The existing general debug switch will control diagnostics. The checker will catch failures at its current best-effort boundary and write one concise line to stderr with the exception type and message. Normal runs remain silent and never fail because the network check failed.

## Acceptance criteria

- Default network, JSON, and version errors remain silent.
- `PD_OCR_DEBUG=1` reports each failure on stderr.
- Diagnostics never include a traceback, token, or response body.
- Update checks remain non-fatal.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** Implemented with deviations.

- Medium: three failures stay silent even with `PD_OCR_DEBUG=1`: a non-list response such as a rate-limit reply, no stable tag, and an unparseable current version. Documented; reporting them is a follow-up.
- Medium: the message prints the exception text unscrubbed. The URL carries no token, so nothing leaks today, but nothing enforces the criterion. Documented. Follow-up.
- Medium: only the timeout failure has a debug-on test. Follow-up.
- Low: accepted truthy values for `PD_OCR_DEBUG` are undocumented; a late diagnostic from the background thread can be lost or interleaved; module docstrings still say errors are swallowed. Follow-up.
