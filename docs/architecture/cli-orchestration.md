---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-13
Kind: architecture
Supersedes:
  - docs/plans/2026-05-29-pdomain-ocr-cli-review-remediation.md
---

# CLI orchestration

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing CLI execution flow, batching, runtime setup, output planning, artifact writes, image limits, model pins, installers, dependency bounds, startup notices, releases, or the boundary with sibling repositories.
- **Search terms:** CLI orchestration, RunPolicy, BatchPlan, RuntimeSession, PageOutputTransaction, batch errors, output collisions, rollback, image limits, installer digest, first-index, dependency bounds, release preflight, repository boundary.

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
`ImageLimitError`, which names the path and the limit. The byte limit is
checked again on the bytes actually read, and the read stops one byte past the
limit, so a file that grew after the `stat` is rejected without loading it all.

A chunk holds at most 400,000,000 decoded pixels, about 1.2 GB. That is what
the default `--batch-pages 4` could already hold at the per-image limit, so
only larger `--batch-pages` values change. An image that would overrun the
chunk starts the next chunk instead. The first image in a chunk is always
admitted. The CLI does not time out a page. Stopping native OCR mid-call
would need a separate process, and this command does not do that.

`PageOutputTransaction` stages the JSON sidecar, illustration crops, and the
final text file as exclusive temporary files, then promotes them. The text
file is promoted last, after the other successfully staged artifacts. Crop
source or encoding failures can warn and omit an illustration while text still
commits. Text presence alone does not prove that every requested crop exists. If
promotion fails, the transaction removes new files and restores the ones it
replaced. Files staged before a failed commit are removed. When rollback also
fails, the CLI reports the affected paths. A `KeyboardInterrupt` during commit
stays a `KeyboardInterrupt`, and its rollback notes print before the interrupt
summary. Diagnostic snapshots and the layout-debug report stay outside the
transaction.

A crash, `SIGKILL`, or power loss mid-commit can leave hidden `.bak` and
`.stage` files next to the outputs. A later run scans each output directory
once, before it stages anything, and handles the leftovers for each file it is
about to write. If the destination is missing, recovery prefers the newest nonempty backup.
If every backup is empty, it restores the newest empty backup instead.
Every other leftover is superseded and removed. The run prints a warning for
each file it restores, removes, or cannot clean up. A backup that a successful
commit cannot delete also prints a warning, and the page still counts as
written.

Leftovers for a file the later run does not write stay in place. Stale
sidecars or crops from an earlier run with other flags are not removed.
Concurrent runs writing to the same output directory are not locked against
each other. Two runs writing the same page can remove each other's staged
files.

## Trust and network boundaries

OCR and layout checkpoints are trusted inputs. The default OCR model is
`pdomain/pdomain-ocr-models` at commit
`8b7f9b31d55015d16febaa99ae1d42960904028c`, the commit behind the tag `v0.7`.
A tag can be moved by the repository owner; a commit cannot. An unset revision
or `latest` prints a trust warning. So does any other name that is neither a
commit hash nor version-shaped, such as `main`, because a branch can move. Tags
and branches cannot be told apart offline, so a version-shaped name counts as
pinned. Custom checkpoint paths or repositories also print a warning. The CLI
does not sandbox model deserialization itself. `pdomain-book-tools` loads
DocTR checkpoints with `torch.load(..., weights_only=True)` and rejects any
checkpoint that is not a plain state dict of tensors.
`tests/test_upstream_safe_load.py` guards that upstream behavior: it scans the
installed package for any `torch.load` without `weights_only=True`, checks that
a pickled object is refused at load time, and checks that the CLI passes no
`torch_load` override.

The startup-notice seam owns update and GPU notices, including the environment
and CLI opt-outs. The update check stays silent on failure unless
`PD_OCR_DEBUG` is set. Then an exception prints
`update check failed: {type}: {message}` to stderr, without a traceback. The
message is the exception's own text and is not scrubbed. Three failures print
`update check failed: {reason}` with a fixed reason and no response data: a
response that is not a usable tag list, such as a rate-limit reply; no stable
tag; and an unparseable installed version.

