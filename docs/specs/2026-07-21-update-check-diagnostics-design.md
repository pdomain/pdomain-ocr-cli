---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: spec
---

# Report update-check failures only in debug mode

The update checker will remain silent by default and explain failures when `PD_OCR_DEBUG` is enabled.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** changing startup notices or update-check errors
- **Search terms:** PD_OCR_DEBUG, update check diagnostics, former GH 35
- **Relates to:** [issue](../issues/2026-07-19-gh-35-update-check-diagnostics.md)

**Implementation plan:** [update-check diagnostics plan](../plans/2026-07-21-update-check-diagnostics.md)

## Adopted design

The existing general debug switch will control diagnostics. The checker will catch failures at its current best-effort boundary and write one concise line to stderr with the exception type and message. Normal runs remain silent and never fail because the network check failed.

## Acceptance criteria

- Default network, JSON, and version errors remain silent.
- `PD_OCR_DEBUG=1` reports each failure on stderr.
- Diagnostics never include a traceback, token, or response body.
- Update checks remain non-fatal.
