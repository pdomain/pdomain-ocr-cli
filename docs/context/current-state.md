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

v0.9.1 is released and published to the pdomain pip index. It ships
rotation-aligned layout and crops, installer index and digest checks, image
limits, output rollback, the `v0.7` model pin, update-check diagnostics, and
dependency bounds. The 2026-11-07 spec-review fixes and the docs
consolidation are on local master and are not released. The open product
item on [`docs/roadmap.md`](../roadmap.md) is long-s normalization. The
batch path reads `page.ocr_rotation_degrees` from `pdomain-ops` 0.12.2.
Quote and dash cleanup calls `pdomain-book-contracts`. Owner decisions are
listed there and in the intent map.

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

No feature branch is open. Local master pins `pdomain-book-tools==0.31.0`
and is not released. GitHub runs no workflows for this repository; releases
run locally through `just release-{patch,minor,major}`.

## Test state

The v0.9.1 release preflight `make ci-slow` passed on 2026-11-07 with 468
tests and 100% coverage. On branch `fix/spec-review-followups`, `make ci-slow`
passed on 2026-11-10 with 537 tests and 100% coverage, on CPU with
`CUDA_VISIBLE_DEVICES=""`. The fast suite runs with `AI=1 just test` after
installing the declared PowerShell prerequisite through
`scripts/ensure-pwsh.sh`.

`just ci` installs the GPU dependencies three times for its wheel smoke test,
and on 2026-11-10 that exceeded the quota on `/tmp`. Set `TMPDIR` to a directory
on a larger disk if it fails with `Disk quota exceeded`.

## Risks

Predictor batch-size defaults now live upstream. Benchmarking and any CLI
exposure stay on the roadmap.

Quote and dash cleanup calls `pdomain-book-contracts`. No long-s or ligature
normalizer exists.

Open governed reports live under [`docs/issues/`](../issues/README.md)
(1 active); see intent-map Open issues.
