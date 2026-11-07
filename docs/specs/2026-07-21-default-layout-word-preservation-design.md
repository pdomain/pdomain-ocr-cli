---
Status: implemented
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Prove default layout preserves every OCR word

A slow integration test will compare word multisets before and after default layout reorganization.

## Agent Index

- **Kind:** spec
- **Status:** implemented
- **Read when:** changing default layout or word-preservation coverage
- **Search terms:** word multiset, default layout, two column, former GH 41
- **Relates to:** shipped in commit `c325c13` (v0.9.0); current behavior is [test-suite.md](../architecture/test-suite.md)

**Implementation plan:** retired after it shipped; see the 2026-11-07 tombstone in [decisions](../context/decisions.md).

## Adopted design

The test will use the existing pinned OCR predictor and `two_column_page.png`. It will snapshot OCR words before reorganization, enable the real default layout path, and compare `Counter` values after reorganization. Counters preserve duplicates and avoid false success from set equality.

## Acceptance criteria

- The test exercises the real default layout model.
- It compares normalized word text as a multiset, including duplicates.
- `validate_word_preservation` remains enabled.
- The test carries the existing slow marker and deterministic model revision.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** Implemented with deviations. Three acceptance criteria are not met as written.

- High: criterion 1, the real default layout model, is not met. The test replaces OCR, the runtime and the layout detector with fakes; it does call the real `Page.reorganize_page`. Documented in `test-suite.md`.
- High: criterion 3, `validate_word_preservation` enabled, is not met. The test does not pass `--validate-reorg`, and the shared fixture mocks the validator. Follow-up.
- High: criterion 4, a slow pinned-model test, is not met. The test is fast and mocked. Documented in `test-suite.md`; a slow real-model case is a follow-up.
- Medium: the fixture is one synthetic figure page, not `two_column_page.png`, and the oracle is a raw `Counter` of word text. It catches plain drops, not altered or moved words, overlaps, captions or columns. Follow-up.
