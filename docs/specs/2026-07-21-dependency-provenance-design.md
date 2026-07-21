---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: spec
---

# Bound runtime dependencies and pin build and hook tools

Release inputs will use tested compatibility ranges and immutable tool revisions.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** changing Python metadata, build tools, or pre-commit updates
- **Search terms:** upper bounds, build backend pins, pre-commit SHA, former GH 31, former GH 45, former GH 50
- **Relates to:** [runtime bounds](../issues/2026-07-19-gh-31-runtime-dep-upper-bounds.md), [hook pins](../issues/2026-07-19-gh-45-pre-commit-immutable-pins.md), [build pins](../issues/2026-07-19-gh-50-pin-build-backends.md)

**Implementation plan:** [dependency provenance plan](../plans/2026-07-21-dependency-provenance.md)

## Adopted design

Runtime requirements will use the next incompatible major version as an exclusive upper bound. Related GPU requirements use the same policy. The lockfile records the tested solution but does not replace published metadata bounds.

`hatchling` and `hatch-vcs` will use exact versions from the current lock. Every remote pre-commit `rev` will use a 40-character commit SHA. The weekly refresh workflow will update hooks with `pre-commit autoupdate --freeze` so refreshes preserve immutable revisions.

## Acceptance criteria

- Every direct runtime and GPU requirement has a justified exclusive cap.
- Build-system requirements are exact pins.
- Remote hook revisions are full SHAs.
- Automated refresh keeps full SHAs.
- Metadata, lock, build, wheel smoke, and full CI pass.
