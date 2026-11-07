---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: plan
---

# Model Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Goal

Pin the default OCR model and guard the upstream safe-loading contract.

## Architecture

Argument parsing owns the immutable default. Model-security warnings continue to classify user overrides, while an AST scan of the installed package and a behavioral load test guard the upstream `weights_only=True` contract.

## Tech Stack

Python, argparse, pytest, pdomain-book-tools, uv

## Global Constraints

Never silently drop OCR words. Keep reusable logic in `pdomain-book-tools`.
Run `make ci AI=1` before committing. Docs, code and tests change together.
GitHub runs no workflows for this repository, so every check here is local.

**Spec:** [model provenance design](../specs/2026-07-21-model-provenance-design.md)

---

## Status

Both tasks shipped. Task 1, the `v0.7` default revision pin, shipped in
`7af73fc` (v0.9.1); see
[cli-orchestration.md](../architecture/cli-orchestration.md#trust-and-network-boundaries).
Task 2 added `tests/test_upstream_safe_load.py` on 2026-11-07. It has three
guards:

- An AST scan of every `.py` file in the installed `pdomain_book_tools`. It
  fails on any `torch.load` call, or `functools.partial` wrap of it, that lacks
  a literal `weights_only=True`, including aliased imports. Synthetic sources
  prove the scan accepts safe patterns and flags unsafe ones.
- A behavioral test: a pickled non-tensor object makes
  `get_finetuned_torch_doctr_predictor` raise `pickle.UnpicklingError`. With
  `weights_only=False` the same call raises `ValueError` instead, so the test
  fails.
- A test that the CLI calls the predictor without a `torch_load` override.

One review follow-up remains: pin the default to the commit SHA behind `v0.7`,
since an HF tag can be moved. It is listed in
[intent-map.md](../context/intent-map.md#spec-review-follow-ups-2026-11-07).
