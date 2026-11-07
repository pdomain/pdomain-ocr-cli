---
Status: implemented
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Propagate OCR rotation into layout and crop processing

Layout detection and illustration cropping will use the same oriented pixels that OCR used.

## Agent Index

- **Kind:** spec
- **Status:** implemented
- **Read when:** implementing rotated layout or crop handling
- **Search terms:** rotation metadata, layout crop, former GH 18
- **Relates to:** shipped in commit `c325c13` (v0.9.0); current behavior is [layout-aware-ocr.md](../architecture/layout-aware-ocr.md)

**Implementation plan:** retired after it shipped; see the 2026-11-07 tombstone in [decisions](../context/decisions.md).

## Adopted design

`pdomain-book-tools` must first expose the selected quarter-turn angle on each OCR result. The CLI batch adapter will pair every page result with that angle. It will rotate the in-memory image before layout detection, debug rendering, and illustration cropping.

The CLI will not infer orientation a second time. A missing angle means zero rotation for compatibility. Any non-quarter-turn value fails explicitly because crop coordinates would be ambiguous.

## Acceptance criteria

- The upstream result contract exposes `rotation_degrees` as one of `0`, `90`, `180`, or `270`.
- Single-page and batch paths orient pixels identically.
- Layout regions and illustration crops align with rotated text.
- The existing unrotated path remains byte-for-byte equivalent.
- Regression coverage uses `tests/fixtures/rotated_page.png`.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** Implemented with deviations.

- Medium: only the single-image OCR path records the angle (`ocr_to_txt.py:513`). The batch path relies on `pdomain-book-tools` storing an upright buffer; without it, a rotated page gets layout and crops from the on-disk file with no error. The design's "every result carries an angle" criterion is not met. Documented in `layout-aware-ocr.md`; a batch-path test is a follow-up.
- Medium: the rotate branch of `upright_layout_source` is a fallback that production rarely reaches. Its direction is tested only for 90° on a synthetic array, not 180° or 270°. The direction is correct today (`np.rot90(k=-1)` upstream). Follow-up.
- Medium: the main regression test uses mocks and checks that the stored buffer is passed through, not that crop pixels come from the upright image. The `rotated_page.png` criterion is met only nominally. Follow-up.
- Low: float or numpy-integer angles fail the page with `ValueError`; out-of-range crop boxes are clamped or skipped silently; the byte-for-byte unrotated criterion is untested. The clamp and skip are documented.
