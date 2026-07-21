---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

# Dependency Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish bounded dependencies and make build and hook inputs immutable.

**Architecture:** `pyproject.toml` remains the package metadata authority. Static tests enforce bounds and exact pins; the refresh workflow retains SHA-form hook revisions.

**Tech Stack:** Python packaging, uv, Hatchling, pre-commit, GitHub Actions, pytest

**Spec:** [dependency provenance design](../specs/2026-07-21-dependency-provenance-design.md)

---

### Task 1: Add package metadata contracts

**Files:**
- Create: `tests/test_dependency_metadata.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Add failing metadata tests**

```python
def test_direct_dependencies_have_upper_bounds():
    data = tomllib.loads(Path("pyproject.toml").read_text())
    requirements = data["project"]["dependencies"]
    requirements += data["project"]["optional-dependencies"].get("gpu", [])
    assert all("<" in requirement for requirement in requirements)

def test_build_backends_are_exactly_pinned():
    requires = tomllib.loads(Path("pyproject.toml").read_text())["build-system"]["requires"]
    assert all("==" in requirement for requirement in requires)
```

- [ ] **Step 2: Confirm the tests fail**

Run: `uv run pytest -n auto tests/test_dependency_metadata.py -v`
Expected: FAIL on unbounded dependencies and unpinned build backends.

- [ ] **Step 3: Apply compatibility caps and exact backend pins**

For each runtime/GPU requirement, preserve its floor and add `<next-major`. Read the current `hatchling` and `hatch-vcs` versions from `uv.lock` and pin those exact versions under `[build-system].requires`.

- [ ] **Step 4: Refresh and verify metadata**

Run: `uv lock && uv run pytest -n auto tests/test_dependency_metadata.py -v && make build AI=1`
Expected: lock succeeds, tests pass, and build prints `✅`.

- [ ] **Step 5: Commit package bounds**

```bash
git add pyproject.toml uv.lock tests/test_dependency_metadata.py
git commit -m "build: bound runtime and build dependencies"
```

### Task 2: Freeze pre-commit revisions

**Files:**
- Modify: `.pre-commit-config.yaml`
- Modify: `.github/workflows/dep-refresh.yml`
- Modify: `tests/test_workflows_static.py`

- [ ] **Step 1: Add a failing SHA contract test**

```python
def test_remote_pre_commit_revisions_are_full_shas():
    config = yaml.safe_load(Path(".pre-commit-config.yaml").read_text())
    revisions = [repo["rev"] for repo in config["repos"] if repo["repo"] != "local"]
    assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in revisions)
```

- [ ] **Step 2: Confirm the test fails**

Run: `make test-k K='pre_commit_revisions_are_full_shas' AI=1`
Expected: FAIL because revisions are tags.

- [ ] **Step 3: Freeze hooks and refresh behavior**

Run `uv run pre-commit autoupdate --freeze`. Change the dependency-refresh workflow's hook update command to the same `uv run pre-commit autoupdate --freeze` command.

- [ ] **Step 4: Verify and commit hook pins**

Run: `make test-k K='workflows_static' AI=1 && make ci AI=1`
Expected: both commands print `✅`.

```bash
git add .pre-commit-config.yaml .github/workflows/dep-refresh.yml tests/test_workflows_static.py
git commit -m "build: freeze pre-commit hook revisions"
```
