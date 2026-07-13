---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: context
---

# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** checking durable repository decisions or documentation tombstones.
- **Search terms:** decisions, rationale, retirement, tombstone, docgraph.

### 2026-07-13 — Adopt docgraph governance

- **Context:** The repository used a folder taxonomy without declared lifecycle metadata.
- **Decision:** Govern repository Markdown with docgraph, authored context, and explicit lifecycle statuses.
- **Rationale:** Retrieval must distinguish current truth from completed or superseded work.
- **Evidence:** `docgraph.toml`, `DOCGRAPH.md`, and the initial 24-node index.
- **Remaining work:** Complete promotion and retirement of the implemented live plans and spec.

### 2026-07-13 — Retired: Basedpyright Baseline Cleanup Implementation Plan

- **Old path:** `docs/archive/plans/2026-05-23-basedpyright-baseline-cleanup.md`
- **Outcome:** implemented
- **Superseded by:** `docs/conventions/lint-deviations.md` and current type-check configuration
- **Removal commit:** This docgraph migration commit.
- **Rationale kept:** Commit `064a87f`, `.basedpyright/baseline.json`, and the current lint-deviation records preserve the result.
- **Remaining work:** Reconcile the two suppression records.

### 2026-07-13 — Retired: `--no-illustration-placeholders` flag plan

- **Old path:** `docs/archive/plans/no-illustration-placeholders.md`
- **Outcome:** implemented
- **Superseded by:** `docs/usage/cli-usage.md`
- **Removal commit:** This docgraph migration commit.
- **Rationale kept:** CLI policy code, parsing and wiring tests, and the no-silent-drops rule preserve the behavior.
- **Remaining work:** none

### 2026-07-13 — Retired: dev-local-aware `upgrade-deps` plan

- **Old path:** `docs/archive/plans/upgrade-deps-local.md`
- **Outcome:** superseded
- **Superseded by:** `DEVELOPMENT.md`, `CLAUDE.md`, and `scripts/local-upgrade-deps.sh`
- **Removal commit:** This docgraph migration commit.
- **Rationale kept:** Commit `4c175a8` and the current local-dev workflow preserve the durable behavior.
- **Remaining work:** Remove the retired `docs/runbooks/dev-local-upgrade-flow.md` after preserving any unique provenance.
