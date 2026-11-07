---
Status: active
Owner: CT
Created: 2026-07-19
Last verified: 2026-11-07
Kind: issue
Level: I1
---

# Default OCR model pin and safe-load guard

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-11-07
- **Resolution:** Open
- **Severity:** Medium. Safe loading works today, but nothing here detects an
  upstream regression.
- **Affected version:** pdomain-ocr-cli v0.9.1 (`7af73fc`) with
  `pdomain-book-tools==0.30.1`
- **Read when:** working on former GH #15, model provenance, or checkpoint
  loading safety
- **Search terms:** former GH #15, 2026-07-19-gh-15-model-revision-pin-and-safe-load,
  weights_only, torch.load, model revision pin
- **Relates to:** [roadmap](../roadmap.md),
  [model provenance plan](../plans/2026-07-21-model-provenance.md)

## Summary

One test remains. The issue had two parts:

1. **Pin the default model revision.** Shipped in `7af73fc` (v0.9.1). The
   default `--model-version` is `v0.7`, and only an unset revision or `latest`
   counts as mutable.
2. **Load checkpoints safely.** `pdomain-book-tools` 0.30.1 already does this:
   it calls `torch.load(..., weights_only=True)` and rejects checkpoints that
   are not plain state dicts of tensors. What this repository lacks is a test
   that fails if a future upstream version drops that setting.

This report was written on 2026-07-19, when both parts were open and part 2
was thought to be blocked upstream. It was rewritten on 2026-11-07.

Provenance: former GH #15.

## Impact

If `pdomain-book-tools` ever loads checkpoints without `weights_only=True`, a
malicious checkpoint could run code, and this repository's tests would not
notice. Today's installed version is safe.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli @ 7af73fc (v0.9.1)
pdomain-book-tools: 0.30.1 (pinned exactly)
python-doctr: 1.1.0
```

## Evidence

- `pdomain_ocr_cli/ocr_to_txt.py`: `DEFAULT_MODEL_REVISION` is `v0.7`.
  `tests/test_model_security.py::test_pinned_default_revision_has_no_mutable_warning`
  covers the pin.
- `pdomain_book_tools/ocr/doctr_support.py` in 0.30.1 builds its loader as
  `functools.partial(torch.load, weights_only=True)` and calls
  `_validate_state_dict` after each load.
- No test file in `tests/` references `weights_only`.

## Root-cause hypotheses

1. **Most likely:** the guard test was planned (Task 2 of the model provenance
   plan) but was not written when part 1 landed in v0.9.1.

## Defects to fix

1. Add `tests/test_upstream_safe_load.py`, which inspects
   `pdomain_book_tools.ocr.doctr_support` and fails unless its checkpoint
   loader passes `weights_only=True`.

## Next steps

1. Write the test from the model provenance plan, Task 2, against
   `pdomain_book_tools.ocr.doctr_support`.
2. Keep the custom-model warnings from former GH #16.

## What is NOT broken (to scope the fix)

- The default model pin (`v0.7`).
- Upstream safe loading in `pdomain-book-tools` 0.30.1.
- The custom-model and mutable-revision warnings (former GH #16).

## Resolution

_Open._ When the guard test lands, retire this report through `doc-retirer`
and add a tombstone to `docs/context/decisions.md`.
