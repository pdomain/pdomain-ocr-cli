---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

# Output Transaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Roll back new and overwritten page artifacts when any promotion fails.

**Architecture:** `PageOutputTransaction` stages content, backs up destinations, and promotes files. A reverse-order rollback restores the exact pre-call filesystem state.

**Tech Stack:** Python pathlib/os, pytest

**Spec:** [output transaction design](../specs/2026-07-21-output-transaction-design.md)

---

### Task 1: Specify rollback behavior with tests

**Files:**
- Modify: `tests/test_artifacts.py`

- [ ] **Step 1: Add new-artifact rollback coverage**

```python
def test_page_output_transaction_removes_new_sidecars_when_text_promotion_fails(tmp_path, monkeypatch):
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    monkeypatch.setattr(transaction, "_promote", fail_for(txt_path))
    with pytest.raises(OSError, match="forced"):
        transaction.commit()
    assert not json_path.exists()
    assert not txt_path.exists()
```

- [ ] **Step 2: Add overwrite restoration coverage**

Create both destinations with `old-json` and `old-text`, trigger the same failure, and assert those exact bytes remain.

- [ ] **Step 3: Confirm both tests fail**

Run: `uv run pytest -n auto tests/test_artifacts.py -k 'removes_new_sidecars or restores_overwritten' -v`
Expected: FAIL because promoted sidecars remain or old files are lost.

### Task 2: Implement backup and rollback

**Files:**
- Modify: `pdomain_ocr_cli/_artifacts.py`
- Modify: `tests/test_artifacts.py`

- [ ] **Step 1: Add transaction state**

Track `staged: list[tuple[Path, Path]]`, `backups: list[tuple[Path, Path]]`, and `promoted: list[Path]`. Create backup names with the existing unique sibling-temp helper.

- [ ] **Step 2: Implement reverse rollback**

```python
def _rollback(self) -> list[OSError]:
    errors: list[OSError] = []
    for destination in reversed(self._promoted):
        try:
            destination.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(exc)
    for destination, backup in reversed(self._backups):
        try:
            os.replace(backup, destination)
        except OSError as exc:
            errors.append(exc)
    return errors
```

- [ ] **Step 3: Wire rollback into `commit`**

On promotion failure, call `_rollback()`. Re-raise the original exception when rollback succeeds. Raise an `ExceptionGroup("artifact promotion and rollback failed", [original, *errors])` when rollback also fails.

- [ ] **Step 4: Run artifact tests**

Run: `make test-k K='artifacts or pipeline_atomic_write' AI=1`
Expected: PASS.

- [ ] **Step 5: Run all gates and commit**

Run: `make ci AI=1`
Expected: `✅`.

```bash
git add pdomain_ocr_cli/_artifacts.py tests/test_artifacts.py
git commit -m "fix: roll back failed page output transactions"
```
