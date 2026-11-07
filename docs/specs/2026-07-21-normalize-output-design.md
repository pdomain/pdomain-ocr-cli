---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Add output normalization only after the shared API stabilizes

The CLI will expose normalization as a default-off enum after `pdomain-book-tools` ships a stable shared function.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** upstream text normalization becomes available
- **Search terms:** normalize output, glyph map, upstream gate
- **Relates to:** [deferred issue](../issues/2026-07-19-normalize-output-flag-deferred.md)

**Implementation plan:** [normalize-output plan](../plans/2026-07-21-normalize-output.md)

## Status on 2026-11-07

Still blocked. `pdomain-book-tools` 0.30.1 has no `text_normalize.py` and no
`normalize_text`.

## Adopted design

The upstream library owns glyph mappings and idempotent normalization. After that API ships, the CLI will add `--normalize-output {none,typographic}` with `none` as the default. Normalization runs after text assembly and existing opt-in quote/dash transforms, immediately before the atomic text write.

No CLI-only glyph map will be created. Until the upstream symbol and version exist, implementation remains blocked and the plan's first task is the explicit gate.

## Acceptance criteria

- The upstream API is versioned, deterministic, and idempotent.
- Omitted flag and `none` preserve current output exactly.
- `typographic` delegates to the upstream function.
- Composition with existing quote and dash flags is tested.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** Waiting on upstream is reasonable, but the design cannot be built as written.

- High: the mode name differs across documents: `typographic` in this spec and the plan, `ascii` in the issue and usage doc. The stated purpose, mapping long-s and ligatures to ASCII, fits `ascii`. Owner decision.
- High: the transform's contract is undefined: whether it may map one character to several, delete characters, or pass unmapped glyphs through. The never-drop-words rule needs that contract and a token-preservation test. Follow-up.
- Medium: the plan tests reversed transform order, but this spec fixes the order. JSON output would not be normalized, which no document says. Follow-up.
- Medium: nothing tracks the upstream `normalize_text` work, and the documents disagree on its module path. `pdomain-book-tools` has a glyph-annotation vocabulary it could build on. The plan's gate checks the sibling checkout instead of the pinned release. Follow-up.
