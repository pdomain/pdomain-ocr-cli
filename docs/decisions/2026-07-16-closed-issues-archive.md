---
Status: retired
Owner: CT
Created: 2026-07-16
Last verified: 2026-07-16
Kind: decision
---

<!-- markdownlint-disable -->
<!-- Verbatim archive of deleted GitHub issues; issue bodies keep their
     original headings and code fences, so lint rules are disabled. -->

# Closed-Issue Archive — 50 issues

## Agent Index

- **Kind:** decision
- **Status:** retired
- **Read when:** you need the text of a `pdomain-ocr-cli` GitHub issue that was deleted from the tracker on 2026-07-16.
- **Search terms:** closed issues, archive, tombstone, deleted issues, backlog, issue history, #NNN

## Context

The `pdomain-ocr-cli` GitHub tracker (`github.com/pdomain/pdomain-ocr-cli`) held
50 issues, all closed as `COMPLETED`. The backlog items among them had
already been carried forward into [`../roadmap.md`](../roadmap.md) on 2026-07-14,
each tagged with its originating `#NNN`, so the tracker no longer held any live
planning state — only historical text.

## Decision

Delete all 50 issues from GitHub and preserve their full text here
instead. This file records each issue's body and comments verbatim. Per this
repo's docs convention (see [`../README.md`](../README.md)), the archive is
committed and then removed from the working tree in a follow-up commit: **Git
history is the tombstone.** The working tree stays clean; the record is
permanent.

## Consequences

- The complete text survives in Git history even though the file is removed from
  the tree and the GitHub issues are gone. To read it, find the commit that
  added this file and run
  `git show <sha>:docs/decisions/2026-07-16-closed-issues-archive.md`.
- GitHub issue links (`#NNN` and `/issues/NNN` URLs) no longer resolve; the
  numbers are preserved here for cross-reference with `../roadmap.md`.
- Future per-repo issue archives should follow this same commit-then-remove
  pattern.

## Supersedes / Superseded-by

Supersedes nothing; superseded by nothing.

Issues archived (by number): #1, #2, #3, #5, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, #20, #21, #22, #23, #24, #25, #26, #27, #28, #29, #30, #31, #32, #33, #34, #35, #36, #37, #38, #39, #40, #41, #42, #43, #44, #45, #46, #47, #48, #49, #50, #51.

---

## #1 — Windows installer: nvidia-smi found but CUDA version detection fails, silently falls back to CPU

`author:` ConcaveTrillion · `created:` 2026-05-11 · `closed:` 2026-05-21 · `state:` CLOSED (COMPLETED)

`labels:` (none)

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/1

**Body**

## Problem

On Windows, the installer script detects `nvidia-smi` on PATH (GPU is present) but fails to parse the CUDA version from its output and silently falls back to a CPU-only install:

```
nvidia-smi found but could not detect CUDA version -- falling back to CPU.
```

The user ends up with a CPU build even though a CUDA-capable GPU is available, with no clear indication that anything went wrong or how to fix it.

## Likely cause

`nvidia-smi` on Windows prints the CUDA version in a slightly different format than what the script's regex/parse logic expects, or the command exits with a non-zero code in certain driver configurations. The script swallows the failure and continues silently.

## Proposed improvements

1. **Better detection**: test the actual `nvidia-smi` output format on Windows and fix the parse logic (e.g. `nvidia-smi --query-gpu=driver_version --format=csv,noheader` or parse `nvidia-smi -q` for the `CUDA Version` line).
2. **Louder fallback**: if detection fails, print a more actionable message, e.g.:
   ```
   Warning: GPU detected but CUDA version could not be determined.
   Installing CPU build. To install the GPU build manually, re-run with CUDA_VERSION=<your version>.
   ```
3. **Manual override**: accept a `$env:CUDA_VERSION` environment variable so users can bypass detection:
   ```powershell
   $env:CUDA_VERSION = "12.4"
   irm https://raw.githubusercontent.com/ConcaveTrillion/pd-ocr-cli/main/install.ps1 | iex
   ```

## Repro

- Windows machine with an NVIDIA GPU and valid CUDA drivers installed
- `nvidia-smi` present on PATH
- Run: `irm https://raw.githubusercontent.com/ConcaveTrillion/pd-ocr-cli/main/install.ps1 | iex`
- Observe: "nvidia-smi found but could not detect CUDA version -- falling back to CPU"

---

## #2 — Installer: pin to Python 3.13 to avoid source-build failures on pre-release Python

`author:` ConcaveTrillion · `created:` 2026-05-11 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` (none)

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/2

**Body**

## Problem

`uv` currently selects the newest available Python when none is specified — on Windows this resolves to Python 3.14 (currently pre-release/alpha). Several dependencies (notably `regex`, pulled in via `pd-book-tools`) do not yet ship pre-built wheels for 3.14, so uv falls back to a source build. On Windows that fails without MSVC Build Tools:

```
error: Microsoft Visual C++ 14.0 or greater is required.
```

## Fix

Add `--python 3.13` to both `uv tool install` calls in `install.ps1`. Python 3.13 is the current stable release and has pre-built wheels for all our dependencies on Windows:

```powershell
uv tool install --python 3.13 --reinstall $InstallRef --extra-index-url $ExtraIndex
# and
uv tool install --python 3.13 --reinstall $InstallRef
```

Same fix should be applied to `install.sh` if it also lacks a `--python` pin.

## Notes

- When 3.14 goes stable and wheels catch up, the pin can be bumped.
- Longer-term, `requires-python = ">=3.10,<3.14"` in `pyproject.toml` would prevent uv from selecting a pre-release interpreter at all, but the installer pin is the immediate fix.

---

## #3 — Tighten requires-python upper bound to <3.14 until regex ships stable wheels

`author:` ConcaveTrillion · `created:` 2026-05-11 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` (none)

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/3

