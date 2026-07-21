---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: spec
---

# Reject oversized image inputs before OCR batching

The CLI will reject files over 100 MiB or decoded images over 100 million pixels before model work begins.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** changing image admission or security limits
- **Search terms:** image byte limit, decompression bomb, pixel limit, former GH 38
- **Relates to:** [issue](../issues/2026-07-19-gh-38-untrusted-image-resource-limits.md)

**Implementation plan:** [image limits plan](../plans/2026-07-21-image-resource-limits.md)

## Adopted design

The CLI owns admission limits because it sees filesystem size before decoding and controls batching. It will stat each candidate, reject files above 100 MiB, open only the image header, and reject width times height above 100 million pixels. Rejected files use the existing per-file error path, so other inputs continue.

Processing timeouts are excluded. Safely interrupting native OCR requires subprocess isolation and belongs in a separate design.

## Acceptance criteria

- Byte limits run before Pillow opens the file.
- Pixel limits run before images enter a batch.
- Boundary values are accepted; values one unit above are rejected.
- Errors name the path, observed value, and limit.
- Usage documentation states both fixed limits and the timeout non-goal.
