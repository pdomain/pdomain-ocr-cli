---
Status: active
Owner: CT
Created: 2026-05-19
Last verified: 2026-11-13
Kind: architecture
---

# Layout-aware OCR

`pdomain-ocr` runs document-layout detection on every page by default. The
detected regions feed `Page.reorganize_page()` as a hint, which:

- Detects high-confidence running titles and page numbers and role-labels
  them as page headers / footers. It weaves them back into the page at
  the boundaries (header band at the front, footer band at the back) so
  they don't bleed into body paragraphs. Words are preserved, not dropped.
- Tags tables and figures so downstream consumers can route them
  separately.
- Routes marginalia (sidenotes, abandoned regions) so they don't fold
  into the main reading flow — left-margin notes sort before the body,
  right-margin notes after. The words remain on the page.

By default, `pdomain-ocr` uses
[`PaddlePaddle/PP-DocLayout_plus-L`](https://huggingface.co/CT2534/PP-DocLayout_plus-L)
via `pdomain-book-tools`. It is Apache-2.0 licensed and downloads ~132 MB on
the first run.

Plain `--no-reorg` skips both `Page.reorganize_page()` and layout
detection. The only exception is `--extract-illustrations`, which still
requires layout regions to discover crop boxes.

## Flags

| Flag | Purpose |
|---|---|
| `--layout-model {none,contour,pp-doclayout-plus-l}` | Detector backend. `none` skips layout entirely. Default `pp-doclayout-plus-l`. |
| `--layout-checkpoint PATH_OR_REPO` | Use a fine-tuned PP-DocLayout checkpoint instead of the default weights. |
| `--layout-confidence THRESHOLD` | Minimum region confidence (0..1). Default 0.5. |
| `--extract-illustrations` | Crop figure/decoration/table regions into `i_<stem>_<n>.jpg`. Requires a layout model. |
| `--layout-debug` | Write per-step layout debug text alongside outputs. |
| `--layout-debug-dir DIR` | Where to put the debug text files (default: alongside each image's output). |

## Examples

```sh
# Skip layout detection entirely (faster; reorganize falls back to
# heuristics, which can fold captions into paragraphs and leave page
# numbers in the body text).
pdomain-ocr --layout-model none page.png

# Crop figure / decoration / table regions to i_<stem>_<n>.jpg files
# alongside the .txt output.
pdomain-ocr --extract-illustrations page.png

# Use a fine-tuned PP-DocLayout checkpoint (path or HF repo).
pdomain-ocr --layout-checkpoint ~/my-finetuned-layout/ page.png

# Lower confidence threshold for noisier scans.
pdomain-ocr --layout-confidence 0.3 page.png

# Per-step layout diagnostics for tuning the reorganize pipeline.
pdomain-ocr --layout-debug page.png
```

## Page rotation

The OCR layer can re-read a page at 90°, 180°, or 270° when upright
recognition confidence is low. It keeps the orientation with the best text.

Layout detection and illustration crops use that same upright image. The
single-image path stores the angle on the page as `ocr_rotation_degrees`.
The batch path does too. `run_doctr_batch` in `pdomain-ops` 0.12.2 copies the
degree list from `pdomain-book-tools` 0.31.0 onto each page. This CLI reads
`page.ocr_rotation_degrees` and does not call `from_images_ocr_via_doctr`
again. `upright_layout_source()` in `pdomain_ocr_cli/_pipeline.py` then picks
the layout source:

- If OCR stored an upright page buffer, layout and crops use it.
- If the angle is 0, layout reads the on-disk file and crops re-read it.
- Otherwise the decoded page array is rotated clockwise by the angle.

An angle other than 0, 90, 180, or 270 raises `ValueError`. Rotating anything
other than a decoded array raises `TypeError`. Crop boxes come from layout on the
same upright image; a box that runs past the edge is clamped, and an empty one
is skipped without a warning.

`Document.from_images_ocr_via_doctr` returns one clockwise degree per page.
The degree is 0 when that page stayed upright, and 0 on every page when
`auto_rotate` is false. The library still stores the upright page buffer.
`test_pinned_batch_ocr_returns_degrees_and_the_upright_image` fails if that
buffer or the degree list disappears. A page with no stored buffer and no
angle still uses the on-disk file, and no error is raised.

On the sideways fixture `tests/fixtures/rotated_page.png`, layout reports 0
regions at the default confidence of 0.5. That is correct. An offline run of
the cached PP-DocLayout-Plus-L weights on 2026-11-07 scored the upright
orientation's strongest box, a title, at 0.472. No test records that number.

## Performance notes

- The layout detector loads once at startup (auto-detects CUDA / MPS /
  CPU, mirroring the OCR predictor) and is reused for every page in the
  batch.
- Per-page layout inference is reported on the processing line:
  `layout: N regions (M ms)`.
- If a page returns `0 regions`, that's plausible for plain-text pages
  but can also indicate the confidence threshold filtered everything
  out — try `--layout-confidence 0.3` to verify.

## Artifact lifecycle

The CLI writes JSON sidecars, illustration crops, and the final `.txt` file
through one transaction: exclusive temporary files, then promotion together.
The text file is promoted last, after the successfully staged artifacts.
A crop source or encoding failure can warn and skip a crop while text still
commits. Presence of `<image>.txt` does not guarantee every requested crop.
If promotion fails, the transaction
removes the new files and restores the previous ones. Diagnostic snapshots and
the layout-debug report stay outside that transaction.

## Test coverage

The slow integration suite exercises the real OCR path, the default
`pp-doclayout-plus-l` layout path, layout-debug report writing, JSON
sidecars, corrupt-image handling, and the fixture corpus under
`tests/fixtures/`. Run it with:

```sh
just test-integration
just test-layout-integration
```

The fast suite's `tests/test_default_layout_word_preservation.py` mocks DocTR
and PP-DocLayout and checks that default layout reorganization keeps every OCR
word as a multiset. It also checks that
`--experimental-drop-layout-words` is the only switch that may drop figure
words.

## Related flags

These aren't layout-specific but interact with the reorganize step that
consumes layout output:

- `--no-reorg` — skip `reorganize_page()` entirely; emit raw OCR. Layout
  detection is skipped too unless `--extract-illustrations` needs it for
  crop discovery.
- `--save-reorganize-diagnostics` — with `--save-json`, also writes
  `<image>.pure-ocr.json` + `.txt` (literal OCR output) and
  `<image>.post-noise.json` + `.txt` (state after figure-noise removal,
  before reorg). Six files per page in total when combined with the
  regular `--save-json` post-reorganize pair. Old alias:
  `--save-pre-reorg-json`. Useful when comparing pipeline output to raw
  OCR or auditing the noise-drop step.
- `--validate-reorg` — warn (don't fail) if reorganize drops any words.
- _Always-on noise-drop warning_ — when reorganize drops figure-internal
  noise words, the CLI prints a warning to stderr identifying the page,
  the count, a sample of the dropped tokens, and a re-run hint pointing
  at `--save-json --save-reorganize-diagnostics` for the full diagnostic
  bundle. There is no flag to silence it.
- `--experimental-drop-layout-words` (alias: `--edl`) — gates BOTH
  figure-internal drop steps (Layout-2b and B2). Default OFF preserves
  every OCR word; the always-on warning's count is then 0 and the
  warning does not fire. Footnote / header / footer / abandoned
  regions are NEVER dropped, regardless of this flag.

## Evidence

- Code: `pdomain_ocr_cli/_pipeline.py` (`upright_layout_source`),
  `pdomain_ocr_cli/ocr_to_txt.py` (single-image rotation, layout and crop
  calls), `pdomain_ocr_cli/_artifacts.py` (`PageOutputTransaction`).
- Tests: `tests/test_upright_layout.py`
  (`test_rotated_page_layout_and_crops_use_upright_image`,
  `test_unrotated_page_keeps_on_disk_layout_and_crops`,
  `test_kept_angle_orients_layout_when_no_buffer_is_stashed`,
  `test_upright_layout_source_rejects_non_quarter_turn`,
  `test_angle_only_crop_takes_the_marked_corner_from_real_pixels`,
  `test_pinned_batch_ocr_returns_degrees_and_the_upright_image`),
  `tests/test_default_layout_word_preservation.py`
  (`test_default_layout_preserves_every_ocr_word`), `tests/test_artifacts.py`.
- History: commit `c325c13` (v0.9.0, `pdomain-book-tools==0.30.1`) and
  `7af73fc` (v0.9.1).
- Verified: 2026-11-07, by reading the code and tests at `7af73fc`. The
  v0.9.1 release preflight `make ci-slow` passed with 468 tests.

The 2026-11-13 source review checked the warning-and-skip crop path against
`tests/test_main_errors.py::test_main_extract_illustrations_imencode_returns_false_no_tmp_swallows_unlink`.
The pinned batch contract test in `tests/test_upright_layout.py` exercises
`pdomain-book-tools` with a mocked predictor and rotation choice; it does not
directly exercise the `pdomain-ops` batch wrapper.
