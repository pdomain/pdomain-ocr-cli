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

- Keep the standing CLI roadmap current, including explicit empty states when
  it has no open items.
- Add output normalization only after `pdomain-book-tools` provides the shared
  normalization logic and glyph map.

## Deferred work

- Constrain executable model checkpoints with immutable defaults and a safer
  format or loading mode when upstream compatibility permits.
- Add untrusted-image resource controls, including file-size and decoded-pixel
  limits, and document the supported processing-time boundary.
- Verify installer-downloaded release wheels with published checksums or
  GitHub/Sigstore attestations.
- Replace mutable pre-commit revision tags with immutable commit pins where the
  update workflow can keep those pins maintainable.
- Evaluate upper bounds or compatibility caps for build and runtime
  dependencies, including `hatchling`, `hatch-vcs`, and pdomain packages.
- Further split the large happy-path and error-path test modules when doing so
  improves readability without duplicating fixtures or weakening behavior
  oracles.

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
- **Implemented and retired:** the two implementation plans and test-suite
  design spec were promoted into architecture and deleted.
- **Retired and removed:** all three former archive plans, both completed
  research records, and the superseded local-upgrade runbook. Durable behavior,
  provenance, and residual intent now live in architecture, decisions, and this
  intent map.
- **Needs owner review:** the parked predictor batch-size spec.
