---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-07-19
Kind: issue
Level: I1
---

# Layout detection and illustration crops use the unrotated page image

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-19
- **Resolution:** Open
- **Severity:** High — layout and crops misaligned with OCR text on rotated pages
- **Affected version:** pdomain-ocr-cli master @ 3a818aa (docs baseline)
- **Read when:** working on former GH #18 or related Now roadmap work
- **Search terms:** former GH #18, 2026-07-19-gh-18-layout-crops-ignore-rotation, bug
- **Relates to:** [layout-aware OCR architecture](../architecture/layout-aware-ocr.md)

## Summary

OCR may auto-rotate a page for best text confidence, but layout detection and illustration crops still run on the original on-disk image path. The single-image OCR path discards the rotation angle. Architecture previously overstated alignment; the gap is former GH #18.

Provenance: former GH #18. Roadmap priority: **Now**.

## Impact

- Rotated book pages can get figure crops and layout regions that do not match the upright text stream.
- Caption tagging and extract-illustrations can disagree with OCR orientation.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master (docs reports added on docs/open-issue-reports)
GitHub Issues: enabled, 0 open, 0 closed
```

## Evidence

### 1. Layout uses the path as stored on disk

In `pdomain_ocr_cli/ocr_to_txt.py`, layout detection is invoked with the input
image path (not a rotated buffer). Illustration crops use `cv2.imread` on the
same original path.

### 2. Rotation angle is dropped on the single-image path

The OCR helper returns `(doc, rotation)` but the caller binds rotation to `_`
and does not feed it into layout or crop steps.

### 3. Architecture records the gap

`docs/architecture/layout-aware-ocr.md` § Page rotation documents this as an
open CLI gap (former GH #18).

## Root-cause hypotheses

1. **Most likely) Rotation is applied only inside the OCR backend for text** — layout and crops never receive the chosen angle.
2. **Alternative) Batch path may differ from single-image** — confirm both paths discard or keep rotation the same way.

## Defects to fix

1. Wire OCR rotation into layout detection and illustration crop inputs (primary).
2. Add regression coverage with `tests/fixtures/rotated_page.png` plus layout or `--extract-illustrations`.

## Next steps

1. Trace single-image and batch paths for where rotation is available.
2. Implement rotate-then-detect/crop; update architecture when behavior matches.

## What is NOT broken (to scope the fix)

- OCR auto-rotation for text confidence still works.
- Plain `--no-reorg` layout skip (former GH #20) is implemented.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
