---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: spec
---

# Prove default layout preserves every OCR word

A slow integration test will compare word multisets before and after default layout reorganization.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** changing default layout or word-preservation coverage
- **Search terms:** word multiset, default layout, two column, former GH 41
- **Relates to:** [issue](../issues/2026-07-19-gh-41-default-layout-word-preservation-test.md)

**Implementation plan:** [word-preservation plan](../plans/2026-07-21-default-layout-word-preservation.md)

## Adopted design

The test will use the existing pinned OCR predictor and `two_column_page.png`. It will snapshot OCR words before reorganization, enable the real default layout path, and compare `Counter` values after reorganization. Counters preserve duplicates and avoid false success from set equality.

## Acceptance criteria

- The test exercises the real default layout model.
- It compares normalized word text as a multiset, including duplicates.
- `validate_word_preservation` remains enabled.
- The test carries the existing slow marker and deterministic model revision.
