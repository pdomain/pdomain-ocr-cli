---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-19
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
  it has no open items:
  [`docs/roadmap.md`](../roadmap.md).
- Add output normalization only after `pdomain-book-tools` provides the shared
  normalization logic and glyph map.
- Keep GitHub Issues disabled; plan in-repo via roadmap and
  [`docs/issues/`](../issues/README.md). See
  [`docs/decisions/2026-07-19-github-issues-cutover.md`](../decisions/2026-07-19-github-issues-cutover.md).

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
- Benchmark whether predictor-internal batching improves throughput beyond
  page chunking with `--batch-pages`.
- Decide whether the upstream `det_bs=2` and `reco_bs=128` defaults need
  device-derived tuning or a VRAM-aware clamp.
- Decide whether batch-size overrides belong in `pdomain-book-tools`,
  `pdomain-ops`, or CLI flags and caller-side glue.

## Rejected directions

- Do not keep completed execution plans in `docs/archive/` when current code,
  tests, architecture, usage, or decisions already preserve their durable truth.
- Do not recreate one `docs/issues/` file per former GitHub chore number; the
  roadmap is the backlog for that class of work.

## Blocked (waiting on)

- Safe checkpoint loading remains blocked on upstream compatibility work
  (roadmap Blocked section; former GH #15).

## Open issues

Governed evidence-bearing reports under [`docs/issues/`](../issues/README.md):

- *None yet.*

Standing backlog items are listed only in [`docs/roadmap.md`](../roadmap.md).

## Needs owner decision

- Decide whether `docs/decisions/type-suppressions.md` should remain a separate
  decision record or be consolidated into
  [`docs/conventions/lint-deviations.md`](../conventions/lint-deviations.md).

## Legacy-unverified sweep

- **Still active:** layout-aware OCR architecture, roadmap, and
  type-suppression rationale.
- **Implemented and retired:** the two implementation plans and test-suite
  design spec were promoted into architecture and deleted.
- **Retired and removed:** all three former archive plans, both completed
  research records, and the superseded local-upgrade runbook. Durable behavior,
  provenance, and residual intent now live in architecture, decisions, and this
  intent map.
- **Retired and removed:** the local writing-style process doc and parked
  predictor batch-size spec. The writing-docs plugin owns readability.
  Repository-specific link and command rules remain in `CONVENTIONS.md`.
  Upstream predictor defaults and current architecture preserve shipped
  behavior. Deferred intent preserves every unresolved tuning question.