The POSIX and PowerShell installers install the wheel from the latest GitHub
Release. They pass the pdomain index to `uv` as a named `--index` with
`--index-strategy first-index`, so a package listed on the pdomain index, such
as `pdomain-book-tools`, cannot resolve from another index. PyPI stays in the
index list, so a name the pdomain index does not list can still come from PyPI. Before download, each installer requires the release asset's
digest to be a lowercase `sha256:` plus 64 hex characters. After download, it
refuses the wheel if the bytes do not match. If `gh` reports no digest,
`install.sh` asks the REST API before failing closed, and it leaves the
caller's `TMPDIR` set for `uv`. `install.ps1` enables TLS 1.2 before its first
web request, for Windows PowerShell 5.1; no real 5.1 host has run it.
`install.sh` reads the digest
from the wheel's own asset record, so a CR or CRLF between assets cannot apply
the sdist digest to the wheel. Piped PowerShell installation stays
self-contained, and Windows PowerShell 5.1 skips the Unix file-mode step.
The digest comes from the same GitHub API as the wheel, so it catches
corruption in transit, not a replaced release asset. `uv` does not hash-check
the wheel's dependencies.

## Dependency bounds

Every direct runtime dependency has an upper bound or an exact pin.
`pdomain-book-tools` is pinned exactly at `==0.31.0`. The build backends are
pinned exactly at `hatchling==1.33.0` and `hatch-vcs==0.5.0`.
`tests/test_dependency_metadata.py` enforces both rules, including every
optional extra. It parses each requirement, so an environment marker cannot
stand in for a version cap. `pillow` is `>=11.0,<13`. `pdomain-book-contracts`
and `pdomain-ops` are `0.x` packages capped at `<1`. Those three ranges are
wider than one next-major step. No decision records why.

Every external pre-commit hook is pinned to a full commit SHA, with a
`# frozen: vX.Y.Z` comment naming the version. The local
`require-frozen-hook-revs` hook fails any other `rev:`. `just update-hooks`
runs `pre-commit autoupdate --freeze`, which bumps hooks and keeps SHA pins;
plain `autoupdate` would write tags back. The third-party `pre-commit-update`
hook was removed because it can only write tags.

## Repository boundary

This repository owns the `pdomain-ocr` command and the scripts that install
and release that command. `pdomain-book-tools` owns OCR, layout,
reorganization, the rotation angle, and checkpoint loading.
`pdomain-book-contracts` owns the shared curly-quote and em-dash helpers in
`pdomain_book_contracts.text.text_normalize`. `apply_text_normalizations` in
`pdomain_ocr_cli/_pipeline.py` calls those helpers before the page text is
written. This repository does not keep a second implementation. The two
flags stay off unless the user passes them. Cleanup changes the text output
only; it does not mutate the page used for JSON. No long-s or ligature map
runs on that path.

`pdomain-index-pip` publishes the wheel. The batch OCR path calls
`pdomain_ops.gpu.doctr_batch.run_doctr_batch`. `pdomain-ops` 0.12.2 sets
`page.ocr_rotation_degrees` from the degree list that `pdomain-book-tools`
0.31.0 returns. This CLI does not call `from_images_ocr_via_doctr` a second
time.

A specific compatibility fallback handles a missing
`Document.from_images_ocr_via_doctr` attribute: `_run_doctr_batch` retries via
`_run_doctr_batch_single_image_compat`. That path retains each page's rotation
degrees. Other backend errors keep their normal error path.

No long-s or ligature normalizer exists in this repository or in
`pdomain-book-tools` 0.31.0. Open work, including a shared installer, is on
the [roadmap](../roadmap.md).

## Task automation

