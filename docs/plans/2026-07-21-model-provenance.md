---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

# Model Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pin the default OCR model and guard the upstream safe-loading contract.

**Architecture:** Argument parsing owns the immutable default. Model-security warnings continue to classify user overrides, while a test-only source inspection guards the upstream `weights_only=True` contract.

**Tech Stack:** Python, argparse, pytest, pdomain-book-tools, uv

**Spec:** [model provenance design](../specs/2026-07-21-model-provenance-design.md)

---

### Task 1: Pin the default revision

**Files:**
- Modify: `pdomain_ocr_cli/ocr_to_txt.py`
- Modify: `tests/test_parse_args.py`
- Modify: `tests/test_model_security.py`

- [ ] **Step 1: Add failing default and warning tests**

```python
def test_default_model_revision_is_immutable(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "page.png"])
    assert parse_args().model_version == "v0.7"

def test_default_revision_has_no_mutable_warning() -> None:
    warnings = model_security_warnings(_args(model_version="v0.7"))
    assert not any("mutable latest OCR model revision" in item for item in warnings)
```

- [ ] **Step 2: Confirm the tests fail**

Run: `make test-k K='default_model_revision_is_immutable or default_revision_has_no_mutable_warning' AI=1`
Expected: FAIL because the parser still defaults to `latest` or `None`.

- [ ] **Step 3: Set one shared immutable default**

Add `DEFAULT_MODEL_REVISION = "v0.7"` near the parser constants in `ocr_to_txt.py`. Use it as the `--model-version` default and make `_model_security.py` treat only `None` and `"latest"` as mutable.

- [ ] **Step 4: Run focused tests**

Run: `make test-k K='parse_args or model_security' AI=1`
Expected: PASS.

- [ ] **Step 5: Commit the default pin**

```bash
git add pdomain_ocr_cli/ocr_to_txt.py pdomain_ocr_cli/_model_security.py tests/test_parse_args.py tests/test_model_security.py
git commit -m "fix: pin default OCR model revision"
```

### Task 2: Guard safe upstream loading

**Files:**
- Create: `tests/test_upstream_safe_load.py`

- [ ] **Step 1: Add the contract test**

```python
import inspect

from pdomain_book_tools import doctr


def test_upstream_torch_load_is_weights_only() -> None:
    source = inspect.getsource(doctr)
    assert "weights_only=True" in source
```

Resolve the exact upstream module containing `torch.load` with `rg -n 'torch\.load' ../pdomain-book-tools/pdomain_book_tools` and import that module instead of `doctr` if needed.

- [ ] **Step 2: Verify the contract**

Run: `uv run pytest -n auto tests/test_upstream_safe_load.py -v`
Expected: PASS against `pdomain-book-tools >=0.18.0`.

- [ ] **Step 3: Run all gates**

Run: `make test-slow AI=1 && make ci AI=1`
Expected: both commands print `✅`.

- [ ] **Step 4: Commit the tripwire**

```bash
git add tests/test_upstream_safe_load.py
git commit -m "test: guard upstream safe model loading"
```
