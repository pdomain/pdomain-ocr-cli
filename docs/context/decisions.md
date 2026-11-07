---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-07
Kind: context
---

# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** checking durable repository decisions or documentation tombstones.
- **Search terms:** decisions, rationale, retirement, tombstone, docgraph.

### 2026-11-07 — Remaining-work docs pass after v0.9.0 and v0.9.1

- **Context:** v0.9.0 (`c325c13`) and v0.9.1 (`7af73fc`) shipped most of the
  roadmap, but the roadmap, issue index, plans, and architecture still
  described that work as open.
- **Decision:** Promote shipped behavior into architecture with Evidence
  blocks. Retire six implemented plans and nine resolved issues. Mark six
  implemented specs `implemented` and keep them, because they lack the
  `## Adversarial Review` section that spec retirement requires. Replace the
  roadmap narrative with a one-line-per-item remaining-work list.
- **Rationale:** Open-work docs must not list finished work, and present-tense
  architecture must match the code.
- **Evidence:** Code and tests at `7af73fc`; commits `c325c13`, `23f263e`,
  `b9e1f02`, `7b0f4f7`, `7af73fc`, and `7041179`. The v0.9.1 preflight
  `make ci-slow` passed with 468 tests.
- **Remaining work:** See `docs/roadmap.md`.

### 2026-11-07 Retired: Rotation propagation implementation plan

- Old path: `docs/plans/2026-07-21-rotation-propagation.md`
- Outcome: implemented in `c325c13`
- Superseded by: `docs/architecture/layout-aware-ocr.md`
- Removal commit: (fill after commit)
- Rationale kept: The plan proposed a new upstream `PageResult.rotation_degrees` field. The shipped code instead keeps the angle from `from_image_ocr_via_doctr`'s `(document, rotation)` return. The architecture doc records the shipped design.
- Remaining work: none

### 2026-11-07 Retired: Default-layout word-preservation plan

- Old path: `docs/plans/2026-07-21-default-layout-word-preservation.md`
- Outcome: implemented in `c325c13`
- Superseded by: `docs/architecture/test-suite.md`
- Removal commit: (fill after commit)
- Rationale kept: Test scaffolding only; the architecture doc names the shipped test.
- Remaining work: none

### 2026-11-07 Retired: Installer trust implementation plan

- Old path: `docs/plans/2026-07-21-installer-trust.md`
- Outcome: implemented in `23f263e`
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: First-index binding and digest rules are in Trust and network boundaries.
- Remaining work: none

### 2026-11-07 Retired: Image resource limits implementation plan

- Old path: `docs/plans/2026-07-21-image-resource-limits.md`
- Outcome: implemented in `7af73fc`
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: Limits are in Execution invariants and `docs/usage/cli-usage.md`.
- Remaining work: none

### 2026-11-07 Retired: Update-check diagnostics implementation plan

- Old path: `docs/plans/2026-07-21-update-check-diagnostics.md`
- Outcome: implemented in `b9e1f02`
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: Diagnostic format is in Trust and network boundaries.
- Remaining work: none

### 2026-11-07 Retired: Output transaction implementation plan

- Old path: `docs/plans/2026-07-21-output-transaction.md`
- Outcome: implemented in `7af73fc`
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: Rollback rules are in Execution invariants.
- Remaining work: none

### 2026-11-07 Retired: Layout detection and illustration crops use the unrotated page image (former GH #18)

- Old path: `docs/issues/2026-07-19-gh-18-layout-crops-ignore-rotation.md`
- Outcome: resolved in `c325c13`; code and tests prove the fix
- Superseded by: `docs/architecture/layout-aware-ocr.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/layout-aware-ocr.md`
- Remaining work: none

### 2026-11-07 Retired: No multiset default-layout word-preservation test (former GH #41)

- Old path: `docs/issues/2026-07-19-gh-41-default-layout-word-preservation-test.md`
- Outcome: resolved in `c325c13`; code and tests prove the fix
- Superseded by: `docs/architecture/test-suite.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/test-suite.md`
- Remaining work: none

