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

- [ ] **Step 1: Add the contract test**

```python
import inspect

from pdomain_book_tools.ocr import doctr_support


def test_upstream_torch_load_is_weights_only() -> None:
    source = inspect.getsource(doctr_support)
    assert "weights_only=True" in source
```

In 0.30.1 the loader is `functools.partial(torch.load, weights_only=True)` in `pdomain_book_tools/ocr/doctr_support.py`. If upstream moves it, find it with `rg -n 'torch\.load' ../pdomain-book-tools/pdomain_book_tools`.

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
