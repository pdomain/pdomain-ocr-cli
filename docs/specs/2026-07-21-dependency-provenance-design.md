---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Bound runtime dependencies and pin build and hook tools

Release inputs will use tested compatibility ranges and immutable tool revisions.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** changing Python metadata, build tools, or pre-commit updates
- **Search terms:** upper bounds, build backend pins, pre-commit SHA, former GH 31, former GH 45, former GH 50
- **Relates to:** hook pins (former GH #45, retired 2026-11-07; see `docs/context/decisions.md`); runtime bounds and build pins shipped in `7b0f4f7`, see [cli-orchestration.md](../architecture/cli-orchestration.md#dependency-bounds)

**Implementation plan:** [dependency provenance plan](../plans/2026-07-21-dependency-provenance.md)

## Status on 2026-11-07

The bounds and exact build-backend pins shipped in `7b0f4f7`. The `[gpu]`
extra forwards to `pdomain-book-tools[gpu]==0.30.1`, which is exact. On
2026-11-07 the owner chose commit SHAs for hook revisions (former GH #45), and
they shipped then. The
weekly refresh workflow below no longer exists: commit `7041179` removed it on
2026-09-13, so hook refreshes are local.

## Adopted design

Runtime requirements will use the next incompatible major version as an exclusive upper bound. Related GPU requirements use the same policy. The lockfile records the tested solution but does not replace published metadata bounds.

`hatchling` and `hatch-vcs` will use exact versions from the current lock. Every remote pre-commit `rev` will use a 40-character commit SHA. The weekly refresh workflow will update hooks with `pre-commit autoupdate --freeze` so refreshes preserve immutable revisions.

## Acceptance criteria

- Every direct runtime and GPU requirement has a justified exclusive cap.
- Build-system requirements are exact pins.
- Remote hook revisions are full SHAs.
- Automated refresh keeps full SHAs.
- Metadata, lock, build, wheel smoke, and full CI pass.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** The shipped bounds are sound. The bounds test is weaker than its name, and the hook half of the design is stale.

- Medium: `_is_bounded` in `tests/test_dependency_metadata.py` is a substring check, so a marker such as `; python_version < '3.12'` makes an unbounded requirement pass. It checks only `dependencies` and the `gpu` extra. Follow-up: parse with `packaging`.
- Medium: `pillow>=11.0,<13` spans two majors and the `<1` caps on 0.x packages differ from the "next major" rule; no document records why. Follow-up.
- Medium: the design and acceptance criteria still rely on the removed weekly refresh workflow. Task 2 of the plan also needs to remove the third-party `pre-commit-update` hook and the `-@` in `make update-hooks`, and its test would need PyYAML or a regex. Follow-up.
- Recommendation for former GH #45: pin hook revisions to SHAs with `pre-commit autoupdate --freeze` and remove the `pre-commit-update` hook. The cost is small and it drops a tag-pinned hook that runs code.
