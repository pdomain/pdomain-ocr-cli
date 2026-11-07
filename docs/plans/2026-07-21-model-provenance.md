---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: plan
---

# Model Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Pin the default OCR model and guard the upstream safe-loading contract.

## Architecture

Argument parsing owns the immutable default. Model-security warnings continue to classify user overrides, while a test-only source inspection guards the upstream `weights_only=True` contract.

## Tech Stack

Python, argparse, pytest, pdomain-book-tools, uv

## Global Constraints

Never silently drop OCR words. Keep reusable logic in `pdomain-book-tools`.
Run `make ci AI=1` before committing. Docs, code and tests change together.
GitHub runs no workflows for this repository, so every check here is local.

**Spec:** [model provenance design](../specs/2026-07-21-model-provenance-design.md)

---

## Status

Task 1, the `v0.7` default revision pin, shipped in `7af73fc` (v0.9.1); see
[cli-orchestration.md](../architecture/cli-orchestration.md#trust-and-network-boundaries).
Task 2 is open and not blocked: `pdomain-book-tools` 0.30.1 already loads
checkpoints with `weights_only=True`.

## Task 2: Guard safe upstream loading

**Files:**

- Create: `tests/test_upstream_safe_load.py`

- [ ] **Step 1: Add a behavioral contract test**

Do not search the module source for `weights_only=True`: that string also
appears in two docstrings, so the check would pass after the real call changed.
Test the behavior instead:

```python
import pickle
from pathlib import Path

import pytest
import torch

from pdomain_book_tools.ocr.doctr_support import get_finetuned_torch_doctr_predictor


class _Marker:
    """Any non-tensor class; weights_only=True refuses to unpickle it."""


def test_upstream_loader_refuses_pickled_objects(tmp_path: Path) -> None:
    det = tmp_path / "det.pt"
    reco = tmp_path / "reco.pt"
    torch.save(_Marker(), det)
    torch.save({}, reco)
    with pytest.raises(pickle.UnpicklingError):
        get_finetuned_torch_doctr_predictor(det, reco)
```

With `weights_only=True`, `torch.load` raises `UnpicklingError`. If upstream
drops it, the load succeeds and `_validate_state_dict` raises `ValueError`
instead, so the test fails. Confirm the call signature against the pinned
release before writing the test. Also add a test that the CLI calls
`get_finetuned_torch_doctr_predictor` without its `torch_load` override, which
would bypass the safe loader.

- [ ] **Step 2: Verify the contract**

Run: `uv run pytest -n auto tests/test_upstream_safe_load.py -v`
Expected: PASS against `pdomain-book-tools==0.30.1`.

- [ ] **Step 3: Run all gates**

Run: `make test-slow AI=1 && make ci AI=1`
Expected: both commands print `✅`.

- [ ] **Step 4: Commit the tripwire**

```bash
git add tests/test_upstream_safe_load.py
git commit -m "test: guard upstream safe model loading"
```
