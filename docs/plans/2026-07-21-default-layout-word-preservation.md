---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

# Default Layout Word Preservation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an integration tripwire proving default layout preserves duplicate OCR words.

**Architecture:** The integration helper captures the page before layout and the final page after layout. A shared extractor converts each page to a `Counter[str]` for exact comparison.

**Tech Stack:** Python collections.Counter, pytest, DocTR, pdomain-book-tools

**Spec:** [word preservation design](../specs/2026-07-21-default-layout-word-preservation-design.md)

---

### Task 1: Add the slow multiset regression

**Files:**
- Modify: `tests/test_pipeline_integration.py`

- [ ] **Step 1: Add a page-word helper**

```python
def _word_multiset(page) -> Counter[str]:
    return Counter(
        word.value
        for block in page.blocks
        for line in block.lines
        for word in line.words
    )
```

- [ ] **Step 2: Add the integration test**

```python
@pytest.mark.slow
def test_default_layout_preserves_two_column_word_multiset(monkeypatch, shared_predictor, tmp_path):
    before, after = _invoke_default_layout_with_snapshots(
        monkeypatch,
        shared_predictor,
        Path("tests/fixtures/two_column_page.png"),
        tmp_path,
    )
    assert _word_multiset(after) == _word_multiset(before)
```

The helper must pass `validate_word_preservation=True` and the existing `PINNED_MODEL_REVISION`.

- [ ] **Step 3: Run the slow test**

Run: `uv run pytest -n auto tests/test_pipeline_integration.py::test_default_layout_preserves_two_column_word_multiset -v -m slow`
Expected: PASS; if it fails, stop and file the observed dropped/duplicated multiset as an implementation defect.

- [ ] **Step 4: Run all gates and commit**

Run: `make test-slow AI=1 && make ci AI=1`
Expected: both commands print `✅`.

```bash
git add tests/test_pipeline_integration.py
git commit -m "test: prove default layout preserves OCR words"
```
