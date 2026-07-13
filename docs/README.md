---
Status: active
Owner: CT
Created: 2026-05-19
Last verified: 2026-07-13
Kind: process
---

# docs/

How documentation is organized in this repo.

| Folder | Purpose | Use when |
| --- | --- | --- |
| `architecture/` | Durable reference — how the system works today. | Capturing current shape (modules, data flow, contracts, current-state diagrams). |
| `archive/` | Exceptional cold storage. | Durable rationale cannot be captured fully in architecture, decisions, or authored context. |
| `decisions/` | ADRs — dated, append-only "we chose X because Y." | Recording a specific design choice with context, alternatives, consequences. |
| `plans/` | Active execution — what order to make a spec real. | Sequencing work for an approved spec. |
| `process/` | Cross-cutting workflow conventions (verification rules, merge strategy, release process). | Capturing how the team works, not what the system does. |
| `research/` | Investigation in progress. Messy by design. | Exploring before committing to a design. |
| `runbooks/` | Operational reference — something is broken or being operated. | An on-call or ops task needs a recipe. |
| `specs/` | Aspirational, pre-implementation design. | Describing what to build, before code. |
| `templates/` | Issue, spec, plan, ADR boilerplate. | Adding a starter template for a new doc type. |
| `usage/` | Downstream reference — how to consume this app/tool/library. | A user or integrator needs to know how to use it. |

Empty folders are intentional and tracked via `.gitkeep`. Completed plans and
specs are promoted into architecture and retired through docgraph. Deletion
with a decision tombstone is the default; archive is a last resort.

Active docs map to GitHub issues — see this repo's issue tracker for status.
This layout follows the workspace documentation taxonomy and this repository's
[docgraph rules](../DOCGRAPH.md).