The standalone `justfile` owns the task recipes. `ci` runs these steps in order:

1. Setup and pre-commit.
2. Read-only format and lint checks.
3. Type checking and fast coverage.
4. Installer tests, build, and wheel smoke.
5. Strict docgraph checks.

Wheel smoke checks Python 3.11, 3.12, and 3.13 by default. `ci-slow` runs
`ci` and then `coverage-slow`; it does not replace coverage with a plain test
run.

`AI=1` writes the full recipe log to `.ci-ai.log` and prints one result line.
Both coverage floors default to 100 and accept environment overrides. The
Makefile shim was removed in `10cbac7`; scripts now call `just` directly.
The existing `local-run` recipe still delegates to a missing `run` recipe.
`UV_NO_SYNC=1 uv run pdomain-ocr …` remains the documented local CLI command.

## Release boundary

Releases run locally; GitHub runs no workflows for this repository. The
CI, dependency-refresh, and release workflows were removed on 2026-09-13.
`just release-{patch,minor,major}` calls `scripts/do-release.sh`. It runs the
`just ci-slow` preflight, creates and pushes the tag, builds the wheel and
sdist, and creates the GitHub Release with those assets
(`scripts/release-common.sh`). Publishing the pip index is a separate local
command, `./scripts/publish-index.sh`, in `pdomain-index-pip`.

## Evidence

Verified against the repository at `7af73fc` on 2026-11-07, by reading code
and tests. The v0.9.1 release preflight `make ci-slow` passed with 468 tests.
The image-limit, transaction, model-pin, installer, and dependency sections
were re-read on 2026-11-12 against `fix/spec-review-followups` at `211708f`.
That branch's `make ci-slow` passed on 2026-11-10 with 537 tests. This docs
pass did not re-run it. On 2026-11-13 the pin and the batch-rotation boundary
were updated for `pdomain-book-tools` 0.31.0 and `pdomain-ops` 0.12.2.

- Sources: `pdomain_ocr_cli/ocr_to_txt.py`, `_policy.py`, `_batch_plan.py`,
  `_runtime.py`, `_artifacts.py`, `_image_limits.py`, `_model_security.py`,
  `_update_check.py`, `_startup_notices.py`, `install.sh`, `install.ps1`,
  `pyproject.toml`, `scripts/do-release.sh`, and `scripts/release-common.sh`.
- Tests: `tests/test_policy.py`, `tests/test_batch_plan.py`,
  `tests/test_main_errors.py`, `tests/test_artifacts.py`,
  `tests/test_image_limits.py`, `tests/test_opencv_io_max_image_pixels.py`,
  `tests/test_model_security.py`, `tests/test_update_check_network.py`,
  `tests/test_startup_notices.py`, `tests/test_install_sh.py`,
  `tests/test_install_ps1.py`, `tests/test_dependency_metadata.py`, and
  `tests/test_upstream_safe_load.py` (added 2026-11-07).
- History: commits `87f066a`, `bcf8807`, `a0c2054`, `0287e2c`, `1c3993c`,
  and `9e8b089`; workflow removal `7041179`; installer checks `23f263e`;
  update-check diagnostics `b9e1f02`; dependency bounds `7b0f4f7`; model pin,
  image limits, and rollback `7af73fc`; spec review fixes on branch
  `fix/spec-review-followups` (`ddf6f3f` to `211708f`). Upstream predictor defaults landed in
  `pdomain-book-tools` commit `5585d27`.

The 2026-11-13 architecture pass checked crop failure handling against
`test_main_extract_illustrations_imencode_returns_false_no_tmp_swallows_unlink`
in `tests/test_main_errors.py`, recovery ranking in `_artifacts.py`, and
`test_single_image_compat_keeps_rotation_degrees` in
`tests/test_upright_layout.py`. The worktree baseline at `10cbac7` passed
`just test` with 522 tests, 16 skipped, and 100% configured coverage.