### 2026-11-07 Retired: Installers do not pin pdomain packages against dependency confusion (former GH #24)

- Old path: `docs/issues/2026-07-19-gh-24-installer-dependency-confusion.md`
- Outcome: resolved in `23f263e`; code and tests prove the fix
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/cli-orchestration.md`
- Remaining work: none

### 2026-11-07 Retired: Installers do not verify downloaded release wheel integrity (former GH #30)

- Old path: `docs/issues/2026-07-19-gh-30-installer-artifact-verification.md`
- Outcome: resolved in `23f263e`; code and tests prove the fix
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/cli-orchestration.md`
- Remaining work: none

### 2026-11-07 Retired: Runtime dependency ranges have no upper bounds (former GH #31)

- Old path: `docs/issues/2026-07-19-gh-31-runtime-dep-upper-bounds.md`
- Outcome: resolved in `7b0f4f7`; code and tests prove the fix
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/cli-orchestration.md`
- Remaining work: none

### 2026-11-07 Retired: Build backend requirements are unpinned (former GH #50)

- Old path: `docs/issues/2026-07-19-gh-50-pin-build-backends.md`
- Outcome: resolved in `7b0f4f7`; code and tests prove the fix
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/cli-orchestration.md`
- Remaining work: none

### 2026-11-07 Retired: No resource limits for untrusted image inputs (former GH #38)

- Old path: `docs/issues/2026-07-19-gh-38-untrusted-image-resource-limits.md`
- Outcome: resolved in `7af73fc`; code and tests prove the fix
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/cli-orchestration.md`
- Remaining work: none

### 2026-11-07 Retired: Update-check failures are swallowed without diagnostics (former GH #35)

- Old path: `docs/issues/2026-07-19-gh-35-update-check-diagnostics.md`
- Outcome: resolved in `b9e1f02`; code and tests prove the fix
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/cli-orchestration.md`
- Remaining work: none

### 2026-11-07 Retired: No rollback of sidecars if final .txt write fails (former GH #22)

- Old path: `docs/issues/2026-07-19-gh-22-sidecar-rollback-on-txt-failure.md`
- Outcome: resolved in `7af73fc`; code and tests prove the fix
- Superseded by: `docs/architecture/cli-orchestration.md`
- Removal commit: (fill after commit)
- Rationale kept: shipped behavior and its Evidence block in `docs/architecture/cli-orchestration.md`
- Remaining work: none

### 2026-07-19 — Roadmap completed-item reconcile

- **Context:** After GitHub issue deletion, `docs/roadmap.md` still listed many
  former issues as open though code, tests, and architecture already shipped
  them (or accepted a superseding design).
- **Decision:** Re-evidence every open checkbox against the tree; move
  implemented items to Shipped; correct architecture overclaims (rotation /
  layout, write-last vs full rollback, word-preservation coverage gap); fix
  usage image suffixes and DEVELOPMENT release branch; close former GH #36 as
  won't-fix per the PATH-probe ADR.
- **Rationale:** A standing roadmap must not re-open finished work. Present-tense
  architecture must match code, including known gaps.
- **Evidence:** Analyzer classification of former GH #15–#51 vs workflows,
  installers, `_artifacts.py`, `_policy.py`, tests, and arch docs; commits on
  this pass.
- **Remaining work:** True open set on the roadmap (Now/Next/Blocked) only.

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

### 2026-07-19 — Retired: repository-local writing-style process doc

- **Old path:** `docs/process/writing-style.md`
- **Outcome:** deleted (superseded by writing-docs plugin + `CONVENTIONS.md`)
- **Superseded by:** `writing-docs:write-readably` /
  `writing-docs:edit-for-readability`; repository-specific link and command
  rules in `CONVENTIONS.md`
- **Removal commit:** `ac05397`
- **Rationale kept:** Decision “2026-07-15 — Remove repository-local archives
  and writing rules” already authorized removal; the file had been re-scaffolded
  as `status: active` and was still indexed. Intent-map already listed it as
  retired and removed.
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
