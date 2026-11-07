---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-07
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
- Keep the GitHub Issues tracker empty; plan in-repo via roadmap and
  [`docs/issues/`](../issues/README.md). See
  [`docs/decisions/2026-07-19-github-issues-cutover.md`](../decisions/2026-07-19-github-issues-cutover.md).

## Deferred work

- Constrain executable model checkpoints with a safer format or loading mode
  when upstream compatibility permits. The default revision pin shipped.
- Replace mutable pre-commit revision tags with immutable commit pins if the
  owner chooses SHAs (former GH #45).
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
- Do not re-open the PATH-based `nvidia-smi` GPU probe as a defect (former GH
  #36); the accepted bounded PATH probe stands in decisions and lint-deviations.

## Blocked (waiting on)

- Safe checkpoint loading remains blocked on upstream compatibility work
  (roadmap Blocked section; former GH #15).

## Open issues

Governed reports under [`docs/issues/`](../issues/README.md) (GitHub tracker empty):

- [Model revision pin + safe load](../issues/2026-07-19-gh-15-model-revision-pin-and-safe-load.md) (former GH #15, Blocked)
- [Pre-commit immutable pins](../issues/2026-07-19-gh-45-pre-commit-immutable-pins.md) (former GH #45, needs decision)
- [Dep-refresh leftovers](../issues/2026-08-08-dep-refresh-cannot-auto-land.md) (needs decision)
- [Deferred normalize-output](../issues/2026-07-19-normalize-output-flag-deferred.md) (Later)

Standing priority order remains in [`docs/roadmap.md`](../roadmap.md).

## Needs owner decision

- Choose tag or commit-SHA revisions for pre-commit hooks (former GH #45).
- Close dep-refresh pull requests #58 to #66 and delete their `dep-refresh/*`
  branches on origin. Commit `7041179` removed the workflow on 2026-09-13.
- Six implemented specs cannot be retired by the doc-retirer rules because they
  have no `## Adversarial Review` section. They are marked `implemented` and
  point at their architecture docs. Decide whether to add a review record and
  retire them, or keep them:
  [rotation](../specs/2026-07-21-rotation-propagation-design.md),
  [word preservation](../specs/2026-07-21-default-layout-word-preservation-design.md),
  [installer trust](../specs/2026-07-21-installer-trust-design.md),
  [image limits](../specs/2026-07-21-image-resource-limits-design.md),
  [update-check diagnostics](../specs/2026-07-21-update-check-diagnostics-design.md),
  [output transaction](../specs/2026-07-21-output-transaction-design.md).

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
