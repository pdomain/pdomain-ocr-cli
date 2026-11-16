---
Status: active
Owner: CT
Created: 2026-05-31
Last verified: 2026-11-15
Kind: decision
---

# Type Suppressions

The basedpyright baseline is empty. This decision records the rationale for the
three inline `pyright: ignore` comments and one notable structural `noqa`; the
complete current inventory belongs in `docs/conventions/lint-deviations.md`.

## Context

The basedpyright baseline is empty, but intentional inline type and lint
suppressions remain. `CONVENTIONS.md` requires every suppression to carry an
inline rationale and appear in the consolidated catalogue at
`docs/conventions/lint-deviations.md`.

## Decision

Fix the underlying issue when possible. Keep a suppression only when the
deviation is correct, explain why it is safe inline, and catalogue it in
`docs/conventions/lint-deviations.md`.

## Consequences

Each suppression remains visible at its source and auditable in one central
catalogue. New suppressions require both an inline rationale and a catalogue
entry.

## Supersedes / Superseded-by

No supersession relationship is recorded.

## `pyright: ignore` suppressions

| File | Line | Rule | Rationale |
|------|------|------|-----------|
| `pdomain_ocr_cli/ocr_to_txt.py` | 429 | `reportAttributeAccessIssue` | `module` is the result of `importlib.import_module("pdomain_ops.gpu.device")` cast to `object`. Basedpyright cannot resolve attributes on `object`; the `cast` on the same line completes the type for downstream callers. |
| `pdomain_ocr_cli/ocr_to_txt.py` | 452 | `reportAttributeAccessIssue` | Same pattern — `importlib.import_module("pdomain_ops.gpu.doctr_batch")` cast to `object`. The outer `cast` resolves the callable type; the suppress covers the intermediate attribute access. |

## `noqa` suppressions with structural rationale

Most `noqa` suppressions have an inline comment explaining the context. One
suppression needs extra explanation:

| File | Line | Rule | Rationale |
|------|------|------|-----------|
| `pdomain_ocr_cli/ocr_to_txt.py` | 1069 | `TRY301` | `raise ValueError(...)` is inside a `try` block. TRY301 suggests abstracting the raise to an inner function, but here it is intentional: the outer `except Exception` (line 1075) unifies all per-image decode failures — both the explicit ValueError and any unexpected cv2 error — through a single error-reporting path. Abstracting would require duplicating that handler. |

Other inline and configured suppressions are outside this decision's historical
inventory. `docs/conventions/lint-deviations.md` is the authoritative catalogue.

## Source-location update, 2026-11-13

The historical table above remains unchanged. The live inventory in
[`lint-deviations.md`](../conventions/lint-deviations.md) now records the
dynamic-module accesses at `ocr_to_txt.py` lines 436 and 459 and the `TRY301`
site at line 1084. Its shared per-image decode handler is at line 1094.
The startup probe no longer imports CuPy. `_startup_notices.py` checks
`torch.cuda` and treats a broken PyTorch install as "do not nudge." Source
inspection confirmed the same structural rationale; this update does not
change the suppression policy or resolve the owner's consolidation question.