**Body**

## Problem

`requires-python = ">=3.10,<4.0"` allows uv to select Python 3.14 (currently pre-release/alpha). Transitive dependency `regex` (via `pd-book-tools`) does not yet ship pre-built wheels for 3.14, so uv falls back to a source build. On Windows that fails without MSVC Build Tools.

## Fix

Change to `requires-python = ">=3.10,<3.14"`. Revert to `<4.0` once Python 3.14 is stable and `regex` publishes matching wheels.

Tracked upstream: https://github.com/ConcaveTrillion/pd-book-tools/issues/23

---

## #5 — Spec: Strict-linting rollout — pd-ocr-cli

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:spec, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/5

**Body**

Spec: docs/specs/2026-05-17-superpowers-gh-workflow-integration-design.md
Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md

Mirror pd-book-tools canonical strict-lint pattern in pd-ocr-cli.

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  All sub-tasks (#6–#13) closed — complete strict-linting stack is already implemented.

---

## #6 — Add canonical `.editorconfig` (TRIVIAL)

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:feature, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/6

**Body**

Approach: (see plan)

Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md#add-canonical-editorconfig-trivial
Tracks: #5

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  Already implemented: .editorconfig, .gitlint, pre-commit, basedpyright recommended mode, full canonical ruff select (ANN/S/C4/PERF/TC/TID/PT/RET/PL/D/BLE/TRY/LOG/G), filterwarnings=error, and no standalone isort/pylint — all present in pyproject.toml.

---

## #7 — Migrate pyright → basedpyright (standard mode) (MODERATE)

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:feature, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/7

**Body**

Approach: (see plan)

Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md#migrate-pyright-basedpyright-standard-mode-moderat
Tracks: #5

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  Already implemented: .editorconfig, .gitlint, pre-commit, basedpyright recommended mode, full canonical ruff select (ANN/S/C4/PERF/TC/TID/PT/RET/PL/D/BLE/TRY/LOG/G), filterwarnings=error, and no standalone isort/pylint — all present in pyproject.toml.

---

## #8 — Remove isort + pylint dev deps — **NOOP** (neither present)

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:feature, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/8

**Body**

Approach: (see plan)

Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md#remove-isort-pylint-dev-deps-noop-neither-present
Tracks: #5

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  Already implemented: .editorconfig, .gitlint, pre-commit, basedpyright recommended mode, full canonical ruff select (ANN/S/C4/PERF/TC/TID/PT/RET/PL/D/BLE/TRY/LOG/G), filterwarnings=error, and no standalone isort/pylint — all present in pyproject.toml.

---

## #9 — Expand pre-commit (TRIVIAL — extend thin existing config) (TRIVIAL)

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:feature, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/9

**Body**

Approach: (see plan)

Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md#expand-pre-commit-trivial-extend-thin-existing-con
Tracks: #5

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  Already implemented: .editorconfig, .gitlint, pre-commit, basedpyright recommended mode, full canonical ruff select (ANN/S/C4/PERF/TC/TID/PT/RET/PL/D/BLE/TRY/LOG/G), filterwarnings=error, and no standalone isort/pylint — all present in pyproject.toml.

---

## #10 — Add gitlint (TRIVIAL)

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:feature, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/10

**Body**

Approach: (see plan)

Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md#add-gitlint-trivial
Tracks: #5

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  Already implemented: .editorconfig, .gitlint, pre-commit, basedpyright recommended mode, full canonical ruff select (ANN/S/C4/PERF/TC/TID/PT/RET/PL/D/BLE/TRY/LOG/G), filterwarnings=error, and no standalone isort/pylint — all present in pyproject.toml.

---

## #11 — Expand ruff `select` to canonical set (MODERATE)

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:feature, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/11

**Body**

Approach: (see plan)

Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md#expand-ruff-select-to-canonical-set-moderate
Tracks: #5

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  Already implemented: .editorconfig, .gitlint, pre-commit, basedpyright recommended mode, full canonical ruff select (ANN/S/C4/PERF/TC/TID/PT/RET/PL/D/BLE/TRY/LOG/G), filterwarnings=error, and no standalone isort/pylint — all present in pyproject.toml.

---

## #12 — Pytest hardening (MODERATE — coverage floor pressure)

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:feature, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/12

**Body**

Approach: (see plan)

Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md#pytest-hardening-moderate-coverage-floor-pressure
Tracks: #5

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  Already implemented: .editorconfig, .gitlint, pre-commit, basedpyright recommended mode, full canonical ruff select (ANN/S/C4/PERF/TC/TID/PT/RET/PL/D/BLE/TRY/LOG/G), filterwarnings=error, and no standalone isort/pylint — all present in pyproject.toml.

---

## #13 — Upgrade basedpyright to `recommended` + Makefile/CI wiring (MODERATE)

`author:` ConcaveTrillion · `created:` 2026-05-17 · `closed:` 2026-05-19 · `state:` CLOSED (COMPLETED)

`labels:` kind:feature, status:backlog

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/13

**Body**

Approach: (see plan)

Plan: docs/plans/2026-05-17-pd-ocr-cli-strict-linting.md#upgrade-basedpyright-to-recommended-makefileci-wir
Tracks: #5

**Comments (1)**

- **ConcaveTrillion** (2026-05-19):
  Already implemented: .editorconfig, .gitlint, pre-commit, basedpyright recommended mode, full canonical ruff select (ANN/S/C4/PERF/TC/TID/PT/RET/PL/D/BLE/TRY/LOG/G), filterwarnings=error, and no standalone isort/pylint — all present in pyproject.toml.

---

## #14 — chore: document all lint-rule suppressions (lint-deviations.md)

`author:` ConcaveTrillion · `created:` 2026-05-21 · `closed:` 2026-05-22 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/14

**Body**

## Summary

Apply the workspace `CONVENTIONS.md` rule **"Document every lint-rule
suppression"** to `pd-ocr-cli`. `pd-book-tools` is the reference implementation.

Part of the cross-cut rollout tracked in ConcaveTrillion/ocr-container-meta#291.

## Tasks

- [ ] Grep for all standing suppressions: `# pyright: ignore`, `# type: ignore`,
      `# noqa`, and ruff `[tool.ruff.lint]` `ignore` / `per-file-ignores`.
- [ ] Add a concise inline rationale at each suppression point (or remove the
      suppression and fix the underlying issue if it isn't warranted).
- [ ] Create `docs/conventions/lint-deviations.md` cataloguing every remaining
      deviation (rule, tool, file locations, justification). Tag any genuinely
      unclear case "needs review" rather than inventing a rationale.
- [ ] Prefer tool-native codes correctly
      (`# pyright: ignore[reportRuleName]`, not `# type: ignore[mypy-code]`).

## Reference

- Rule: workspace `CONVENTIONS.md` → "Document every lint-rule suppression"
- Reference implementation: `pd-book-tools/docs/conventions/lint-deviations.md`
- Cross-cut tracking issue: ConcaveTrillion/ocr-container-meta#291

---

## #15 — Security: pin default OCR model revisions and avoid unsafe torch.load trust boundary

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, status:blocked, priority:high, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/15

**Body**

## Finding
Default OCR model downloads are mutable (`--model-version` defaults to latest) and the resulting `.pt` checkpoints are loaded through `torch.load`.

## Evidence
- `pd_ocr_cli/ocr_to_txt.py:325` defaults `--model-version` to `None` / latest.
- `pd_ocr_cli/_hf_models.py:80` delegates model resolution to `pd-book-tools`.
- Installed dependency evidence during review: `pd_book_tools/hf/models.py:63` downloads with `revision=None`; `pd_book_tools/ocr/doctr_support.py:244` and `:275` load checkpoints through `torch.load`.

## Impact
A compromised or malicious default Hugging Face model file can execute code during checkpoint loading on first run.

## Remediation
Pin default OCR model revisions to immutable commit SHAs, require explicit opt-in for mutable/non-default repos or revisions, and migrate checkpoints to a safe loading format such as `safetensors` or `torch.load(..., weights_only=True)` where compatible.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 1.

**Comments (2)**

- **ConcaveTrillion** (2026-05-23):
  **Partially shipped + blocked.**

  - ✅ **Part 1 (model revision pinning):** Shipped on branch \`fix/security-15-torch-load-pinning\` (commit \`78dde81\`, local-only). Default revision now pinned to \`v0.6\` (immutable tag on \`CT2534/pd-ocr-models\`); tests guard against moving refs.
  - 🚫 **Part 2 (\`weights_only=True\`):** Blocked upstream. \`pd_book_tools.get_finetuned_torch_doctr_predictor\` does not currently accept a \`torch_load\` kwarg, so the CLI layer can't inject \`weights_only=True\` without monkey-patching. Tracking in ConcaveTrillion/pd-book-tools#205.

  A placeholder test (\`tests/test_security_model_pinning.py::test_upstream_get_finetuned_does_not_expose_torch_load_param\`) will flip red once pd-book-tools#205 ships, as the cue to wire the second half here.

  **This issue stays OPEN** until pd-book-tools#205 ships and Part 2 lands.

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#blocked (this item is in the **Blocked** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #16 — Security: warn or guard when users supply arbitrary .pt model checkpoints

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/16

**Body**

## Finding
User-supplied Hugging Face repos/files and local `.pt` paths cross the same unsafe checkpoint-loading trust boundary as default models.

## Evidence
- `pd_ocr_cli/ocr_to_txt.py:317` accepts `--hf-repo`.
- `pd_ocr_cli/ocr_to_txt.py:325` accepts `--model-version`.
- `pd_ocr_cli/ocr_to_txt.py:344` and `:351` accept local `.pt` detection/recognition files.

## Impact
Users can be tricked into running untrusted `.pt` checkpoints that execute code locally.

## Remediation
Document model paths/repos as executable trust inputs, warn on non-default repos/local `.pt` files, and prefer safe model formats.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 2.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #17 — Security: use exclusive non-symlink temp files for atomic writes

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/17

**Body**

## Finding
Atomic writes use predictable sibling temp names opened with truncate semantics, and JSON/crop writes use predictable temp names too.

## Evidence
- `pd_ocr_cli/_pipeline.py:57` derives deterministic temp path `.{name}.tmp`.
- `pd_ocr_cli/_pipeline.py:88` opens with `O_CREAT | O_TRUNC` without exclusive/no-follow protection.
- `pd_ocr_cli/ocr_to_txt.py:820` and `:871` create deterministic JSON/crop temp names.

## Impact
In an attacker-writable output directory, a pre-created temp symlink can truncate or overwrite files writable by the user.

## Remediation
Create temp files with exclusive creation in the destination directory, reject symlink temps, and preserve atomic replace semantics.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 3.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #18 — Bug: run layout detection and illustration crops on rotated page images

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:high, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/18

**Body**

## Finding
Auto-rotated OCR pages can still get layout regions and illustration crops from the original unrotated image path.

## Evidence
- `pd_ocr_cli/ocr_to_txt.py:728` creates the OCR document.
- `pd_ocr_cli/ocr_to_txt.py:743` passes the original `img_path` to layout detection.
- `pd_ocr_cli/ocr_to_txt.py:850` re-reads the original image for crops.

## Impact
Sideways/upside-down scans may OCR correctly while layout detection and crops run on the unrotated source, producing misaligned regions, wrong reading-order hints, wrong figure/caption tagging, or crops from the wrong coordinates.

## Remediation
Pass the OCR page's rotated image/frame to layout detection and crop extraction when available, and add a rotated-image regression test.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 4.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#now--highest-priority (this item is in the **Now — highest priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #19 — Bug: detect output path collisions for file inputs with the same basename

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-05-23 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:high

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/19

**Body**

## Finding
Explicit file inputs with the same basename silently overwrite each other under `-o`.

## Evidence
- `pd_ocr_cli/_pipeline.py:159` returns no mirror root for file-only inputs.
- `pd_ocr_cli/_pipeline.py:200` writes flat under `--output-dir`.
- `pd_ocr_cli/_pipeline.py:205` builds output names from basename only.

## Impact
`pd-ocr -o out dir1/page.png dir2/page.png` writes both pages to `out/page.txt`; the later page silently replaces the earlier output.

## Remediation
Preflight output-path collisions and fail clearly, or mirror by a common parent when collisions would occur.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 5.

**Comments (1)**

- **ConcaveTrillion** (2026-05-23):
  Fixed in commit 60577d7 on branch fix/bug-19-output-path-collisions. Added `check_output_collisions` preflight that exits 1 with an actionable error before any image is processed.

---

## #20 — Bug: skip layout loading and inference for plain --no-reorg runs

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/20

**Body**

## Finding
`--no-reorg` still resolves, downloads, loads, and runs layout detection when layout output cannot affect text output.

## Evidence
- `pd_ocr_cli/ocr_to_txt.py:655` resolves/prefetches layout source when layout is enabled.
- `pd_ocr_cli/ocr_to_txt.py:677` loads layout detector.
- `pd_ocr_cli/ocr_to_txt.py:741` runs detection.
- `pd_ocr_cli/ocr_to_txt.py:754` computes `do_reorg` only after layout work.

## Impact
A user asking for raw OCR can still pay layout model download/load costs and can fail on layout network/model errors even though reorganization is disabled.

## Remediation
Compute an effective layout need: reorg will run or illustration extraction is requested. Skip layout for plain `--no-reorg`.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 6.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #21 — Bug: make JSON and crop writes use the durable atomic-write path

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/21

**Body**

## Finding
JSON and crop writes bypass the durable fsync + replace helper used for `.txt` output.

## Evidence
- `pd_ocr_cli/_pipeline.py:46` states all pipeline disk writes should use sibling temp, fsync, replace, and parent-dir fsync.
- `pd_ocr_cli/ocr_to_txt.py:820` and `:827` write JSON via `doc.to_json_file()` then `os.replace()`.
- `pd_ocr_cli/ocr_to_txt.py:871` and `:881` write crops via `cv2.imwrite()` then `os.replace()`.

## Impact
A crash or power loss can lose or corrupt sidecar/crop outputs even when `.txt` output uses the stronger durability path.

## Remediation
Serialize JSON and encoded crop bytes through the atomic write helper, or add a binary/callback atomic writer that fsyncs the temp file and parent directory.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 7.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #22 — Bug: roll back sidecars and crops when final .txt write fails

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/22

**Body**

## Finding
A failed final `.txt` write leaves earlier JSON/diagnostic/crop artifacts behind.

## Evidence
- Sidecars and crops are written before the final text write.
- `pd_ocr_cli/ocr_to_txt.py:888` writes the final `.txt`.
- No rollback removes artifacts if the final write fails.

## Impact
A failed page can leave new sidecars/crops without a `.txt`, violating the code's all-or-nothing artifact comment and confusing downstream consumers that inspect sidecars directly.

## Remediation
Track newly created artifacts and unlink them if a later mandatory artifact fails, or stage all page artifacts and promote them only after every artifact succeeds.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 8.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #23 — Bug: make the PowerShell installer resolve pd-book-tools from pd-index-pip

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:high, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/23

**Body**

## Finding
The Windows installer likely cannot resolve `pd-book-tools` consistently because it never adds the pd-index-pip index.

## Evidence
- `install.ps1:137` installs from a GitHub source ref.
- `install.ps1:156` only adds an extra index when CUDA/PyTorch is detected.
- `pyproject.toml:16` depends on `pd-book-tools>=0.12.0`.
- `pyproject.toml:51` declares the uv source only for this repo's own uv operations.
- `install.sh:151` explicitly passes the pd index URL.

## Impact
Windows installs can fail to resolve `pd-book-tools` or resolve it from an unintended source.

## Remediation
Make `install.ps1` mirror `install.sh`: install the release wheel, always pass `https://concavetrillion.github.io/pd-index-pip/simple/`, and test generated `uv tool install` arguments.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 9.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#now--highest-priority (this item is in the **Now — highest priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #24 — Security: prevent dependency confusion for pd-book-tools installs

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/24

**Body**

## Finding
Installer dependency resolution permits dependency confusion for `pd-book-tools`.

## Evidence
- `pyproject.toml:16` uses a generic lower-bound dependency on `pd-book-tools`.
- `install.sh:151` passes the private index as `--extra-index-url`.
- `install.ps1` omits the private index entirely in the CPU path.

## Impact
A same-named package on a higher-priority/default index could satisfy `pd-book-tools` during installation.

## Remediation
Use an index strategy that prevents PyPI fallback for `pd-book-tools`, or pin by direct URL/hash. Add the pd index consistently to Windows installs.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 10.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #25 — CI: run server-side tests before publishing tag-triggered releases

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:high, area:ci, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/25

**Body**

## Finding
Tag-pushed releases publish artifacts without a server-side test gate.

## Evidence
- `.github/workflows/release.yml:17` runs on any `v*` tag push.
- `.github/workflows/release.yml:50` builds artifacts.
- `.github/workflows/release.yml:61` publishes the release.
- The local preflight in `scripts/do-release.sh` can be bypassed by a direct tag push.

## Impact
A tag push can publish wheel/sdist artifacts that never passed tests, typecheck, pre-commit, or integration checks on GitHub Actions.

## Remediation
Run `make ci` or `make ci-slow` in the release workflow before `uv build`, add a smoke install from the built wheel, and protect release tags.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 11.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#now--highest-priority (this item is in the **Now — highest priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #26 — CI: pin release workflow actions and uv to immutable versions

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:ci, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/26

**Body**

## Finding
The privileged release workflow uses mutable third-party action refs and tool versions.

## Evidence
- `.github/workflows/release.yml:31` grants write/id-token/attestation permissions.
- `.github/workflows/release.yml:36`, `:43`, `:57`, and `:62` use action tags.
- `.github/workflows/release.yml:45` installs `uv` with `version: latest`.
- `zizmor` also flagged unpinned action refs in both CI and release workflows.

## Impact
A compromised/moved action tag or latest tool release can influence release artifacts.

## Remediation
Pin actions by full commit SHA and pin `uv` to a specific version.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 12.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #27 — CI: remove template-injection risk from release dispatch shell block

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:high, area:ci, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/27

**Body**

## Finding
`zizmor` flagged template injection in the release workflow shell block.

## Evidence
- `.github/workflows/release.yml:94` interpolates `${{ github.ref_name }}` directly into a `run:` block.

## Impact
If an attacker can influence a matching tag name, expression expansion can alter shell script behavior in a privileged release job.

## Remediation
Pass `github.ref_name` through an environment variable and quote it inside the script, or avoid shell interpolation entirely.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 13.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#now--highest-priority (this item is in the **Now — highest priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #28 — CI: disable persisted checkout credentials where not needed

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:low, area:ci, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/28

**Body**

## Finding
`zizmor` flagged checkout steps without `persist-credentials: false`.

## Evidence
- `.github/workflows/ci.yml:20` uses `actions/checkout` without disabling persisted credentials.
- `.github/workflows/release.yml:36` uses `actions/checkout` without disabling persisted credentials.

## Impact
Persisted credentials can be exposed to later steps or accidentally captured in artifacts if the workflow grows.

## Remediation
Set `persist-credentials: false` for checkout steps unless a later git push from the checkout is required.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 14.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#later--low-priority (this item is in the **Later — low priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #29 — CI: disable or harden setup-uv cache in the release workflow

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:low, area:ci, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/29

**Body**

## Finding
`zizmor` flagged release workflow caching as a cache-poisoning risk.

## Evidence
- `.github/workflows/release.yml:43` uses `astral-sh/setup-uv` in a tag-triggered publishing workflow.

## Impact
Runtime artifacts in a publishing workflow can be influenced by a poisoned cache.

## Remediation
Disable cache for the release workflow or scope/cache-key it so untrusted refs cannot influence release builds.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 15.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#later--low-priority (this item is in the **Later — low priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #30 — Security: verify downloaded release artifacts in installers

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/30

**Body**

## Finding
The default installer downloads release artifacts without checksum, signature, or attestation verification.

## Evidence
- `.github/workflows/release.yml:56` creates attestations.
- `install.sh:136` downloads the wheel.
- `install.sh:158` installs the wheel.
- `README.md:60` recommends piping the installer.

## Impact
Users have no install-time protection if a release asset, account, or network path is compromised.

## Remediation
Publish checksums and verify them in installers, or verify GitHub artifact attestations/Sigstore before `uv tool install`.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 16.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #31 — Deps: bound runtime dependency ranges and smoke-test released installs

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/31

**Body**

## Finding
Runtime dependency ranges are open-ended for released installs.

## Evidence
- `pyproject.toml:16` uses `pd-book-tools>=0.12.0`.
- `pyproject.toml:17` uses `huggingface_hub>=0.23`.
- The installer resolves from live indexes at install time.

## Impact
Future incompatible `pd-book-tools`, `huggingface_hub`, or transitive releases can break fresh installs without a code change here.

## Remediation
Add conservative upper bounds for runtime dependencies and run a release smoke install from the built wheel using the same indexes as installers.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 17.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #32 — Docs: fix README manual install index URL

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-05-23 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:low, area:docs

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/32

**Body**

## Finding
README manual install commands use the wrong self-hosted index URL.

## Evidence
- `README.md:284` and `README.md:294` point to `https://concavetrillion.github.io/pd-index/simple/`.
- Project config and installer use `https://concavetrillion.github.io/pd-index-pip/simple/`.

## Impact
Users following the safer manual install path can fail to resolve `pd-book-tools` and fall back to the piped installer.

## Remediation
Correct the README URLs and add a docs/install command smoke check.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 18.

---

## #33 — Security: avoid shell-interpolated ARGS passthrough in local Make targets

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:low, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/33

**Body**

## Finding
Developer Makefile targets interpolate `ARGS` directly into shell commands.

## Evidence
- `Makefile:248` runs `uv run pd-ocr $(ARGS)`.
- `Makefile:251` runs `uv run python $(ARGS)`.

## Impact
A developer who copies an untrusted `make run-local ARGS=...` or `python-local ARGS=...` command can execute shell metacharacters locally.

## Remediation
Avoid shell-interpolated passthrough for arbitrary args, use a wrapper script, or clearly document these as trusted developer-only targets.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 19.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#later--low-priority (this item is in the **Later — low priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #34 — Security: constrain update-check URL opener to HTTPS-only behavior

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/34

**Body**

## Finding
`bandit` flagged the update check's `urllib.request.urlopen` call as B310.

## Evidence
- `pd_ocr_cli/_update_check.py:81` uses `urllib.request.urlopen`.
- The URL is currently fixed HTTPS, but the generic opener accepts more schemes by default.

## Impact
Future changes could accidentally allow non-HTTPS schemes or make the update check harder to audit.

## Remediation
Enforce the expected scheme before opening, keep the URL constant, or switch to a client path that rejects non-HTTPS schemes by construction.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 20.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #35 — Observability: make best-effort update-check failures diagnosable

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:low, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/35

**Body**

## Finding
`bandit` flagged the update check's broad swallowed exception as B110.

## Evidence
- `pd_ocr_cli/_update_check.py:118` catches all exceptions and silently passes.

## Impact
Update-check regressions, parser changes, or API contract breaks become silent and can remain undiscovered.

## Remediation
Keep best-effort behavior but emit debug-level diagnostics behind an environment flag or record failures in telemetry-free logs/tests.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 21.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#later--low-priority (this item is in the **Later — low priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #36 — Security: execute resolved nvidia-smi path for GPU nudge probe

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:low, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/36

**Body**

## Finding
`bandit` flagged the GPU nudge's `nvidia-smi` subprocess call as B603/B607.

## Evidence
- `pd_ocr_cli/ocr_to_txt.py:242` runs `subprocess.run(["nvidia-smi"], shell=False, ...)`.
- The command is fixed, but the executable is resolved from PATH.

## Impact
A malicious earlier PATH entry can run during the optional GPU nudge probe in a compromised local environment.

## Remediation
Resolve with `shutil.which()`, execute the resolved absolute path, and keep `shell=False`.

## Source
Deep review report: `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md` finding 22.

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#later--low-priority (this item is in the **Later — low priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #37 — CI: pin CI workflow actions and uv to immutable versions

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:high, area:ci, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/37

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- .github/workflows/ci.yml:20 uses actions/checkout@v4.\n- .github/workflows/ci.yml:23 uses astral-sh/setup-uv@v4.\n- .github/workflows/ci.yml:25 installs uv version latest.\n- zizmor reports unpinned-uses for both CI actions.\n\nImpact:\nA moved or compromised action tag, or a breaking/latest uv release, can change CI behavior without a repository change. CI is less privileged than release, but it is still the quality gate for pull requests and main.\n\nRemediation:\nPin CI actions by full commit SHA and pin uv to a reviewed version. Add a maintenance process for reviewed action/tool updates.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#now--highest-priority (this item is in the **Now — highest priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #38 — Security: add resource limits for untrusted image inputs

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/38

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- pd_ocr_cli/ocr_to_txt.py:540 accepts file and directory inputs by suffix/path expansion.\n- pd_ocr_cli/ocr_to_txt.py:728 passes images into OCR.\n- pd_ocr_cli/ocr_to_txt.py:743 passes images into layout detection.\n- pd_ocr_cli/ocr_to_txt.py:850 re-reads images with OpenCV for illustration crops.\n\nImpact:\nHuge or malformed image files can cause CPU/GPU memory exhaustion or exercise native parser vulnerabilities in OpenCV/Pillow/DocTR dependencies. This matters when running pd-ocr on mixed-trust batches.\n\nRemediation:\nAdd configurable limits for file size, decoded pixel count, page count where applicable, and per-page processing time. Document guidance for sandboxing untrusted batches.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #39 — Bug: validate inputs before resolving and loading models

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/39

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- pd_ocr_cli/ocr_to_txt.py:649 resolves OCR model files.\n- pd_ocr_cli/ocr_to_txt.py:655-658 resolves and prefetches layout files.\n- pd_ocr_cli/ocr_to_txt.py:665-685 loads OCR/layout models.\n- Input collection and the no-valid-images check happen later at pd_ocr_cli/ocr_to_txt.py:698-701.\n\nImpact:\nCommands such as pd-ocr missing.png or pd-ocr notes.txt can download/resolve/load models before reporting that there is no work to do. Fresh installs can pay network/model cost or fail on model setup even though the input set is invalid.\n\nRemediation:\nCollect and validate images before model resolution, prefetch, device detection, and model loading. Add a regression test that patches model resolution/loading to fail if called for an empty-image run.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #40 — Bug: turn startup model and layout failures into clean CLI errors

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/40

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- pd_ocr_cli/_hf_models.py:79-90 only translates FileNotFoundError for OCR model resolution.\n- pd_ocr_cli/ocr_to_txt.py:666-670 only catches ImportError around OCR predictor loading.\n- pd_ocr_cli/ocr_to_txt.py:680-684 only catches ImportError and ValueError around layout detector loading.\n- pd_ocr_cli/ocr_to_txt.py:655-658 resolves/prefetches layout files before the per-image error handler.\n\nImpact:\nInvalid Hugging Face repos, network/cache failures, corrupt checkpoints, incompatible checkpoints, or CUDA/OOM failures can surface as raw tracebacks instead of the CLI's normal concise ERROR message and exit code.\n\nRemediation:\nWrap startup resolution/prefetch/load phases in clean error handling, with full tracebacks only under PD_OCR_DEBUG=1. Add mocked tests for resolve_ocr_models, resolve_layout_source, prefetch_layout_files, predictor load, and layout load failures.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #41 — Tests: assert default layout reorganization preserves every OCR word

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:high, area:tests, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/41

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- CLAUDE.md:39 forbids silently dropping OCR words.\n- docs/architecture/layout-aware-ocr.md:95-99 says default --experimental-drop-layout-words off preserves every OCR word.\n- tests/test_main_mocked.py:979-1004 only asserts drop_layout_words=False is forwarded.\n- tests/test_pipeline_integration.py:102-109 forces --layout-model none, and :152-155 only checks a small token subset.\n\nImpact:\nA regression in pd-book-tools or the CLI/layout interaction could drop footnote/header/footer/caption words under the default layout path while pd-ocr-cli tests still pass.\n\nRemediation:\nAdd a CLI-level integration regression using a synthetic Page/layout or small fixture page that asserts the original OCR word multiset survives default reorganization. Include header, footer, footnote, abandoned, and figure-adjacent caption words.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#now--highest-priority (this item is in the **Now — highest priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #42 — Tests: assert --no-illustration-placeholders preserves caption text

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:tests, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/42

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- docs/usage/cli-usage.md:139-141 and :277-278 promise caption text is preserved.\n- pd_ocr_cli/ocr_to_txt.py:499-508 repeats this CLI contract.\n- tests/test_main_mocked.py:1063-1089 only checks emit_illustration_placeholders=False is forwarded; it does not assert output text behavior.\n\nImpact:\nreorganize_page or CLI output wiring could suppress both placeholder and caption while the current test suite still passes.\n\nRemediation:\nAdd a CLI-level test with body, figure, and caption content. Run with and without --no-illustration-placeholders and assert caption words remain present while only the placeholder block changes.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #43 — Tests: cover the default layout-enabled end-to-end path

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:tests, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/43

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- docs/usage/cli-usage.md:116-119 documents layout detection as the default path.\n- tests/test_parse_args.py:41 confirms the default layout model is pp-doclayout-plus-l.\n- tests/test_pipeline_integration.py:102-109 always adds --layout-model none in the slow helper.\n\nImpact:\nThe shipped default command pd-ocr page.png can fail in layout resolution, detector loading, region detection, or layout-to-reorg wiring while slow integration tests continue to pass because they exercise only the non-default no-layout path.\n\nRemediation:\nAdd at least one slow default-layout test that runs without --layout-model none and asserts successful output plus expected layout UX such as the layout-region processing line.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #44 — Docs: document all accepted image suffixes including JPEG 2000

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:low, area:docs, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/44

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- docs/usage/cli-usage.md:33-35 lists .png, .jpg, .jpeg, .tif, .tiff, .bmp, and .webp only.\n- tests/test_collect_images.py:118-121 accepts every SUPPORTED_IMAGE_SUFFIXES entry.\n- tests/test_collect_images.py:132-143 explicitly asserts .jp2 support.\n\nImpact:\nUsers with JPEG 2000 scans can assume pd-ocr will skip their files even though the code accepts them.\n\nRemediation:\nUpdate usage docs to match pd_book_tools.image_processing.formats.SUPPORTED_IMAGE_SUFFIXES, or state that supported formats are delegated to pd-book-tools and include JPEG 2000 examples. Add a docs command smoke check if practical.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#later--low-priority (this item is in the **Later — low priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #45 — Security: pin pre-commit hooks or enforce reviewed hook updates

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:low, area:ci, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/45

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- .pre-commit-config.yaml:4-9 uses mutable hook tag refs for pre-commit-update and pre-commit-hooks.\n- .pre-commit-config.yaml:20-26 uses mutable tag refs for gitleaks and ruff-pre-commit.\n- .pre-commit-config.yaml:36-42 and :61-64 use mutable tag refs for markdownlint and gitlint.\n\nImpact:\nA compromised or moved upstream hook tag can run code in developer environments and in CI pre-commit runs.\n\nRemediation:\nPin hooks to commit SHAs, or formalize reviewed pre-commit autoupdate PRs with diff review before adoption.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#later--low-priority (this item is in the **Later — low priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #46 — Deps: add integrity hashes for pd-book-tools lock entries

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/46

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- uv.lock:1838 points to the pd-book-tools sdist URL without a hash.\n- uv.lock:1840 points to the pd-book-tools wheel URL without a hash.\n\nImpact:\nThe lockfile does not provide artifact integrity verification for the key private dependency. A changed or compromised release artifact can be consumed without the lockfile detecting a hash mismatch.\n\nRemediation:\nPublish PEP 503 hash fragments in pd-index-pip or otherwise lock pd-book-tools direct URL hashes, then refresh uv.lock.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #47 — CI: test all supported Python versions

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:ci, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/47

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- pyproject.toml:14 claims support for Python >=3.10,<3.14.\n- .github/workflows/ci.yml:17 only sets UV_PYTHON=3.13.\n- .github/workflows/release.yml:48 builds with Python 3.12.\n\nImpact:\nPython 3.10, 3.11, or 3.12 runtime/install failures can ship unnoticed even though the package metadata advertises support.\n\nRemediation:\nAdd a CI matrix for all supported Python versions, at least smoke tests plus lock/install checks for 3.10, 3.11, 3.12, and 3.13.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #48 — Docs: align release instructions with do-release push behavior

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:low, area:docs, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/48

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- DEVELOPMENT.md:134-138 says make release-* only creates a local tag and does not push.\n- scripts/do-release.sh:143-144 pushes main plus tags unless SKIP_PUSH=1.\n\nImpact:\nMaintainers can accidentally push a release while expecting a local-only tag, or run redundant/confusing push commands after the script already pushed.\n\nRemediation:\nUpdate DEVELOPMENT.md to describe the script's default push behavior and SKIP_PUSH=1, or change the script to require an explicit push flag.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#later--low-priority (this item is in the **Later — low priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #49 — Bug: make the PowerShell installer use the release wheel path

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:bug, status:backlog, priority:medium, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/49

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- README.md:248-249 says installers resolve the latest non-prerelease GitHub Release and download the published .whl asset.\n- install.ps1:137 constructs a git+https source install ref.\n- install.ps1:139-143 resolves tags from the tags API, not release wheel assets.\n- install.ps1:156-160 installs that git ref directly with uv tool install.\n\nImpact:\nWindows users bypass the documented and attested release-wheel path and can get different source-build behavior than Linux/macOS users. This also leaves the PowerShell installer out of any future wheel checksum or attestation verification path unless it is aligned.\n\nRemediation:\nMake install.ps1 mirror install.sh: resolve the latest release, download the wheel asset, pass the pd index, and verify provenance/checksums when available.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #50 — Build: pin build backend versions used for releases

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/50

**Body**

Finding from 2026-05-22 deep code/security review.\n\nEvidence:\n- pyproject.toml:2 declares build-system requires as hatchling and hatch-vcs without version bounds.\n- .github/workflows/release.yml:50 runs uv build in the release workflow.\n\nImpact:\nA future build backend release can change wheel/sdist contents or break release builds without any repository change. In the release workflow this affects official artifacts.\n\nRemediation:\nPin build backend versions to reviewed ranges or exact versions and update them through explicit maintenance PRs. Include release smoke checks from built artifacts.\n\nReview report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---

## #51 — Deps: upgrade vulnerable idna lock entry

`author:` ConcaveTrillion · `created:` 2026-05-22 · `closed:` 2026-07-14 · `state:` CLOSED (COMPLETED)

`labels:` kind:chore, status:backlog, priority:medium, area:deps, migrated

`url:` https://github.com/pdomain/pdomain-ocr-cli/issues/51

**Body**

Finding from 2026-05-22 deep code/security review.

Evidence:
- uv.lock:773-774 pins idna 3.13.
- uvx pip-audit -r a requirements file containing idna==3.13 reports CVE-2026-45409 fixed in idna>=3.15.

Impact:
The locked dependency graph contains a package with a known CPU denial-of-service vulnerability in crafted IDNA input handling. Direct pd-ocr exposure appears limited, but the vulnerable package is present in the runtime dependency graph.

Remediation:
Upgrade idna to >=3.15 and refresh uv.lock. Re-run pip-audit against the runtime dependency set after the private pd-book-tools index is available to the audit command.

Review report: docs/research/2026-05-22-pd-ocr-cli-code-security-review.md

**Comments (1)**

- **ConcaveTrillion** (2026-07-14):
  Migrated to docs/ — tracking now lives in-repo at https://github.com/pdomain/pdomain-ocr-cli/blob/master/docs/roadmap.md#next--medium-priority (this item is in the **Next — medium priority** section). Closing here; the Issues tab stays open as an intake inbox and new requests are swept into docs on a cadence. Full history remains on this issue.

---
