---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
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

## Adopted design

The upstream library owns glyph mappings and idempotent normalization. After that API ships, the CLI will add `--normalize-output {none,typographic}` with `none` as the default. Normalization runs after text assembly and existing opt-in quote/dash transforms, immediately before the atomic text write.

No CLI-only glyph map will be created. Until the upstream symbol and version exist, implementation remains blocked and the plan's first task is the explicit gate.

## Acceptance criteria

- The upstream API is versioned, deterministic, and idempotent.
- Omitted flag and `none` preserve current output exactly.
- `typographic` delegates to the upstream function.
- Composition with existing quote and dash flags is tested.
