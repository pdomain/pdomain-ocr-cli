---
Status: draft
Owner: CT
Created: 2026-05-30
Last verified: 2026-07-13
Kind: spec
Supersedes: N/A
Promotes to: N/A
Disposition: Parked pending upstream design and owner review.
---

# Spec stub: tune DocTR predictor batch sizes for GPU throughput

**Status:** Parked — needs brainstorming + review. Not yet groomed into a plan.
**Date:** 2026-05-30
**Origin:** Salvaged from uncommitted WIP on the (now-removed) `feat/batch-pages`
worktree. The full WIP diff is preserved at
`docs/research/2026-05-30-batch-pages-wip.patch`.

## Why this exists

The `feat/batch-pages` branch held an early prototype of `--batch-pages`. That
feature **already shipped on main** via a more mature design (`_batch_plan.py`,
`_run_doctr_batch` → `pdomain_ops.gpu.doctr_batch.run_doctr_batch`, with a
`from_images_ocr_via_doctr` fallback and `test_batch_pages.py` /
`test_batch_plan.py`). The prototype's page-chunking is therefore superseded and
was discarded.

One idea in the prototype is **not** on main and is worth considering separately:
tuning the DocTR predictor's *internal* detection/recognition batch sizes,
independent of how many pages we chunk per call.

## The salvaged idea

main's `_load_predictor` builds the predictor with paths only:

```python
def _load_predictor(det_path: Path, reco_path: Path) -> object:
    return module.get_finetuned_torch_doctr_predictor(det_path, reco_path)
```

The WIP threaded explicit batch sizes into the predictor builder:

```python
def _load_predictor(det_path, reco_path, det_bs: int = 2, reco_bs: int = 128) -> object:
    return module.get_finetuned_torch_doctr_predictor(
        det_path, reco_path, det_bs=det_bs, reco_bs=reco_bs)
```

The premise: DocTR's detection and recognition predictors each have their own
internal batch size; raising them (esp. recognition, where many word crops per
page are cheap) can improve GPU utilisation beyond what page-chunking alone
achieves. `det_bs=2` / `reco_bs=128` were the prototype's untuned guesses.

## Open questions (for the brainstorm)

- Is predictor-internal batching actually a throughput win on top of the
  shipped `--batch-pages` page-chunking, or do they overlap?
- What are sane defaults, and should they be exposed as CLI flags or kept
  internal / device-derived?
- Memory ceiling: large `reco_bs` on a constrained GPU — clamp by VRAM?
- Does this belong in `pdomain-ocr-cli` at all, or in
  `pdomain_ops.gpu.doctr_batch` next to `run_doctr_batch`?

## Hard dependency (upstream)

Requires `pdomain-book-tools`'s
`pdomain_book_tools.ocr.doctr_support.get_finetuned_torch_doctr_predictor`
to accept `det_bs` / `reco_bs` keyword args. **It currently does not** — main's
Protocol types it as `Callable[[Path, Path], object]`. This upstream change
must land first, so any work here starts in `pdomain-book-tools`.

## Next step

Brainstorm the idea (is it worth it? where does it live?) before writing a plan
or filing issues. If rejected, delete this stub and the patch.

## Adversarial Review

- **Stage:** Design-stub review, 2026-07-13.
- **Source:** Docgraph migration red-team against current predictor calls,
  tests, roadmap, and authored context.
- **Accepted findings:** No detector or recognizer batch-size control has
  shipped, and the proposal still depends on upstream predictor ownership. The
  document remains a parked draft rather than implying that `--batch-pages`
  provides equivalent model-level batching.
- **Residual risks:** Device-specific defaults could cause GPU memory failures,
  the configuration boundary is undecided, and no benchmark defines the
  throughput or memory target. An owner must still choose whether to pursue or
  abandon the proposal.
