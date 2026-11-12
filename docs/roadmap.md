---
kind: plan
status: active
owner: CT
created: 2026-05-19
last_verified: 2026-11-12
disposition: Standing roadmap for CLI-owned work.
---

<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# pdomain-ocr-cli Roadmap

## Agent Index

- **Kind:** plan
- **Status:** active
- **Read when:** deciding what to work on next in `pdomain-ocr-cli`.
- **Search terms:** roadmap, backlog, now next later, open priorities, shared installer, text normalization, batch rotation
- **Last verified:** 2026-11-12

The next change is to delete `pdomain_ocr_cli/_text_normalize.py` and call
`pdomain_book_contracts.text.text_normalize` instead.

This is the only backlog for work this repository owns.

Shipped behavior is in the architecture docs.

One line here is one open item.

`former GH #NNN` tags are provenance. They record where an item came from.
They are not live tracker links.

The GitHub Issues tracker stays empty. See
[`docs/decisions/2026-07-19-github-issues-cutover.md`](decisions/2026-07-19-github-issues-cutover.md).

## What this repository owns

`pdomain-ocr` owns flags, defaults, help, batching, artifact writes, the
release installers, and the local release that creates the GitHub Release.

OCR, layout, the rotation angle, and checkpoint loading stay in
`pdomain-book-tools`.

Curly-quote and em-dash helpers already live in `pdomain-book-contracts`.

The pip index stays in `pdomain-index-pip`.

## Goal

Keep one list of open work this repository owns.

Shipped behavior stays in the architecture docs.

A library change stays in that library's roadmap.

The line here covers only the flag, the help text, the default, and the
caller-side glue.

## Architecture

The command wraps `pdomain-book-tools` for OCR and layout.

It uses `pdomain-ops` for suite plumbing that is not on the OCR path.

[CLI orchestration](architecture/cli-orchestration.md) documents the
boundary, the image limits, the installers, and the release flow.

## Tech Stack

Python 3.11 through 3.13.

Hatchling `1.33.0` and hatch-vcs `0.5.0` build the package.

Runtime dependencies are `pdomain-book-tools==0.30.1`,
`pdomain-book-contracts`, `pdomain-ops`, `huggingface_hub`, and `pillow`.

Development uses `uv`, pytest, Ruff, and basedpyright.

## Global Constraints

Never silently drop OCR words.

Output options may change a word's role or suppress a placeholder block.

Caption text and OCR text stay unless the experimental drop flag is on.

Run `make ci AI=1` before committing.

Where a feature is a thin pass-through, the library work is tracked in
`pdomain-book-tools/docs/plans/roadmap.md`.

## Remaining work

- **Next:** delete `pdomain_ocr_cli/_text_normalize.py` and call
  `pdomain_book_contracts.text.text_normalize` instead.

  The contracts module was added so this CLI would not keep its own copy.

  The copy is still here, and the two implementations match. See
  [CLI orchestration](architecture/cli-orchestration.md#repository-boundary).
- **Blocked:** pass the batch OCR path the rotation angle that
  `pdomain-book-tools` chooses.

  Version 0.30.1 picks an angle and discards it.

  This CLI must not infer the angle again.

  Until the library reports it, the batch path uses the upright buffer the
  library stores. See
  [layout-aware OCR](architecture/layout-aware-ocr.md#page-rotation).
- **Later:** `--normalize-output` for long-s and ligatures, after a shared
  function exists.

  Do not add a private glyph map.

  Decision D-025 in `pdomain-ocr-labeler-spa` named
  `pdomain_book_tools.text.normalize` on 2026-05-06. That module has never
  existed.

  On 2026-09-18 the labeler removed its probe and does not offer the
  feature.

  Quote and dash cleanup has since landed in `pdomain-book-contracts`.

  That package is the better home for a glyph map, because it does not
  pull in the imaging stack.

  The mode name is still open. The usage page uses `ascii`. The spec uses
  `typographic`.

  The review favors `ascii`.

  One glyph may need to become several characters (`ﬁ` to `fi`).

  Unmapped glyphs must pass through.

  JSON output is not in the proposal.

  `pdomain-book-tools` 0.30.1 has neither function.

  [Issue](issues/2026-07-19-normalize-output-flag-deferred.md),
  [spec](specs/2026-07-21-normalize-output-design.md),
  [plan](plans/2026-07-21-normalize-output.md).
- **Later:** benchmark predictor-internal batching against `--batch-pages`.

  Decide whether `det_bs` and `reco_bs` overrides belong in
  `pdomain-book-tools` or as flags here.

  The library defaults are `det_bs=2` and `reco_bs=128`. This CLI does not
  expose them.
- **Later:** split the large happy-path and error-path test modules when a
  split does not copy fixtures or weaken the oracles.

Low findings from the 2026-11-07 spec reviews that were not in the follow-up
list are not scheduled.

Current behavior from those reviews is in the architecture docs.

The retired specs remain in git history.

## Consider building elsewhere

One shared installer is worth a separate repository.

`install.sh` and `install.ps1` are copied in this repo,
`pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`,
`pdomain-prep-for-pgdp`, and `pdomain-ocr-simple-gui`.

The trust policy hardened here will drift across those copies.

That policy covers first-index resolution, the wheel digest, TLS 1.2, and
leaving `TMPDIR` alone.

A small script repository should own that policy.

Each app would pass its package name and release asset.

`pdomain-ops` is a poor home for shell installers, because it is a Python
library imported by the SPA backends.

Do not start a repository for any of these:

- Long-s and ligature normalization. Put it in `pdomain-book-contracts`,
  next to the quote and dash helpers, once the contract above is settled.
- Image admission for every caller. This CLI caps bytes and pixels because
  it sees the file before decode.

  `pdomain-book-tools` already has open work for strict image validation.
  Extend that. Do not add a third library.
- Training, synthetic pages, labeling, the trainer UI, or the simple GUI.
  Those are `pdomain-ocr-training`, `pdomain-ocr-synth`,
  `pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, and
  `pdomain-ocr-simple-gui`.
- Model weights. They live in the Hugging Face repo
  `pdomain/pdomain-ocr-models`.
- The pip index. `pdomain-index-pip` publishes it.
- A second update service. `pdomain-ops` already checks updates for the
  suite.

  Leave this CLI's startup notice here unless another command needs the
  same notice. That notice is a GitHub-tag check for the installed
  command.

## Shipped

Current behavior, with evidence, lives in these docs:

- Rotation-aligned layout and crops, and the word-preservation tests:
  [layout-aware OCR](architecture/layout-aware-ocr.md),
  [test suite](architecture/test-suite.md).
- Installer index and digest checks, image limits, output rollback, the
  pinned default model, update-check diagnostics, dependency bounds, and
  the local release flow:
  [CLI orchestration](architecture/cli-orchestration.md).
- Retirement records: [decisions](context/decisions.md).

## Owner decisions still open

- The `--normalize-output` mode name. The usage page and the review use
  `ascii`. The spec and plan use `typographic`.
- Whether the glyph map belongs in `pdomain-book-contracts`, as this
  roadmap recommends, or in `pdomain-book-tools`, as D-025 and the spec say.
- Whether to build the shared installer repository above.
- Whether
  [`docs/decisions/type-suppressions.md`](decisions/type-suppressions.md)
  stays a decision record beside the lint inventory in
  [`docs/conventions/lint-deviations.md`](conventions/lint-deviations.md).
