---
Status: active
Owner: CT
Created: 2026-05-19
Last verified: 2026-07-19
Kind: process
---

# docs/

This repo organizes documentation by its purpose and when contributors use it.

| Folder | Purpose | Use when |
| --- | --- | --- |
| `architecture/` | Durable reference — how the system works today. | Capturing current shape (modules, data flow, contracts, current-state diagrams). |
| `context/` | Authored current state, intent, and decision log. | Orienting before work or checking what is deferred. |
| `conventions/` | Repo-local conventions (lint inventory, style notes). | Checking how this repo deviates from defaults. |
| `decisions/` | ADRs — dated "we chose X because Y." | Recording a specific design choice with context and consequences. |
| `issues/` | Governed evidence-bearing bug and investigation reports. | Filing a durable defect record (not standing backlog). |
| `plans/` | Active execution — what order to make a spec real. | Sequencing work for an approved spec. |
| `process/` | Cross-cutting workflow conventions. | Capturing how the team works, not what the system does. |
| `research/` | Investigation in progress. Messy by design. | Exploring before committing to a design. |
| `runbooks/` | Operational reference — something is broken or being operated. | An on-call or ops task needs a recipe. |
| `specs/` | Aspirational, pre-implementation design. | Describing what to build, before code. |
| `templates/` | Spec, plan, ADR boilerplate. | Adding a starter template for a new doc type. |
| `usage/` | Downstream reference — how to consume this app/tool/library. | A user or integrator needs to know how to use it. |

Empty active folders are intentional and tracked via `.gitkeep`.

Completed plans and specs move into architecture and are retired through
docgraph. By default, they are deleted with a decision tombstone; Git
preserves history.

**Backlog and issues.** Standing CLI work lives in
[`roadmap.md`](roadmap.md). Evidence-bearing defects use
[`issues/`](issues/README.md). The GitHub Issues feature is **enabled** but the
remote tracker is kept **empty** (planning is in-repo); see
[`decisions/2026-07-19-github-issues-cutover.md`](decisions/2026-07-19-github-issues-cutover.md).
Cross-repo work may still use `ConcaveTrillion/ocr-container-meta`.

The layout follows the workspace documentation taxonomy and this repository's
[docgraph rules](../DOCGRAPH.md).
