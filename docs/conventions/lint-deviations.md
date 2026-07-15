---
Status: active
Owner: CT
Created: 2026-05-31
Last verified: 2026-07-13
Kind: process
---

# Lint-rule Deviations — pdomain-ocr-cli

This file catalogs the standing suppressions and per-file rule overrides in
this repo. Each entry records the rule, tool, affected file(s), and
justification. Update this file whenever a new suppression is added.

This catalogue covers the project-wide `[tool.ruff.lint]` `ignore` list and
`per-file-ignores`, plus every inline `# noqa`, `# pyright: ignore`, and
`# type: ignore` comment in the source tree.

Reference implementation: `pdomain-book-tools/docs/conventions/lint-deviations.md`.

---

## Project-wide ruff `ignore`

These rules are disabled repo-wide in `pyproject.toml` → `[tool.ruff.lint]`
`ignore`. Each carries an inline rationale at the suppression point as well.

### 1. `E501` — line-too-long

Many docstrings, error messages, and URLs are long. Enforcing 88/100-char
wrapping everywhere adds noise without improving readability. The ruff
formatter still wraps code; this only relaxes the lint check.

### 2. `D203` / `D212` — pydocstyle pair conflicts

`D203` (1-blank-before-class-docstring) conflicts with `D211`
(no-blank-before-class-docstring). `D212` (multi-line-summary-first-line)
conflicts with `D213` (multi-line-summary-second-line). One of each pair
must be disabled; this repo keeps `D211` + `D213`.

### 3. `D100` / `D104` / `D107` — missing docstrings

Public modules, packages, and `__init__` methods may lack docstrings.
This work is an incremental backlog rather than a hard gate.

### 4. `D105` — missing docstring in magic method

Magic methods are self-documenting; add docstrings incrementally.

### 5. `D205` — 1-blank-line-between-summary-and-description

Too noisy for the docstring style used here.

### 6. `PLR0913` — too-many-arguments

CLI entry points and pipeline functions legitimately take many params
(model paths, device, layout flags, rotation options, etc.).

### 7. `PLR2004` — magic-value-comparison

Common in CLI argument defaults and threshold comparisons.

### 8. `PLR0911` / `PLR0912` / `PLR0915` — function complexity

`main()` orchestrates the full OCR pipeline and legitimately has high
branch / return / statement counts. Splitting it further would scatter
sequential pipeline logic without improving clarity.

### 9. `PLC0415` — import-not-at-top-level

Deferred imports are intentional. They break circular deps and avoid loading
optional-heavy modules (torch, cv2, cupy) until needed.
Several are also monkeypatch seams for tests.

### 10. `TRY003` — long-message-outside-exception-class

Too noisy for a CLI that uses f-string error messages everywhere.

### 11. `COM812` — missing-trailing-comma

Conflicts with the ruff formatter's auto-style; the formatter owns commas.

### 12. `ANN401` — dynamically-typed-expressions (`Any`)

Some helpers legitimately accept/return `Any` — monkeypatch seams and
word-object helpers that operate on heterogeneous pdomain-book-tools objects.

---

## Per-file ruff ignores

From `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`.

### 13. `tests/**/*.py`

Ignored: `S101`, `S105`, `S106`, `S311`, `T201`, `ANN`, `D`, `PLR2004`,
`PT011`, `S108`, `PLR0133`, `PLW2901`, `PERF401`, `S603`, `S607`.

`assert` is the test idiom (`S101`). Hardcoded passwords and random values are
test fixtures (`S105`/`S106`/`S311`). `print()` is fine in tests (`T201`), and
tests need no annotations or docstrings (`ANN`/`D`). Magic numbers are common
(`PLR2004`). `pytest.raises(match=)` is not required on every test (`PT011`),
and `/tmp` paths are fine (`S108`). Trivial self-comparisons can be intentional
(`PLR0133`). Loop-var reassignment is an accepted test pattern (`PLW2901`),
and list-building loops in tests are fine (`PERF401`). Test subprocesses use
fixed fixture commands and intentionally resolve tools from `PATH`
(`S603`/`S607`).

### 14. `scripts/*.py`

Ignored: `T201`, `D`, `S607`.

`print()` is the output mechanism for scripts; no docstrings required;
`S607` partial executable path is idiomatic when invoking system tools
(`uv`, `git`, etc.) that are always on `PATH`.

### 15. `**/__init__.py`

Ignored: `D104`, `F401`, `TC`.

Re-export modules need no docstrings. `F401` unused-import is the public
API-surface pattern. `TC` type-checking import moves do not apply.

### 16. `**/_*.py`

Ignored: `D`.

Private modules follow internal convention and need no docstrings.

---

## Inline `# noqa` suppressions

### 17. `T201` — print-found (ruff)

**Files:** `pdomain_ocr_cli/ocr_to_txt.py` (37 occurrences), `_batch_plan.py`
(3), `_hf_models.py` (2), `_pipeline.py` (1), `_startup_notices.py` (1), and
`_update_check.py` (1).

