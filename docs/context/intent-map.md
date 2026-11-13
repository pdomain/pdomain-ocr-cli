---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-12
Kind: context
---

# Intent Map

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** choosing work, checking deferred intent, or reviewing migration decisions.
- **Search terms:** active bets, deferred work, rejected directions, owner decisions.

## Active bets

- Keep the standing CLI roadmap as the only backlog, including an explicit
  empty state when it has no open items:
  [`docs/roadmap.md`](../roadmap.md).
- Add long-s and ligature normalization only after the shared function exists.
  The roadmap names the open contract. The usage page is not a second plan.
- Keep the GitHub Issues tracker empty; plan in-repo via roadmap and
  [`docs/issues/`](../issues/README.md). See
  [`docs/decisions/2026-07-19-github-issues-cutover.md`](../decisions/2026-07-19-github-issues-cutover.md).

## Deferred work

The open lines live on the [roadmap](../roadmap.md). They are the batch
rotation angle, long-s normalization, predictor batch-size benchmarking, and
a later split of the large test modules. Quote and dash cleanup now calls
`pdomain-book-contracts`.

## Spec review follow-ups (2026-11-07)

The listed follow-ups landed on `fix/spec-review-followups` (`ddf6f3f` through
`211708f`), except the batch rotation angle, which stays blocked on
`pdomain-book-tools`. On 2026-11-12 the shipped specs and their plans were
retired into the architecture docs. Low findings that were not on that list
are not scheduled. Git history keeps the review text.

## Rejected directions

- Do not keep completed execution plans in `docs/archive/` when current code,
  tests, architecture, usage, or decisions already preserve their durable truth.
- Do not recreate one `docs/issues/` file per former GitHub chore number; the
  roadmap is the backlog for that class of work.
- Do not re-open the PATH-based `nvidia-smi` GPU probe as a defect (former GH
  #36); the accepted bounded PATH probe stands in decisions and lint-deviations.
- Do not start a new repository for glyph maps, image admission, training,
  model weights, or the pip index. Homes for each are on the roadmap.
- Do not keep a second copy of the curly-quote and em-dash helpers once the
  CLI calls `pdomain-book-contracts`.

## Blocked (waiting on)

- Long-s and ligature normalization waits on a shared function. Decision
  D-025 named `pdomain_book_tools.text.normalize`. That module has never
  existed, including in `pdomain-book-tools` 0.30.1. The labeler removed its
  probe on 2026-09-18. The roadmap recommends `pdomain-book-contracts`
  instead, next to the quote and dash helpers.
- An explicit rotation angle on the batch OCR path waits on
  `pdomain-book-tools`. In version 0.30.1 and on its master at `f1f0ecb`,
  `Document.from_images_ocr_via_doctr` picks an angle and discards it. The
  retired rotation spec rules out inferring it again in the CLI. Until then
  `tests/test_upright_layout.py` guards the upright buffer the CLI relies on.

## Open issues

Governed reports under [`docs/issues/`](../issues/README.md) (GitHub tracker empty):

- [Deferred normalize-output](../issues/2026-07-19-normalize-output-flag-deferred.md) (Later)

Standing priority order remains in [`docs/roadmap.md`](../roadmap.md).

## Needs owner decision

- Name the `--normalize-output` mode: `typographic` in the spec and plan,
  `ascii` in the issue and usage doc. The review favors `ascii`.
- Confirm the glyph-map home. This roadmap recommends
  `pdomain-book-contracts`. D-025 and the normalize spec still say
  `pdomain-book-tools`.
- Decide whether to build the shared installer repository named on the
  roadmap. Five sibling copies of `install.sh` / `install.ps1` exist today.
- Decide whether `docs/decisions/type-suppressions.md` should remain a
  separate decision record or be consolidated into
  [`docs/conventions/lint-deviations.md`](../conventions/lint-deviations.md).

## Legacy-unverified sweep

- **Still active:** layout-aware OCR architecture, roadmap, and
  type-suppression rationale.
- **Retired on 2026-11-12:** the six implemented design specs, plus the
  model-provenance and dependency-provenance specs and plans. Shipped
  behavior is in the architecture docs. The normalize-output spec, plan,
  and issue stay, because that flag is not built.
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
