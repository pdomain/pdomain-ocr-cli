---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-19
Kind: context
---

# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** checking durable repository decisions or documentation tombstones.
- **Search terms:** decisions, rationale, retirement, tombstone, docgraph.

### 2026-07-19 — GitHub Issues cutover closeout

- **Context:** The July 2026 cutover moved open work into the roadmap and
  deleted GitHub issues, but omitted runbook artifacts (digests, deletion
  journal, `docs/issues/` templates) and needed a clear empty-tracker policy.
- **Decision:** Install `docs/issues/`; keep the roadmap as standing backlog;
  permanently delete all remote issues; keep the Issues **feature enabled** with
  a **zero** issue count; recover closed bodies from git tombstone `9498407`.
- **Rationale:** Product planning belongs in governed docs. An empty enabled
  tracker avoids hiding the Issues UI while preventing a second backlog.
- **Evidence:**
  [`docs/decisions/2026-07-19-github-issues-cutover.md`](../decisions/2026-07-19-github-issues-cutover.md),
  commits `1c5046f` / `b2cfd49`, `9498407`, `165013d`, `a9169ca`.
- **Remaining work:** none for cutover; product items stay on the roadmap.

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

### 2026-07-13 — Retired the 2026-05-22 code and security review

- **Old path:** `docs/research/2026-05-22-pd-ocr-cli-code-security-review.md`
- **Outcome:** Many of its 37 findings drove current orchestration, artifact,
  model-warning, installer, workflow, and test architecture.
- **Superseded by:** `docs/architecture/cli-orchestration.md`,
  `docs/architecture/layout-aware-ocr.md`, `docs/architecture/test-suite.md`,
  current usage documentation, code, tests, and workflows.
- **Implementation direction:** Release verification moved to the pre-tag
  local gate. Model trust is warned rather than eliminated. Image resource
  limits and installer-side artifact verification remain deferred.
- **Evidence:** Commits `87f066a`, `bcf8807`, `a0c2054`, `0287e2c`, `4733780`,
  `1c3993c`, and `9e8b089`.
- **Remaining work:** Safe checkpoint loading, untrusted-image resource limits,
  and installer-side artifact verification remain in current intent.

### 2026-07-13 — Removed historical validation and local-upgrade runbook

- **Context:** Both files were retired but remained in live retrieval with
  point-in-time or superseded instructions.
- **Decision:** Delete the 2026-05-29 validation snapshot and the original
  dev-local upgrade runbook after preserving current behavior and provenance.
- **Rationale:** Current architecture, `DEVELOPMENT.md`, code, tests, and commit
  history are more accurate than the historical documents.
- **Evidence:** Validation commit `9e8b089`; local workflow commits `b84e0fe`
  and `4c175a8`; `docs/architecture/cli-orchestration.md`; current `Makefile`
  and `scripts/local-*.sh`.
- **Remaining work:** none

### 2026-07-13 — Retired: test-suite reorganization plan

- **Old path:** `docs/plans/2026-05-28-test-suite-reorganization.md`
- **Outcome:** implemented
- **Superseded by:** `docs/architecture/test-suite.md`
- **Removal commit:** This docgraph conformance migration commit.
- **Rationale kept:** Current suite structure, deviations, and evidence live in
  the replacement architecture.
- **Remaining work:** Further split the large happy-path and error-path tests
  without weakening their behavior oracles.

### 2026-07-13 — Retired: test-suite reorganization spec

- **Old path:** `docs/specs/2026-05-28-test-suite-reorganization-design.md`
- **Outcome:** implemented
- **Superseded by:** `docs/architecture/test-suite.md`
- **Removal commit:** This docgraph conformance migration commit.
- **Rationale kept:** The replacement records the post-implementation review,
  five implementation deviations, current behavior, and evidence.
- **Remaining work:** Further split the large happy-path and error-path tests.

### 2026-07-13 — Retired: CLI review-remediation plan

- **Old path:** `docs/plans/2026-05-29-pdomain-ocr-cli-review-remediation.md`
- **Outcome:** implemented
- **Superseded by:** `docs/architecture/cli-orchestration.md`
- **Removal commit:** This docgraph conformance migration commit.
- **Rationale kept:** Current seam ownership, invariants, release direction,
  and evidence live in the replacement architecture.
- **Remaining work:** none

### 2026-07-13 — Accepted bounded PATH and URL probes

- **Context:** The retired security review flagged PATH-resolved
  `nvidia-smi` and generic `urlopen` use.
- **Decision:** Keep both probes with narrow boundaries and inline lint
  rationale.
- **Rationale:** NVIDIA tools are intentionally discovered through `PATH`. The
  update check uses a hardcoded HTTPS endpoint and accepts no user-controlled
  scheme.
- **Evidence:** `pdomain_ocr_cli/_startup_notices.py`,
  `pdomain_ocr_cli/_update_check.py`, and
  `docs/conventions/lint-deviations.md`.
- **Remaining work:** none

### 2026-07-15 — Remove repository-local archives and writing rules

- **Context:** The archive tree contained only nine empty `.gitkeep` files. The
  local writing-style document's general readability guidance duplicated the
  installed writing-docs plugin. Its repository-specific rules belonged
  in `CONVENTIONS.md` instead.
- **Decision:** Remove `docs/archive/` and
  `docs/process/writing-style.md`. Route writing through
  `writing-docs:write-readably` and `writing-docs:edit-for-readability`.
- **Rationale:** Current architecture, decisions, authored context, and Git
  history preserve durable truth. One plugin-owned standard avoids competing
  copies.
- **Evidence:** Commits `e1a5f44`, `72c8ee2`, and `915189d`; `AGENTS.md`;
  `CONVENTIONS.md`.
- **Remaining work:** none

### 2026-07-15 — Retired predictor batch-size tuning stub

- **Old path:** `docs/specs/2026-05-30-predictor-batch-size-tuning.md`
- **Outcome:** retired as a standalone spec after its upstream API dependency
  shipped; tuning remains deferred intent.
- **Current behavior:** `docs/architecture/cli-orchestration.md` and
  `pdomain-book-tools` commit `5585d27`
- **Removal commit:** This docgraph migration commit.
- **Rationale kept:** The stub came from the discarded `feat/batch-pages` WIP.
  Its full diff remains at
  `docs/research/2026-05-30-batch-pages-wip.patch`, although page batching
  shipped through a different design. Upstream now owns predictor-internal defaults.
  The intent map preserves throughput overlap, default sizing, VRAM limits,
  API ownership, and CLI exposure as separate unresolved questions.
- **Remaining work:** Benchmark and choose ownership only if the roadmap
  prioritizes explicit tuning.
