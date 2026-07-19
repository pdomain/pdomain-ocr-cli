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

The standing roadmap contains open release, correctness, security, dependency,
test, and documentation work:
[`docs/roadmap.md`](../roadmap.md).

Output normalization remains a deferred feature pending shared upstream logic.

These docs describe current behavior:
[`docs/architecture/layout-aware-ocr.md`](../architecture/layout-aware-ocr.md),
[`docs/architecture/cli-orchestration.md`](../architecture/cli-orchestration.md),
[`docs/architecture/test-suite.md`](../architecture/test-suite.md),
[`docs/usage/cli-usage.md`](../usage/cli-usage.md), and `DEVELOPMENT.md`.

[`docs/decisions/type-suppressions.md`](../decisions/type-suppressions.md)
records suppression rationale;
[`docs/conventions/lint-deviations.md`](../conventions/lint-deviations.md)
lists the current inventory.

GitHub Issues on this repository are disabled. Former issue numbers are
provenance tags only; see
[`docs/decisions/2026-07-19-github-issues-cutover.md`](../decisions/2026-07-19-github-issues-cutover.md).

## In-flight work

No documentation-migration branch is in flight. Cutover closeout lands the
issues templates, cutover decision, and tracker disablement on the branch that
carries this update.

Product work follows the roadmap Now / Next / Blocked sections.

## Test state

The fast test suite passes with `make test AI=1` after installing the declared
PowerShell prerequisite through `scripts/ensure-pwsh.sh`.

## Risks

The roadmap includes high-priority release, correctness, and test work.

Model checkpoint safety remains partly blocked upstream.

Predictor batch-size defaults now live upstream. Only benchmarking or CLI
exposure remains deferred.

Governed defect reports (when filed) live under
[`docs/issues/`](../issues/README.md); none are open at closeout.
