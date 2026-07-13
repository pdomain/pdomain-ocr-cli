---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: context
---

# Current State

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** starting repository work or checking current documentation state.
- **Search terms:** current state, priorities, risks, in-flight work.

## What matters now

The CLI has no open roadmap items. Its current behavior is documented in
[`docs/architecture/layout-aware-ocr.md`](../architecture/layout-aware-ocr.md),
[`docs/usage/cli-usage.md`](../usage/cli-usage.md), and `DEVELOPMENT.md`.

## In-flight work

The `docs/docgraph-migration` branch is migrating legacy documentation into
docgraph governance. Two implemented plans and one implemented spec still need
promotion and formal retirement.

## Test state

The fast test suite passes with `make test AI=1` after installing the declared
PowerShell prerequisite through `scripts/ensure-pwsh.sh`.

## Risks

The predictor batch-size spec remains parked without an owner decision. The
type-suppression decision record also needs reconciliation with
[`docs/conventions/lint-deviations.md`](../conventions/lint-deviations.md).
