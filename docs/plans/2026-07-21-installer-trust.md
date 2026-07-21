---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

# Installer Trust Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent dependency confusion and reject unverified release wheels.

**Architecture:** Shell-specific helpers parse the GitHub asset digest and hash the downloaded file. Both uv invocations use the pdomain index first and PyPI only as a fallback.

**Tech Stack:** POSIX shell, PowerShell, uv, GitHub Releases API, pytest

**Spec:** [installer trust design](../specs/2026-07-21-installer-trust-design.md)

---

### Task 1: Lock index resolution

**Files:**
- Modify: `install.sh`
- Modify: `install.ps1`
- Modify: `tests/test_install_sh.py`
- Modify: `tests/test_install_ps1.py`

- [ ] **Step 1: Add failing static contract tests**

```python
def test_install_sh_uses_first_index_strategy() -> None:
    script = Path("install.sh").read_text()
    assert 'UV_INDEX_STRATEGY="first-index"' in script
    assert '--index-strategy "$UV_INDEX_STRATEGY"' in script

def test_install_ps1_uses_first_index_strategy() -> None:
    script = Path("install.ps1").read_text()
    assert '"--index-strategy", "first-index"' in script
```

- [ ] **Step 2: Confirm tests fail**

Run: `make test-k K='first_index_strategy' AI=1`
Expected: FAIL because both scripts use only `--extra-index-url`.

- [ ] **Step 3: Add the strategy to both uv commands**

Keep the pdomain URL before user-provided extra indexes. Pass `--index-strategy first-index` in both scripts.

- [ ] **Step 4: Run installer tests and commit**

Run: `make test-k K='install_sh or install_ps1' AI=1`
Expected: PASS.

```bash
git add install.sh install.ps1 tests/test_install_sh.py tests/test_install_ps1.py
git commit -m "fix: enforce first-index installer resolution"
```

### Task 2: Verify GitHub asset digests

**Files:**
- Modify: `install.sh`
- Modify: `install.ps1`
- Modify: `tests/test_install_sh.py`
- Modify: `tests/test_install_ps1.py`

- [ ] **Step 1: Add missing and mismatch tests**

Extend the existing mocked-release fixtures with `"digest": "sha256:<known hash>"`. Add cases with no `digest`, `sha256:not-hex`, and a valid digest for different bytes. Each case must assert a non-zero exit and that mocked `uv tool install` was not called.

- [ ] **Step 2: Confirm the tests fail**

Run: `make test-k K='digest or checksum' AI=1`
Expected: FAIL because neither installer checks the asset digest.

- [ ] **Step 3: Implement POSIX verification**

Extract the selected asset digest with the existing JSON parser. Validate it with `case "$DIGEST" in sha256:[0-9a-f]... )`. Calculate with `sha256sum` or `shasum -a 256`, and exit before installation unless values match.

- [ ] **Step 4: Implement PowerShell verification**

Read `$asset.digest`, validate it with `'^sha256:[0-9a-f]{64}$'`, calculate `(Get-FileHash -Algorithm SHA256 $WheelFile).Hash.ToLowerInvariant()`, and compare it to `$asset.digest.Substring(7)`.

- [ ] **Step 5: Run all installer and CI gates**

Run: `make test-k K='install_sh or install_ps1' AI=1 && make ci AI=1`
Expected: both commands print `✅`.

- [ ] **Step 6: Commit digest verification**

```bash
git add install.sh install.ps1 tests/test_install_sh.py tests/test_install_ps1.py
git commit -m "fix: verify installer wheel digests"
```
