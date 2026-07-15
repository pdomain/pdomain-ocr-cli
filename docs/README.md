---
Status: active
Owner: CT
Created: 2026-05-19
Last verified: 2026-07-15
Kind: process
---

# docs/

This repo organizes documentation by its purpose and when contributors use it.

| Folder | Purpose | Use when |
| --- | --- | --- |
| `architecture/` | Durable reference — how the system works today. | Capturing current shape (modules, data flow, contracts, current-state diagrams). |
| `decisions/` | ADRs — dated, append-only "we chose X because Y." | Recording a specific design choice with context, alternatives, consequences. |
| `plans/` | Active execution — what order to make a spec real. | Sequencing work for an approved spec. |
| `process/` | Cross-cutting workflow conventions (verification rules, merge strategy, release process). | Capturing how the team works, not what the system does. |
| `research/` | Investigation in progress. Messy by design. | Exploring before committing to a design. |
| `runbooks/` | Operational reference — something is broken or being operated. | An on-call or ops task needs a recipe. |
| `specs/` | Aspirational, pre-implementation design. | Describing what to build, before code. |
| `templates/` | Issue, spec, plan, ADR boilerplate. | Adding a starter template for a new doc type. |
| `usage/` | Downstream reference — how to consume this app/tool/library. | A user or integrator needs to know how to use it. |

Empty active folders are intentional and tracked via `.gitkeep`. Completed
plans and specs move into architecture and are retired through docgraph. By
default, they are deleted with a decision tombstone; Git preserves history.

Active docs map to GitHub issues. See this repo's issue tracker for their
status. The layout follows the workspace documentation taxonomy and this
repository's [docgraph rules](../DOCGRAPH.md).
