---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Pin the default OCR model and enforce safe upstream loading

The CLI will pin its default OCR model to an immutable Hugging Face revision and verify that its upstream dependency keeps safe PyTorch loading enabled.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** implementing model provenance or safe-loading checks
- **Search terms:** model revision, weights_only, Hugging Face, former GH 15
- **Relates to:** [issue](../issues/2026-07-19-gh-15-model-revision-pin-and-safe-load.md)

**Implementation plan:** [model provenance plan](../plans/2026-07-21-model-provenance.md)

## Status on 2026-11-07

The default revision pin (`v0.7`) shipped in `7af73fc`. The upstream
safe-loading test has not been written. `pdomain-book-tools` 0.30.1 keeps the
loader in `pdomain_book_tools/ocr/doctr_support.py`.

## Adopted design

The default `--model-version` value will be the immutable revision already proven by the slow integration suite. Explicit user values remain supported and keep their existing warnings. The CLI will not duplicate deserialization logic owned by `pdomain-book-tools`.

The safe-load half becomes a dependency contract. A focused test will inspect the installed upstream loader and fail if its `torch.load` call no longer passes `weights_only=True`. This closes the stale upstream blocker while keeping ownership clear.

## Alternatives rejected

- A mutable tag remains reproducible only while the tag is not moved.
- Copying the loader into the CLI would split security ownership and drift from the library.
- Keeping the issue blocked ignores the safe loader already shipped in `pdomain-book-tools >=0.18.0`.

## Failure handling and compatibility

The default changes only when users omit `--model-version`. An explicit revision preserves current behavior. The tripwire reports the missing upstream safety property during tests, not at runtime.

## Acceptance criteria

- Default argument parsing returns the immutable revision used by integration tests.
- The mutable-default warning no longer appears for the default invocation.
- Explicit mutable revisions still produce the existing warning.
- A test proves the installed upstream loader requests `weights_only=True`.
- Fast tests and the slow model smoke test pass.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** Sound but unfinished.

- High: `v0.7` is a tag, and a Hugging Face tag can be moved, so it is not the immutable revision this spec promises. The architecture, usage and README text now say so. Pinning the default to the commit SHA behind `v0.7` is a follow-up.
- High: the planned guard, a source-string search for `weights_only=True`, also matches two docstrings, so it passes even if the real call changes. The plan's Task 2 now specifies a behavioral test instead.
- Medium: only an unset revision or `latest` warns; `main` and other branch names do not. The pin test does not cover them. Follow-up.
- Medium: the spec ignores the layout model. The default PP-DocLayout weights are safetensors pinned to a commit SHA upstream; a custom `--layout-checkpoint` is warn-only. Recorded here.
