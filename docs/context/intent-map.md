---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-10
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

Each spec's `## Adversarial Review` section has the evidence. These follow-ups
landed on branch `fix/spec-review-followups`, which is not on master yet: the
commit-pinned default model and branch-name warning, requirement parsing in the
bounds test, the output-transaction gaps, the three silent update-check
failures, the installer digest fallback and TLS 1.2 and `TMPDIR` fixes, 180° and
270° crop tests on real pixels, the slow real-model word-preservation test with
its overlap, caption and two-column cases, and the chunk pixel limit with the
post-read size check. Two remain:

- Give the batch OCR path an explicit rotation angle
  ([rotation](../specs/2026-07-21-rotation-propagation-design.md)). See Blocked.
- Settle the normalize-output contract before upstream work starts
  ([normalize output](../specs/2026-07-21-normalize-output-design.md)). Deferred
  with the flag.

Findings in those review sections that were not on this list, mostly low
severity, stay recorded there and are not scheduled.

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
- An explicit rotation angle on the batch OCR path waits on
  `pdomain-book-tools`. In version 0.30.1 and on its master at `f1f0ecb`,
  `Document.from_images_ocr_via_doctr` picks an angle and discards it, and the
  spec rules out inferring it again in the CLI. Until then
  `tests/test_upright_layout.py` guards the upright buffer the CLI relies on.

## Open issues

Governed reports under [`docs/issues/`](../issues/README.md) (GitHub tracker empty):

- [Deferred normalize-output](../issues/2026-07-19-normalize-output-flag-deferred.md) (Later)

Standing priority order remains in [`docs/roadmap.md`](../roadmap.md).

## Needs owner decision

- Name the `--normalize-output` mode: `typographic` in the spec and plan, `ascii`
  in the issue and usage doc. The review favors `ascii`.
- Six implemented specs now have review records, so the doc-retirer rules allow
  retiring them. Each was implemented with deviations. The listed follow-ups
  are on `fix/spec-review-followups`, except the batch rotation angle. Decide
  whether to retire them once that branch lands or keep them for the findings
  still open in their review sections:
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
