---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: context
---

# Intent Map

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** choosing work, checking deferred intent, or reviewing migration decisions.
- **Search terms:** active bets, deferred work, rejected directions, owner decisions.

## Active bets

- Keep the standing CLI roadmap current even when it has no open items.

## Deferred work

- Promote the durable test-suite design from
  [`docs/plans/2026-05-28-test-suite-reorganization.md`](../plans/2026-05-28-test-suite-reorganization.md)
  and its implemented spec into architecture, then retire both.
- Consolidate durable review-remediation behavior from
  [`docs/plans/2026-05-29-pdomain-ocr-cli-review-remediation.md`](../plans/2026-05-29-pdomain-ocr-cli-review-remediation.md),
  then retire the plan.
- Remove the retired security review, remediation validation, and superseded
  local-upgrade runbook after their remaining provenance is captured in durable
  architecture or decisions.

## Rejected directions

- Do not keep completed execution plans in `docs/archive/` when current code,
  tests, architecture, usage, or decisions already preserve their durable truth.

## Blocked (waiting on)

- Predictor batch-size tuning is blocked on upstream design and grooming.

## Needs owner decision

- Decide whether to pursue or abandon
  [`docs/specs/2026-05-30-predictor-batch-size-tuning.md`](../specs/2026-05-30-predictor-batch-size-tuning.md).
  The stub records no implementation, and current predictor calls expose no
  detector or recognizer batch-size arguments.
- Decide whether `docs/decisions/type-suppressions.md` should remain a separate
  decision record or be consolidated into
  [`docs/conventions/lint-deviations.md`](../conventions/lint-deviations.md).

## Legacy-unverified sweep

- **Still active:** layout-aware OCR architecture, writing style, roadmap, and
  type-suppression rationale.
- **Implemented:** both live implementation plans and the test-suite design spec.
- **Retired:** all three former archive plans, the two completed research
  records, and the superseded local-upgrade runbook. The archive plans were
  deleted; the research and runbook files remain pending provenance capture.
- **Needs owner review:** the parked predictor batch-size spec.
