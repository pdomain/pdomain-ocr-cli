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

- Guard the upstream safe checkpoint loader with a test in this repository
  (former GH #15 part 2). The default revision pin shipped.
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

## Spec review follow-ups (2026-11-07)

Each spec's `## Adversarial Review` section has the evidence. Highest value
first:

- Pin the default OCR model to the commit SHA behind `v0.7`, and warn on
  branch names such as `main` ([model provenance](../specs/2026-07-21-model-provenance-design.md)).
- Make `tests/test_dependency_metadata.py` parse requirements, so a marker
  cannot hide an unbounded one ([dependency provenance](../specs/2026-07-21-dependency-provenance-design.md)).
- Close the output-transaction gaps: backup bookkeeping before the rename,
  reported backup-cleanup errors, and a sweep of stale `.bak`/`.stage` files
  ([output transaction](../specs/2026-07-21-output-transaction-design.md)).
- Report the three update-check failures that stay silent in debug mode
  ([update-check diagnostics](../specs/2026-07-21-update-check-diagnostics-design.md)).
- Fall back to the REST API when the `gh` path has no digest, force TLS 1.2
  on Windows PowerShell 5.1, and stop overwriting `TMPDIR` in `install.sh`
  ([installer trust](../specs/2026-07-21-installer-trust-design.md)).
- Give the batch OCR path an explicit rotation angle, and test 180° and 270°
  crops on real pixels ([rotation](../specs/2026-07-21-rotation-propagation-design.md)).
- Add a slow real-model word-preservation test with `--validate-reorg`, plus
  overlap, caption and two-column cases ([word preservation](../specs/2026-07-21-default-layout-word-preservation-design.md)).
- Bound decoded memory per chunk and re-check file size after reading
  ([image limits](../specs/2026-07-21-image-resource-limits-design.md)).
- Settle the normalize-output contract before upstream work starts
  ([normalize output](../specs/2026-07-21-normalize-output-design.md)).

## Rejected directions

- Do not keep completed execution plans in `docs/archive/` when current code,
  tests, architecture, usage, or decisions already preserve their durable truth.
- Do not recreate one `docs/issues/` file per former GitHub chore number; the
  roadmap is the backlog for that class of work.
- Do not re-open the PATH-based `nvidia-smi` GPU probe as a defect (former GH
  #36); the accepted bounded PATH probe stands in decisions and lint-deviations.

## Blocked (waiting on)

- Output normalization waits on a shared `normalize_text` in
  `pdomain-book-tools`; version 0.30.1 has none.

## Open issues

Governed reports under [`docs/issues/`](../issues/README.md) (GitHub tracker empty):

- [Model revision pin + safe load](../issues/2026-07-19-gh-15-model-revision-pin-and-safe-load.md) (former GH #15, Next)
- [Pre-commit immutable pins](../issues/2026-07-19-gh-45-pre-commit-immutable-pins.md) (former GH #45, needs decision)
- [Deferred normalize-output](../issues/2026-07-19-normalize-output-flag-deferred.md) (Later)

Standing priority order remains in [`docs/roadmap.md`](../roadmap.md).

## Needs owner decision

- Choose tag or commit-SHA revisions for pre-commit hooks (former GH #45). The
  2026-11-07 review recommends SHAs with `pre-commit autoupdate --freeze`, and
  removing the third-party `pre-commit-update` hook.
- Name the `--normalize-output` mode: `typographic` in the spec and plan, `ascii`
  in the issue and usage doc. The review favors `ascii`.
- Six implemented specs now have review records, so the doc-retirer rules allow
  retiring them. Each was implemented with deviations, and the open deviations
  are listed under the spec review follow-ups above. Decide whether to retire
  them now or keep them until those follow-ups land:
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
