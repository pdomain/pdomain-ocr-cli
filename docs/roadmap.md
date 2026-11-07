---
kind: plan
status: active
owner: CT
created: 2026-05-19
last_verified: 2026-11-07
disposition: Standing roadmap for CLI-owned work.
---

<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# pdomain-ocr-cli Roadmap

## Agent Index

- **Kind:** plan
- **Status:** active
- **Read when:** deciding what to work on next in `pdomain-ocr-cli`.
- **Search terms:** roadmap, backlog, now next later, open priorities, hardening, release, supply chain, security

This roadmap lists **open** CLI-owned work only, one line per item. Shipped
behavior lives in the architecture docs. `former GH #NNN` tags are provenance,
not live tracker links. The GitHub Issues tracker stays empty; see
[`docs/decisions/2026-07-19-github-issues-cutover.md`](decisions/2026-07-19-github-issues-cutover.md).

## Goal

Maintain the standing list of open priorities owned by `pdomain-ocr-cli`. Track
CLI flags, defaults, help, documentation, orchestration, and caller-side glue
here while routing reusable primitives upstream.

## Architecture

`pdomain-ocr` wraps `pdomain-book-tools` OCR and layout primitives and uses
`pdomain-ops` for operational support. Shared processing logic belongs
upstream; this repository owns the command and its integration behavior.

## Tech Stack

The CLI supports Python 3.11 through 3.13 and uses Hatchling and hatch-vcs. It
depends on `pdomain-book-tools`, `pdomain-ops`, and `huggingface_hub`, with
development and verification through `uv`, pytest, Ruff, and basedpyright.

## Global Constraints

**Never silently drop OCR words** — output options may change roles or suppress
placeholder blocks, but caption and OCR text must survive unless an explicitly
experimental drop is enabled. Keep reusable primitives upstream, and run
`make ci AI=1` before committing. Where a CLI feature is a thin pass-through to
a library knob, the library work is tracked in
`pdomain-book-tools/docs/plans/roadmap.md` and the CLI item here covers only the
surfacing (flag name, help text, defaults, docs) and any caller-side glue.

## Remaining work

- **Next:** fixes from the 2026-11-07 spec reviews, highest value first.
  [`docs/context/intent-map.md`](context/intent-map.md) (Spec review follow-ups)
- **Later:** `--normalize-output`, after `pdomain-book-tools` ships shared
  normalization and a glyph map.
  [`docs/issues/2026-07-19-normalize-output-flag-deferred.md`](issues/2026-07-19-normalize-output-flag-deferred.md),
  [`docs/plans/2026-07-21-normalize-output.md`](plans/2026-07-21-normalize-output.md)

## Shipped

Current behavior, with evidence, lives in these docs:

- Rotation-aligned layout and crops, and the default-layout word-preservation
  test: [`docs/architecture/layout-aware-ocr.md`](architecture/layout-aware-ocr.md),
  [`docs/architecture/test-suite.md`](architecture/test-suite.md).
- Installer index and digest checks, image limits, output rollback, the pinned
  default model, update-check diagnostics, dependency bounds, and the local
  release flow: [`docs/architecture/cli-orchestration.md`](architecture/cli-orchestration.md).
- Retirement records: [`docs/context/decisions.md`](context/decisions.md).
