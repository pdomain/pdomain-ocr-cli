---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

# Update Check Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose concise update-check failures when general debug mode is enabled.

**Architecture:** A small diagnostic helper checks `PD_OCR_DEBUG` and writes sanitized exception summaries. The existing outer exception boundary calls it and still returns normally.

**Tech Stack:** Python, pytest

**Spec:** [update-check diagnostics design](../specs/2026-07-21-update-check-diagnostics-design.md)

---

## Task 1: Add opt-in diagnostics

**Files:**

- Modify: `pdomain_ocr_cli/_update_check.py`
- Modify: `tests/test_update_check_network.py`

- [ ] **Step 1: Add failing debug tests**

```python
def test_debug_reports_network_failure(monkeypatch, capsys):
    monkeypatch.setenv("PD_OCR_DEBUG", "1")
    monkeypatch.setattr(_update_check, "urlopen", _fake_urlopen_raises(TimeoutError("slow")))
    _update_check.check_for_update()
    assert capsys.readouterr().err == "update check failed: TimeoutError: slow\n"
```

Add the inverse test with `PD_OCR_DEBUG` unset and expected stderr `""`.

- [ ] **Step 2: Confirm the debug test fails**

Run: `uv run pytest -n auto tests/test_update_check_network.py -k 'debug_reports or silent_without_debug' -v`
Expected: FAIL because caught errors are always silent.

- [ ] **Step 3: Implement the diagnostic helper**

```python
def _report_failure(exc: Exception) -> None:
    if _env_truthy("PD_OCR_DEBUG"):
        print(f"update check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
```

Call it from the existing catch-all boundary and preserve the normal return.

- [ ] **Step 4: Verify and commit**

Run: `make test-k K='update_check' AI=1 && make ci AI=1`
Expected: both commands print `✅`.

```bash
git add pdomain_ocr_cli/_update_check.py tests/test_update_check_network.py
git commit -m "feat: add opt-in update check diagnostics"
```
