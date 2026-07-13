---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: architecture
Supersedes:
  - docs/plans/2026-05-29-pdomain-ocr-cli-review-remediation.md
---

# CLI orchestration

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing CLI execution flow, batching, runtime setup, output planning, artifact writes, startup notices, or release gates.
- **Search terms:** CLI orchestration, RunPolicy, BatchPlan, RuntimeSession, PageOutputTransaction, batch errors, output collisions, release preflight.

## Ownership and data flow

`pdomain_ocr_cli.ocr_to_txt.main()` owns user-facing orchestration. It parses
arguments, invokes focused policy and planning seams, coordinates runtime work,
reports errors, and selects artifacts. Detailed rules live behind those seams.

1. `RunPolicy` converts arguments into effective layout, reorganization,
   diagnostic, and warning behavior.
2. `BatchPlan` expands inputs into page jobs and planned artifact paths before
   model startup.
3. `RuntimeSession` owns the predictor, device, and batch runner. It normalizes
   backend exceptions and validates result counts.
4. `main()` processes validated results and prepares requested artifacts.
5. Atomic helpers replace completed artifacts; `PageOutputTransaction` writes
   the final text file last.

## Execution invariants

`BatchPlan` rejects output collisions before OCR starts. A backend exception
becomes `BatchRuntimeError`, and a batch must return exactly one result per
submitted image. Artifact helpers use unique temporary files and atomic
replacement. The final text file is written last, so its presence signals a
complete requested artifact set.

## Trust and network boundaries

OCR and layout checkpoints are trusted inputs. Custom checkpoint paths or
repositories produce an explicit warning; the CLI does not sandbox model
deserialization. The startup-notice seam owns update and GPU notices, including
the environment and CLI opt-outs.

The POSIX and PowerShell installers resolve a release wheel and provide the
pdomain package index to `uv`. Piped PowerShell installation remains
self-contained.

## Release boundary

Release-grade verification runs before tag creation. The local release driver
runs `make ci-slow`, creates and pushes the tag, then dispatches the publish
workflow.

The dispatch-only `.github/workflows/release.yml` does not rerun `make ci-slow`.
It checks dependency sources, builds the tagged revision, publishes artifacts,
and notifies the package index. Static workflow tests enforce this division.
This shipped direction supersedes the implementation plan's proposal to run
slow CI inside the publish workflow.

## Evidence

Verified against the repository on 2026-07-13.

- Sources: `pdomain_ocr_cli/ocr_to_txt.py`, `_policy.py`, `_batch_plan.py`,
  `_runtime.py`, `_artifacts.py`, `_model_security.py`, `_startup_notices.py`,
  `scripts/do-release.sh`, and `.github/workflows/release.yml`.
- Tests: `tests/test_policy.py`, `tests/test_batch_plan.py`,
  `tests/test_main_errors.py`, `tests/test_artifacts.py`,
  `tests/test_model_security.py`, `tests/test_startup_notices.py`,
  `tests/test_install_sh.py`, `tests/test_install_ps1.py`, and
  `tests/test_workflows_static.py`.
- History: commits `87f066a`, `bcf8807`, `a0c2054`, `0287e2c`, `1c3993c`,
  and `9e8b089`.
