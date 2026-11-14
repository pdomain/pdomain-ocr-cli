---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-14
Kind: context
---

# Current State

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** starting repository work or checking current documentation state.
- **Search terms:** current state, priorities, risks, in-flight work.

## What matters now

v0.9.4 is the published release: tag `v0.9.4` at `462c181`, on GitHub
Releases and the pdomain pip index, wheel SHA256
`338cc0d5c0eebddfdff5cc53ee41282d462ceb8dcaf9de1f51c4952efc2edfb5`. Its release
preflight, `just ci-slow`, passed with 587 tests. GitHub now serves the fixed
installers from `master`.

v0.9.4 carries the installer fixes. Both installers fail when `uv` fails and
retry uv's network failures twice. The Windows command works under the default
`Restricted` execution policy. `install.ps1` checks the Visual C++ runtime and
installs it elevated when it is missing or old. On 2026-11-13 the installer ran
on real Windows PowerShell 5.1 as a standard user, including real UAC prompts
with the runtime missing and too old. Later on 2026-11-13 the README command,
`irm .../master/install.ps1 | iex`, installed v0.9.4 from GitHub as that user
in 28 s. Only the restart-required exit codes have not run on Windows; see the
[Windows proof](../research/2026-11-13-windows-installer-proof.md).

Every GPU install of v0.9.4 fails to resolve; branch `fix/torch-backend`
fixes it, unreleased as of 2026-11-14. With CUDA detected, both installers
added `--index pytorch-cuda=https://download.pytorch.org/whl/cuXXX` under
`--index-strategy first-index`. That index also hosts old copies of common
packages, with `packaging` 24.1 at most; cu126, cu128, cu130 and cu134 were
checked. uv then took `packaging` from it alone, and `pdomain-ops>=0.12.2`
needs `packaging>=26`, so uv reported "No solution found". This was seen on
2026-11-14 on an RTX 5070 Ti host with NVIDIA driver 615.78 and CUDA 13.4. The
CPU path was not affected.

The fix passes `--torch-backend auto` instead of the PyTorch index, in
`install.sh`, `install.ps1` and `scripts/install-uv-tool.sh`. uv then sends
only PyTorch packages to the PyTorch index and reads the driver version
itself. On that host, uv 0.11.26 installed v0.9.4 with this flag and
`--with 'pdomain-book-tools[gpu]'`: torch 2.14.1+cu130, packaging 26.3 and
cupy-cuda13x. OCR then ran on CUDA with 100% word overlap. uv 0.11.26 lists
explicit backends only up to cu130, so the installers use `auto` rather than
a computed tag. A uv too old for the flag gets a hint to run `uv self update`.

The open product item on the [roadmap](../roadmap.md) is long-s normalization.
The batch path reads `page.ocr_rotation_degrees` from `pdomain-ops` 0.12.2.
Quote and dash cleanup calls `pdomain-book-contracts`. The current lock uses
book-tools 0.31.0, contracts 0.3.1, and ops 0.12.2; those wheels are published
on the pdomain pip index. Pins and lock were not changed by this docs pass.

These docs describe current behavior:
[`docs/architecture/layout-aware-ocr.md`](../architecture/layout-aware-ocr.md),
[`docs/architecture/cli-orchestration.md`](../architecture/cli-orchestration.md),
[`docs/architecture/test-suite.md`](../architecture/test-suite.md),
[`docs/usage/cli-usage.md`](../usage/cli-usage.md), and `DEVELOPMENT.md`.

[`docs/decisions/type-suppressions.md`](../decisions/type-suppressions.md)
records suppression rationale;
[`docs/conventions/lint-deviations.md`](../conventions/lint-deviations.md)
lists the current inventory.

GitHub Issues on this repository are enabled but the tracker is empty.
Former issue numbers are provenance tags only; see
[`docs/decisions/2026-07-19-github-issues-cutover.md`](../decisions/2026-07-19-github-issues-cutover.md).

## In-flight work

The completed spec-review handoff is
[retired](../decisions/2026-11-13-spec-followups-handoff-retirement.md).
The architecture pass preserves the four unresolved owner choices in the
[intent map](intent-map.md). Local master keeps the exact
`pdomain-book-tools==0.31.0` pin. No newer upstream NumPy/CuPy changes enter
this CLI release through that pin. GitHub runs no workflows for this
repository; releases run locally through `just release-{patch,minor,major}`.

## Test state

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
