---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-13
Kind: context
---

# Current State

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** starting repository work or checking current documentation state.
- **Search terms:** current state, priorities, risks, in-flight work.

## What matters now

v0.9.3 is the published release: tag `v0.9.3` at `c0419de`, on GitHub
Releases and the pdomain pip index. It includes the spec-review fixes, shared
quote/dash cleanup, batch-angle propagation and the task-runner migration.

Local master after `c0419de` adds unreleased Windows installer fixes. The
README sets a session-only execution policy before each Windows install.
`install.ps1` fails when `uv` fails, retries uv's network failures twice and
checks the Visual C++ runtime, installing it elevated when it is missing or
old. On 2026-11-13 the installer ran on real Windows PowerShell 5.1 as a
standard user, with the runtime already present. The missing-runtime install
and real UAC prompts have not run on Windows; see the
[Windows proof](../research/2026-11-13-windows-installer-proof.md). Published
users still get the old `install.ps1` from GitHub until master is pushed.

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

The Windows UAC prompt and missing-runtime paths have only run against fakes.
The proof VM has UAC off and already has the runtime installed.

Open governed reports live under [`docs/issues/`](../issues/README.md)
(1 active); see intent-map Open issues.
