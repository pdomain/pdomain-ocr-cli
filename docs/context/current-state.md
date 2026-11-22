---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-15
Kind: context
---

# Current State

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** starting repository work or checking current documentation state.
- **Search terms:** current state, priorities, risks, in-flight work.

## What matters now

See the [latest stable release](https://github.com/pdomain/pdomain-ocr-cli/releases/latest)
for the current version and download links.

This checkout supports confirmed upgrades of uv tool installations with
`pdomain-ocr update`. The updater verifies the new installation and can
restore the old one offline. Background checks are off by default.
The installers can save an opt-in preference and cache the default
detection, recognition, and layout models. The model skip flags defer
downloads.

The [dependency lock](../../uv.lock) records the versions used in development.
Fresh installations may resolve newer compatible patches from the pdomain
package index. The CLI accepts `pdomain-book-tools>=0.31.3,<0.32`.
Version 0.32 requires a cap change.
The CLI requires `pdomain-ops>=0.12.7,<1` for Python 3.11 import compatibility.

The installers retry failures that uv identifies as network errors up to
twice. On Windows, the installer checks and repairs the Visual C++ runtime when
needed. The runtime repair requests elevation. The standard-user installer
worked under the default `Restricted` policy in the
[dated Windows proof](../research/2026-11-13-windows-installer-proof.md).

Use the [CLI guide](../usage/cli-usage.md) for commands, the
[installation and update architecture](../architecture/installation-and-updates.md)
for installer and updater internals, and the
[OCR architecture](../architecture/layout-aware-ocr.md) for layout behavior.
The [test architecture](../architecture/test-suite.md) and
[development guide](../../DEVELOPMENT.md) describe verification and release.
[Type-suppression rationale](../decisions/type-suppressions.md) and
[lint deviations](../conventions/lint-deviations.md) cover exceptions.

GitHub Issues are enabled and the tracker is empty. Former issue numbers
record provenance. See the [issue cutover decision](../decisions/2026-07-19-github-issues-cutover.md).

## In-flight work

Long-s and ligature normalization remains open on the [roadmap](../roadmap.md).
Quote and dash cleanup uses `pdomain-book-contracts`. The batch path reads
`page.ocr_rotation_degrees` from `pdomain-ops`. The spec-review handoff is
[retired](../decisions/2026-11-13-spec-followups-handoff-retirement.md). The
[intent map](intent-map.md) records the four remaining owner decisions.

GitHub hosts manual macOS and Windows install tests. Start them with
`just mac-test` and `just win-test`. Run releases locally with
`just release-{patch,minor,major}`.

## Test state

The first updater passed full CI with 684 tests and 100% configured coverage.
An isolated Linux tool install upgraded from 0.1.0 to
[v0.9.6](https://github.com/pdomain/pdomain-ocr-cli/releases/tag/v0.9.6)
at commit `7deaf15`. A clean-cache model download and offline cache reuse
also passed. Linux installer tests exercise PowerShell with fakes.

The recovery worker passed installed-wheel updates on Linux and Windows.
The Windows tests confirmed that activation waits for a running model
command and checks the new installation through the same launcher. Model
prefetch reused the cache in the offline test. Windows also passed
wrong-version rollback and recovery after either directory move.

CI passed 820 tests at 100% configured coverage, with 16 slow tests skipped.
The 16 real-model integration tests passed separately. Power-loss recovery
and the restart-required update path remain unverified on Windows.

### Historical installer checks

The v0.9.4 release preflight passed 587 tests. Its commit is `462c181` and its
wheel, published on GitHub and the pdomain index, has SHA256
`338cc0d5c0eebddfdff5cc53ee41282d462ceb8dcaf9de1f51c4952efc2edfb5`.
The 2026-11-13 standard-user Windows proof covered missing and old runtimes,
real UAC prompts, and a 28-second published install.

On 2026-11-14, v0.9.4 GPU installation failed on an RTX 5070 Ti with driver
615.78 and CUDA 13.4. The cu126, cu128, cu130, and cu134 general PyTorch
indexes offered `packaging` through 24.1. Under first-index resolution, uv
selected that index for `packaging`. That failed the `pdomain-ops` requirement
of version 26 or newer. CPU installs still resolved.

On the same host, uv 0.11.26 installed v0.9.4 with `--torch-backend auto`
and an explicit `--with 'pdomain-book-tools[gpu]'`. It resolved torch
2.14.1+cu130, packaging 26.3, and cupy-cuda13x. OCR ran on CUDA with 100%
word overlap. The current scripts use the automatic backend and omit the
CuPy extra. See the
[installer architecture](../architecture/installation-and-updates.md)
for the current CUDA behavior.

### Earlier test gates

The v0.9.1 release preflight `make ci-slow` passed on 2026-11-07 with 468
tests and 100% coverage. On branch `fix/spec-review-followups`, `make ci-slow`
passed on 2026-11-10 with 537 tests and 100% coverage, on CPU with
`CUDA_VISIBLE_DEVICES=""`. The fast suite runs with `AI=1 just test` after
installing the declared PowerShell prerequisite through
`scripts/ensure-pwsh.sh`.

The isolated worktree baseline at `10cbac7` passed `just test` on
2026-11-13: 522 passed, 16 slow tests skipped, and 100% configured coverage.
That fast run does not establish real-model coverage. Windows PowerShell 5.1
coverage is limited to the
[Windows proof](../research/2026-11-13-windows-installer-proof.md).

`just ci` installs the GPU dependencies three times for its wheel smoke test,
and on 2026-11-10 that exceeded the quota on `/tmp`. Set `TMPDIR` to a directory
on a larger disk if it fails with `Disk quota exceeded`.

## Risks

Predictor batch-size defaults now live upstream. Benchmarking and any CLI
exposure stay on the roadmap.

Quote and dash cleanup calls `pdomain-book-contracts`. No long-s or ligature
normalizer exists.

The runtime installer's restart-required exit codes, 3010 and 1641, have
only run against fakes. The proof VM was left with UAC on.

Open governed reports live under [`docs/issues/`](../issues/README.md)
(1 active); see intent-map Open issues.
