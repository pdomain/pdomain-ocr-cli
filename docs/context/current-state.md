---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-07
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
limits, output rollback, the pinned `v0.7` model, update-check diagnostics, and
dependency bounds. No product work is in the Now tier. The open items are one
test to add, one owner decision, and deferred output normalization; see
[`docs/roadmap.md`](../roadmap.md).

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

None. GitHub runs no workflows for this repository; releases run locally
through `make release-{patch,minor,major}`.

## Test state

The v0.9.1 release preflight `make ci-slow` passed on 2026-11-07 with 468
tests and 100% coverage. The fast suite runs with `make test AI=1` after
installing the declared PowerShell prerequisite through
`scripts/ensure-pwsh.sh`.

## Risks

- No test here fails if `pdomain-book-tools` drops `weights_only=True` from
  its checkpoint loader (former GH #15).

Predictor batch-size defaults now live upstream. Only benchmarking or CLI
exposure remains deferred.

Open governed reports live under [`docs/issues/`](../issues/README.md)
(3 active); see intent-map Open issues.
