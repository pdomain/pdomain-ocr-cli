---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-15
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
test, and documentation work. Output normalization remains a deferred feature
pending shared upstream logic. Current behavior is documented in
[`docs/architecture/layout-aware-ocr.md`](../architecture/layout-aware-ocr.md),
[`docs/architecture/cli-orchestration.md`](../architecture/cli-orchestration.md),
[`docs/architecture/test-suite.md`](../architecture/test-suite.md),
[`docs/usage/cli-usage.md`](../usage/cli-usage.md), and `DEVELOPMENT.md`.
Suppression rationale is recorded in
[`docs/decisions/type-suppressions.md`](../decisions/type-suppressions.md), with
the current inventory in
[`docs/conventions/lint-deviations.md`](../conventions/lint-deviations.md).

## In-flight work

The `docs/docgraph-migration` branch is removing obsolete documentation
scaffolding, consolidating writing guidance under the writing-docs plugin, and
correcting authored context against current upstream behavior.

## Test state

The fast test suite passes with `make test AI=1` after installing the declared
PowerShell prerequisite through `scripts/ensure-pwsh.sh`.

## Risks

The roadmap includes high-priority release, correctness, and test work. Model
checkpoint safety remains partly blocked upstream. Predictor batch-size
defaults now live upstream; only benchmarking or CLI exposure remains deferred.
