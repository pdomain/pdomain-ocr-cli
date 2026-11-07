---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: plan
---

# Dependency Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Publish bounded dependencies and make build and hook inputs immutable.

## Architecture

`pyproject.toml` remains the package metadata authority. Static tests enforce bounds and exact pins. Hook revisions are refreshed locally with `pre-commit autoupdate --freeze`.

## Tech Stack

Python packaging, uv, Hatchling, pre-commit, pytest

## Global Constraints

Never silently drop OCR words. Keep reusable logic in `pdomain-book-tools`.
Run `make ci AI=1` before committing. Docs, code and tests change together.
GitHub runs no workflows for this repository, so every check here is local.

**Spec:** [dependency provenance design](../specs/2026-07-21-dependency-provenance-design.md)

---

## Status

Task 1, package bounds and exact build-backend pins, shipped in `7b0f4f7`
(v0.9.1); see [cli-orchestration.md](../architecture/cli-orchestration.md#dependency-bounds).
Task 2 waits on the owner's choice between tag and SHA revisions (former GH #45).

## Task 2: Freeze pre-commit revisions

**Files:**

- Modify: `.pre-commit-config.yaml`
- Modify: `Makefile` (the `update-hooks` target)
- Create: `tests/test_pre_commit_pins.py`

- [ ] **Step 1: Add a failing SHA contract test**

```python
def test_remote_pre_commit_revisions_are_full_shas():
    config = yaml.safe_load(Path(".pre-commit-config.yaml").read_text())
    revisions = [repo["rev"] for repo in config["repos"] if repo["repo"] != "local"]
    assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in revisions)
```

- [ ] **Step 2: Confirm the test fails**

Run: `uv run pytest -n auto -k 'pre_commit_revisions_are_full_shas'`
Expected: FAIL because revisions are tags.

- [ ] **Step 3: Freeze hooks and refresh behavior**

Run `uv run pre-commit autoupdate --freeze`. `make update-hooks` currently runs the `pre-commit-update` hook on the manual stage, which writes tags. Change it so later refreshes keep SHA revisions, for example by running `uv run pre-commit autoupdate --freeze` instead.

- [ ] **Step 4: Verify and commit hook pins**

Run: `uv run pytest -n auto -k 'pre_commit_revisions_are_full_shas' && make ci AI=1`
Expected: both commands print `✅`.

```bash
git add .pre-commit-config.yaml Makefile tests/test_pre_commit_pins.py
git commit -m "build: freeze pre-commit hook revisions"
```
