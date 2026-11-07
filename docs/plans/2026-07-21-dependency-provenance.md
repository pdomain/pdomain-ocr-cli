---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: plan
---

# Dependency Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Publish bounded dependencies and make build and hook inputs immutable.

## Architecture

`pyproject.toml` remains the package metadata authority. Static tests enforce bounds and exact pins. Hook revisions are refreshed locally with `pre-commit autoupdate --freeze`.

## Tech Stack

Python packaging, uv, Hatchling, pre-commit, pytest

## Global Constraints

Never silently drop OCR words. Keep reusable logic in `pdomain-book-tools`.
Run `make ci AI=1` before committing. Docs, code and tests change together.
GitHub runs no workflows for this repository, so every check here is local.

**Spec:** [dependency provenance design](../specs/2026-07-21-dependency-provenance-design.md)

---

## Status

Both tasks shipped. Task 1, package bounds and exact build-backend pins,
shipped in `7b0f4f7` (v0.9.1); see
[cli-orchestration.md](../architecture/cli-orchestration.md#dependency-bounds).
Task 2 shipped on 2026-11-07, after the owner chose commit SHAs for former
GH #45. It differs from the original steps:

- Each hook was frozen at the version it already used, not bumped.
- The pin check is a local `pygrep` hook, `require-frozen-hook-revs`, not a
  pytest. The same hook went to every pdomain repository, including ones
  without Python tests.
- The third-party `pre-commit-update` hook was removed, and `make update-hooks`
  now runs `pre-commit autoupdate --freeze`.

The remaining follow-up is the requirement-parsing test listed in
[intent-map.md](../context/intent-map.md#spec-review-follow-ups-2026-11-07).
