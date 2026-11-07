---
Status: implemented
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Reject oversized image inputs before OCR batching

The CLI will reject files over 100 MiB or decoded images over 100 million pixels before model work begins.

## Agent Index

- **Kind:** spec
- **Status:** implemented
- **Read when:** changing image admission or security limits
- **Search terms:** image byte limit, decompression bomb, pixel limit, former GH 38
- **Relates to:** shipped in commit `7af73fc` (v0.9.1); current behavior is [cli-orchestration.md](../architecture/cli-orchestration.md)

**Implementation plan:** retired after it shipped; see the 2026-11-07 tombstone in [decisions](../context/decisions.md).

## Adopted design

The CLI owns admission limits because it sees filesystem size before decoding and controls batching. It will stat each candidate, reject files above 100 MiB, open only the image header, and reject width times height above 100 million pixels. Rejected files use the existing per-file error path, so other inputs continue.

Processing timeouts are excluded. Safely interrupting native OCR requires subprocess isolation and belongs in a separate design.

## Acceptance criteria

- Byte limits run before Pillow opens the file.
- Pixel limits run before images enter a batch.
- Boundary values are accepted; values one unit above are rejected.
- Errors name the path, observed value, and limit.
- Usage documentation states both fixed limits and the timeout non-goal.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** Implemented with deviations. All five acceptance criteria are met in code.

- Medium: the check runs per chunk after the models load, not before model work begins as the summary says. No oversized decode precedes it, so this is a startup-cost issue, not a gap. Accepted; the usage doc says "before it joins an OCR batch".
- Medium: the cap is per image, while a chunk holds several decoded arrays, about 300 MB each at the cap. There is no aggregate bound. Follow-up.
- Low: `stat()` and `read_bytes()` are separate, so a growing file is not re-checked; formats Pillow cannot read are capped only after decode; a lower caller-set `OPENCV_IO_MAX_IMAGE_PIXELS` makes the error name the wrong limit; no real JP2, multi-frame TIFF or symlink fixtures. Follow-up.
