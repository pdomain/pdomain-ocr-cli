---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-07
Kind: architecture
Supersedes:
  - docs/plans/2026-05-29-pdomain-ocr-cli-review-remediation.md
---

# CLI orchestration

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing CLI execution flow, batching, runtime setup, output planning, artifact writes, image limits, model pins, installers, dependency bounds, startup notices, or releases.
- **Search terms:** CLI orchestration, RunPolicy, BatchPlan, RuntimeSession, PageOutputTransaction, batch errors, output collisions, rollback, image limits, installer digest, first-index, dependency bounds, release preflight.

## Ownership and data flow

`pdomain_ocr_cli.ocr_to_txt.main()` owns user-facing orchestration. It parses
arguments, calls focused policy and planning seams, coordinates runtime work,
reports errors, and selects artifacts. Detailed rules live behind those seams.

1. `RunPolicy` converts arguments into effective layout, reorganization,
   diagnostic, and warning behavior.
2. `BatchPlan` expands inputs into page jobs and planned artifact paths before
   model startup.
3. `RuntimeSession` owns the predictor, device, and batch runner. It normalizes
   backend exceptions and validates result counts.
4. `main()` processes validated results and prepares requested artifacts.
5. `PageOutputTransaction` stages JSON, illustration crops, and the final
   text file, then promotes the text file last. A failed promotion rolls
   those files back.

The CLI builds the fine-tuned DocTR predictor through the two-checkpoint-path
`get_finetuned_torch_doctr_predictor` call. `pdomain-book-tools` owns the
predictor's internal detection and recognition batch sizes. Its defaults are
`det_bs=2` and `reco_bs=128`; the CLI does not expose overrides.

## Execution invariants

`BatchPlan` expands inputs and rejects output collisions **before** model
resolution or load. Invalid inputs and plan failures exit with a clear
`ERROR:` line and never start OCR. Model or layout resolve/load failures also
exit as clean CLI errors (not raw stack traces for expected resolve paths).

A backend exception becomes `BatchRuntimeError`, and a batch must return
exactly one result per submitted image.

Every candidate image passes an admission check before it joins a batch.
Files over 100 MiB or 100,000,000 decoded pixels are rejected as a per-image
error, and the rest of the batch continues. `ocr_to_txt` sets
`OPENCV_IO_MAX_IMAGE_PIXELS` on import, before anything loads cv2, unless the
caller already set it. A cv2 error that names `CV_IO_MAX_IMAGE_PIXELS` becomes
`ImageLimitError`, which names the path and the limit.

`PageOutputTransaction` stages the JSON sidecar, illustration crops, and the
final text file as exclusive temporary files, then promotes them. The text
file is promoted last, so its presence signals a complete artifact set. If
promotion fails, the transaction removes new files and restores the ones it
replaced. Files staged before a failed commit are removed. When rollback also
fails, the CLI reports the affected paths. A `KeyboardInterrupt` during commit
stays a `KeyboardInterrupt`, and its rollback notes print before the interrupt
summary. Diagnostic snapshots and the layout-debug report stay outside the
transaction.

## Trust and network boundaries

OCR and layout checkpoints are trusted inputs. The default OCR model is
`pdomain/pdomain-ocr-models` pinned to revision `v0.7`. Only an unset revision
or `latest` counts as mutable, and an explicit `latest` still prints a trust
warning. Custom checkpoint paths or repositories also print a warning. The CLI
does not sandbox model deserialization itself. `pdomain-book-tools` loads
DocTR checkpoints with `torch.load(..., weights_only=True)` and rejects any
checkpoint that is not a plain state dict of tensors. No test in this
repository guards that upstream behavior yet.

The startup-notice seam owns update and GPU notices, including the environment
and CLI opt-outs. The update check stays silent on failure unless
`PD_OCR_DEBUG` is set. Then stderr gets
`update check failed: {type}: {message}`, without tracebacks, tokens, or
response bodies.

The POSIX and PowerShell installers install the wheel from the latest GitHub
Release. They pass the pdomain index to `uv` as a named `--index` with
`--index-strategy first-index`, so a pdomain package name cannot resolve from
another index. Before download, each installer requires the release asset's
digest to be a lowercase `sha256:` plus 64 hex characters. After download, it
refuses the wheel if the bytes do not match. `install.sh` reads the digest
from the wheel's own asset record, so a CR or CRLF between assets cannot apply
the sdist digest to the wheel. Piped PowerShell installation stays
self-contained, and Windows PowerShell 5.1 skips the Unix file-mode step.

## Dependency bounds

Every direct runtime dependency has an upper bound or an exact pin.
`pdomain-book-tools` is pinned exactly at `==0.30.1`. The build backends are
pinned exactly at `hatchling==1.33.0` and `hatch-vcs==0.5.0`.
`tests/test_dependency_metadata.py` enforces both rules.

## Release boundary

Releases run locally; GitHub runs no workflows for this repository. The
CI, dependency-refresh, and release workflows were removed on 2026-09-13.
`make release-{patch,minor,major}` calls `scripts/do-release.sh`. It runs the
`make ci-slow` preflight, creates and pushes the tag, builds the wheel and
sdist, and creates the GitHub Release with those assets
(`scripts/release-common.sh`). Publishing the pip index is a separate local
command, `./scripts/publish-index.sh`, in `pdomain-index-pip`.

## Evidence

Verified against the repository at `7af73fc` on 2026-11-07, by reading code
and tests. The v0.9.1 release preflight `make ci-slow` passed with 468 tests.

- Sources: `pdomain_ocr_cli/ocr_to_txt.py`, `_policy.py`, `_batch_plan.py`,
  `_runtime.py`, `_artifacts.py`, `_image_limits.py`, `_model_security.py`,
  `_update_check.py`, `_startup_notices.py`, `install.sh`, `install.ps1`,
  `pyproject.toml`, `scripts/do-release.sh`, and `scripts/release-common.sh`.
- Tests: `tests/test_policy.py`, `tests/test_batch_plan.py`,
  `tests/test_main_errors.py`, `tests/test_artifacts.py`,
  `tests/test_image_limits.py`, `tests/test_opencv_io_max_image_pixels.py`,
  `tests/test_model_security.py`, `tests/test_update_check_network.py`,
  `tests/test_startup_notices.py`, `tests/test_install_sh.py`,
  `tests/test_install_ps1.py`, and `tests/test_dependency_metadata.py`.
- History: commits `87f066a`, `bcf8807`, `a0c2054`, `0287e2c`, `1c3993c`,
  and `9e8b089`; workflow removal `7041179`; installer checks `23f263e`;
  update-check diagnostics `b9e1f02`; dependency bounds `7b0f4f7`; model pin,
  image limits, and rollback `7af73fc`. Upstream predictor defaults landed in
  `pdomain-book-tools` commit `5585d27`.