**Suppression form:** `# noqa: T201  # CLI output` inline.

**Justification.** `pdomain-ocr-cli` is a user-facing CLI. `print()` to stdout
and `print(..., file=sys.stderr)` are the intended output mechanism.
`T201` is relaxed repo-wide for `tests/**` and `scripts/**`, but library
modules under `pdomain_ocr_cli/` keep the rule on. Per-call suppressions ensure
that review still flags any *accidental* debug `print`.

### 18. `BLE001` — blind-except (ruff)

**Files:** `pdomain_ocr_cli/_startup_notices.py` (lines 58, 79, 100),
`_update_check.py` (line 155), and `ocr_to_txt.py` (lines 884, 898, 994,
1218).

**Suppression form:** `# noqa: BLE001` (sometimes `# noqa: BLE001 S110`)
inline, each with a trailing rationale.

**Justification.** Three distinct best-effort boundaries:

- The CuPy GPU probe and the GPU-install nudge helper must never crash
  `pdomain-ocr` — a broken native CuPy can even segfault, so the catch is
  intentionally `BaseException` and silent.
- The update-check is best-effort; any network/parse failure is safe to
  swallow.
- The per-image loop in `main()` catches all errors, reports them, and
  continues the batch rather than aborting on one bad scan.

### 19. `S110` — try-except-pass (ruff)

**Files:** `pdomain_ocr_cli/_startup_notices.py` (line 100) and
`_update_check.py` (line 155). Always paired with `BLE001`.

**Justification.** Both are best-effort boundaries. The startup notice helper
and update check must not interrupt OCR when an optional dependency,
subprocess, network request, or response parse fails.

### 20. `S310` — suspicious-url-open (ruff)

**Files:** `pdomain_ocr_cli/_update_check.py` (lines 109, 116).

**Suppression form:** `# noqa: S310` inline.

**Justification.** `urllib.request.Request` / `urlopen` are called only
with a hardcoded `https://` PyPI URL. There is no `file://` or
attacker-controlled scheme risk.

### 21. `S607` — start-process-with-partial-path (ruff)

**Files:** `pdomain_ocr_cli/_startup_notices.py` (line 67).

**Suppression form:** `# noqa: S607` inline.

**Justification.** `nvidia-smi` is invoked by bare name. When an NVIDIA
driver is present, the binary is always on `PATH`. Hardcoding an absolute
path would be wrong across distros. (`scripts/*.py` get this via
per-file-ignores; this one site is in a library module so it is suppressed
inline.)

### 22. `ERA001` — commented-out-code (ruff)

**Files:** `tests/test_update_check_bypass.py` (line 57).

**Suppression form:** `# noqa: ERA001` inline.

**Justification.** The commented expression is a reference copy of the
update-check gate kept beside the tests that exercise it.

### 23. `TRY301` — raise-within-try (ruff)

**Files:** `pdomain_ocr_cli/ocr_to_txt.py` (line 991).

**Suppression form:** `# noqa: TRY301` inline.

**Justification.** The explicit `ValueError` and unexpected OpenCV failures
share the outer per-image decode handler. Moving the raise to a helper would
split that single error-reporting path.

### 24. `S603` — subprocess-without-shell-equals-true (ruff)

**Files:** `scripts/update_github_actions.py` (line 48).

**Suppression form:** `# noqa: S603` inline.

**Justification.** The executable is resolved to an absolute path with
`shutil.which`, and the command is passed as an argument list without shell
parsing.

---

## Inline `# pyright: ignore` suppressions

### 25. `reportMissingImports` — basedpyright

**Files:** `pdomain_ocr_cli/_startup_notices.py` (line 53).

**Suppression form:** `# pyright: ignore[reportMissingImports]` inline on
the `import cupy` probe line.

**Justification.** `cupy` is an optional GPU dependency absent from CPU-only
installs. The guarded import probes whether the optional GPU stack is
available.

### 26. `reportAttributeAccessIssue` — basedpyright

**Files:** `pdomain_ocr_cli/ocr_to_txt.py` (lines 413 and 436).

**Suppression form:** `# pyright: ignore[reportAttributeAccessIssue]` inline.

**Justification.** Both modules are loaded dynamically with
`importlib.import_module`. As a result, basedpyright cannot resolve their attributes.
The surrounding casts establish the callable types used downstream.

### 27. `reportPrivateUsage` — basedpyright

**Files:** `tests/test_main_errors.py` (lines 31 and 79).

**Suppression form:** `# pyright: ignore[reportPrivateUsage]` inline.

**Justification.** These tests replace the private `_SinglePageDoc` seam to
verify atomic-write cleanup and error handling that cannot be induced through
the public CLI boundary.

---

## Notes

- No `# type: ignore[...]` suppressions remain. basedpyright-native
  `# pyright: ignore[...]` comments carry named rules and inline rationales.
- `failOnWarnings` is enabled for basedpyright.
- Every inline suppression carries a trailing rationale, and this file is the
  consolidated catalogue.
