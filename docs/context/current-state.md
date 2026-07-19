---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-19
Kind: context
---

# Current State

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** starting repository work or checking current documentation state.
- **Search terms:** current state, priorities, risks, in-flight work.

## What matters now

Highest open product work is on the roadmap Now section:

- Layout/crop alignment with OCR page rotation (former GH #18)
- Default-layout word-preservation multiset coverage (former GH #41)

See [`docs/roadmap.md`](../roadmap.md). Output normalization remains deferred
pending shared upstream logic.

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

No feature branch is required for docs hygiene. Product work follows the
roadmap Now / Next / Blocked sections after the 2026-07-19 completed-item
reconcile.

## Test state

The fast test suite passes with `make test AI=1` after installing the declared
PowerShell prerequisite through `scripts/ensure-pwsh.sh`.

## Risks

- Rotation vs layout misalignment on rotated pages until #18 lands.
- Model checkpoint safety remains partly blocked upstream (#15).
- Installer dependency-confusion residual (#24) and missing wheel integrity
  checks (#30).

Predictor batch-size defaults now live upstream. Only benchmarking or CLI
exposure remains deferred.

Open governed defect and residual reports live under
[`docs/issues/`](../issues/README.md) (12 active); see intent-map Open issues.
