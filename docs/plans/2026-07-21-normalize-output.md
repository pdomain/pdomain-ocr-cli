---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: plan
---

# Normalize Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Add a default-off output-normalization mode backed only by the stable shared API.

## Architecture

The plan first verifies the upstream contract. Argparse selects an enum-like mode, and the pipeline delegates `typographic` normalization to the library immediately before writing.

## Tech Stack

Python, argparse, pytest, pdomain-book-tools

## Global Constraints

Never silently drop OCR words. Keep reusable logic in `pdomain-book-tools`.
Run `make ci AI=1` before committing. Docs, code and tests change together.
GitHub runs no workflows for this repository, so every check here is local.

**Spec:** [normalize output design](../specs/2026-07-21-normalize-output-design.md)

---

## Status

Blocked. On 2026-11-07, `pdomain-book-tools` 0.30.1 had no
`text_normalize.py` and no `normalize_text`, so Task 1's gate fails and Task 2
must not start.

## Task 1: Verify the upstream gate

**Files:**

- Inspect: `../pdomain-book-tools/pdomain_book_tools/text_normalize.py`
- Inspect: `pyproject.toml`

- [ ] **Step 1: Confirm the shared symbol exists**

Run: `rg -n '^def normalize_text\(' ../pdomain-book-tools/pdomain_book_tools/text_normalize.py`
Expected: one public `normalize_text` definition. Stop without changing CLI code if the command has no match.

- [ ] **Step 2: Confirm upstream contract tests pass**

Run from `../pdomain-book-tools`: `uv run pytest -n auto -k 'normalize_text and idempotent'`
Expected: `✅`. Stop if idempotence is not covered.

## Task 2: Add the mode with TDD

**Files:**

- Modify: `pdomain_ocr_cli/ocr_to_txt.py`
- Modify: `pdomain_ocr_cli/_pipeline.py`
- Modify: `tests/test_parse_args.py`
- Modify: `tests/test_text_normalize.py`
- Modify: `docs/usage/cli-usage.md`

- [ ] **Step 1: Add failing parser tests**

```python
def test_normalize_output_defaults_to_none(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "page.png"])
    assert parse_args().normalize_output == "none"


def test_normalize_output_accepts_typographic(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["pdomain-ocr", "--normalize-output", "typographic", "page.png"]
    )
    assert parse_args().normalize_output == "typographic"
```

- [ ] **Step 2: Confirm parser tests fail**

Run: `uv run pytest -n auto -k 'normalize_output'`
Expected: FAIL because the argument is absent.

- [ ] **Step 3: Add delegation tests**

Monkeypatch the imported upstream `normalize_text` to return `NORMALIZED`. Assert `apply_text_normalizations(..., normalize_output="typographic")` returns it and mode `none` preserves the input.

- [ ] **Step 4: Implement minimal delegation**

Add argparse choices `("none", "typographic")`, default `"none"`. In `apply_text_normalizations`, call upstream `normalize_text(text)` only for `typographic`, after existing transforms.

- [ ] **Step 5: Test composition and idempotence**

Add a string containing curly quotes, an em dash, and a mapped glyph. Assert both repeated application and reversed independent transform order produce the documented result.

- [ ] **Step 6: Document and verify**

Document both values and the default in `docs/usage/cli-usage.md`.

Run: `uv run pytest -n auto -k 'normalize or parse_args' && make ci AI=1`
Expected: both commands print `✅`.

- [ ] **Step 7: Commit**

```bash
git add pdomain_ocr_cli/ocr_to_txt.py pdomain_ocr_cli/_pipeline.py tests/test_parse_args.py tests/test_text_normalize.py docs/usage/cli-usage.md
git commit -m "feat: add shared output normalization mode"
```
