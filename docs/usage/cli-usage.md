---
Status: active
Owner: CT
Created: 2026-05-19
Last verified: 2026-11-10
Kind: usage
---

# Full usage options

This page lists every `pdomain-ocr` flag, grouped by purpose.
For the friendly walkthrough, see the [README](../../README.md). For
layout-detector specifics (the bulk of the layout flags below), see
[layout-aware-ocr.md](../architecture/layout-aware-ocr.md). `pdomain-ocr --help` is always
authoritative.

## Inputs and outputs

```sh
# Single image — output written alongside as page.txt
pdomain-ocr page.png

# Multiple images (any mix of files / directories)
pdomain-ocr page1.png page2.png images/

# OCR pages in smaller chunks (must be >= 1; default 4)
pdomain-ocr --batch-pages 2 page1.png page2.png page3.png

# All images in a directory (non-recursive)
pdomain-ocr images/

# Recurse into subdirectories
pdomain-ocr --recursive images/        # also: -r, -R

# Write outputs into a specific directory.
# When inputs include directories, structure is mirrored under -o.
pdomain-ocr -o output/ page.png
pdomain-ocr -r images/ -o output/      # output/ mirrors images/'s tree

# Also save the reorganized OCR document as JSON next to the .txt
pdomain-ocr --save-json page.png
```

Recognized image suffixes come from `pdomain-book-tools`
`SUPPORTED_IMAGE_SUFFIXES` (currently): `.avif`, `.bmp`, `.gif`, `.heic`,
`.heif`, `.j2k`, `.jp2`, `.jpeg`, `.jpf`, `.jpg`, `.jpx`, `.pbm`, `.pgm`,
`.png`, `.pnm`, `.ppm`, `.tif`, `.tiff`, `.webp` — including the JPEG 2000
family (`.jp2`, `.j2k`, `.jpf`, `.jpx`). Matching is case-insensitive. Other
files in a directory are skipped with a warning.

### Image resource limits

Every candidate image is checked before it joins an OCR batch:

- **Compressed size** — files over 100 MiB (104,857,600 bytes) are rejected
  before decoding (collection still opens each candidate for a 16-byte
  magic-number sniff; decoding is what's skipped).
- **Decoded pixel count** — images whose width × height exceeds
  100,000,000 pixels are rejected before they enter a batch. This guards
  against decompression-bomb-style inputs whose small compressed size hides
  a huge decoded footprint.

The file size is checked again after the file is read. One OCR batch holds at
most 400,000,000 decoded pixels. A larger `--batch-pages` value can therefore
produce smaller batches than you asked for on very large pages.

A rejected image is reported through the same per-image error channel as
any other OCR failure: the CLI prints `ERROR processing <path>: ...` naming
the path and the limit, counts it as an error, and continues with the rest of
the batch. The size check and the header pixel check also name the observed
value. When Pillow or OpenCV hits the cap during decoding, the message names
only the limit.

These limits are fixed and not configurable. There is no processing
timeout — a pathologically slow (but appropriately sized) image can still
run for as long as OCR takes.

## Text normalization

```sh
# Curly → straight quotes ('hi' "hi" → 'hi' "hi")
pdomain-ocr --straight-quotes page.png        # also: -sq

# Em dash → ASCII double hyphen (— → --)
pdomain-ocr --em-dash-to-double-hyphen page.png   # also: -ed
```

`--straight-quotes` covers the eight common curly variants
(`‘-‟`). Prime symbols (`′`, `″`) are intentionally left
alone — they're meaningful in measurements and citations.

### Future proposal: output normalization (not implemented)

This proposal is not implemented yet. It is tracked here so users and
contributors know it's on the roadmap.

**Motivation.** OCR on old-typesetting books (Cló Gaelach, Fraktur,
early-modern English with long-s) may emit Unicode glyphs that faithfully
reflect the page. These include `ſ` (long s), `ﬁ`/`ﬂ`/`ﬀ`/`ﬃ`/`ﬄ`
(f-ligatures), `ſt` (long-s+t ligature), and similar glyphs. Faithful Unicode
is the right default for archival OCR fidelity. However, downstream consumers,
most notably PGDP-style proofreading flows, want ASCII-equivalent text (`s`,
`fi`, `fl`, `st`, …). This lets volunteers see the same characters they'd
type. The user picks per run.

**Proposed flag.**

```sh
# Default — preserve OCR glyphs exactly as recognized.
pdomain-ocr page.png

# Map the standard glyph set (long-s, f-ligatures, st-ligature, …) to
# their ASCII equivalents before the .txt is written.
pdomain-ocr --normalize-output ascii page.png
```

Flag shape: `--normalize-output {none|ascii|...}`, default `none`.
Mode names are an open extension point for future locale-specific
profiles (e.g. a `gaelic` profile that also handles dotted consonants).

**Dependency.** The actual normalization logic + glyph map live in
`pdomain-book-tools` as `pdomain_book_tools.text.normalize` (to be added). The
CLI is a thin pass-through that runs the normalizer between
reorganize and disk write. This keeps the same map reusable from
`pdomain-ocr-labeler` (page-scope action) and `pdomain-prep-for-pgdp` (export
step) without duplication.

**Cross-refs.** Mirrors decision D-025 in the sibling repository path
`pdomain-ocr-labeler-spa/specs/17-decisions.md`.

## Model selection

By default, `pdomain-ocr` downloads fine-tuned weights from
`pdomain/pdomain-ocr-models` on Hugging Face the first time it runs, pinned
to the commit behind the tag `v0.7`. Pass `--model-version <tag>` to
use a different release.

```sh
# Pin to a specific model version (HF Hub revision / tag)
pdomain-ocr --model-version v1.2.0 page.png

# Use a different HF Hub repo
pdomain-ocr --hf-repo myorg/my-ocr-models page.png

# Override the filenames within the repo
pdomain-ocr --det-filename detection/custom.pt \
       --reco-filename recognition/custom.pt page.png

# Use local .pt files instead of downloading.
# Both flags must be provided together.
pdomain-ocr -d ./detection.pt -g ./recognition.pt page.png
```

Local `.pt` files are loaded as-is. If sibling `.arch` / `.vocab`
files exist next to them, they're picked up automatically.

### Model trust boundary

Treat OCR and layout model checkpoints as trusted inputs. This project
maintains the default model source and pins the default `--model-version` to
commit `8b7f9b31d55015d16febaa99ae1d42960904028c`, the commit behind the tag
`v0.7`. A Hugging Face tag can be moved by the repository owner, so a commit
SHA is the only immutable pin. Branch names such as `main` move, and they print
a warning.
Use custom `--hf-repo`, local `--detection` / `--recognition`, and
`--layout-checkpoint` values only from sources you trust.

## Layout detection

Layout detection runs by default with reorganize and feeds that step. Plain
`--no-reorg` also skips layout. If you also pass `--extract-illustrations`,
layout still runs so it can find the crops.
See [layout-aware-ocr.md](../architecture/layout-aware-ocr.md) for the full picture.

```sh
# Skip layout detection entirely (faster, lower-quality reorg on
# pages with figures, captions, marginalia, etc.)
pdomain-ocr --layout-model none page.png

# Switch to the rule-based contour heuristic
pdomain-ocr --layout-model contour page.png

# Use a fine-tuned PP-DocLayout checkpoint (path or HF repo)
pdomain-ocr --layout-checkpoint ~/my-finetuned-layout/ page.png

# Tighten / loosen the confidence threshold (0..1, default 0.5).
# Values outside [0, 1] (and `nan` / `inf`) are rejected at parse time.
pdomain-ocr --layout-confidence 0.3 page.png

# Crop figure / decoration / table regions to i_<stem>_<n>.jpg
pdomain-ocr --extract-illustrations page.png

# Suppress empty figure / decoration / table placeholder blocks in the
# reorganized .txt (caption text is still preserved)
pdomain-ocr --no-illustration-placeholders page.png

# Per-step layout debug text (see layout-aware-ocr.md)
pdomain-ocr --layout-debug page.png
pdomain-ocr --layout-debug --layout-debug-dir debug/ page.png
```

`--extract-illustrations` requires a layout model — combining it with
`--layout-model none` is rejected.

## Reorganize controls

`Page.reorganize_page()` from `pdomain-book-tools` turns the raw OCR block
tree into reading-order text. These flags let you skip it, snapshot
it, or audit it.

```sh
# Skip reorganize entirely — emit raw OCR
pdomain-ocr --no-reorg page.png

# With --save-json: also write the full diagnostic bundle alongside
# the regular .txt/.json — six files per page in total:
#   <image>.txt + <image>.json                   (post-reorganize)
#   <image>.pure-ocr.txt + <image>.pure-ocr.json (literal OCR output)
#   <image>.post-noise.txt + <image>.post-noise.json
#                                                (after figure-noise
#                                                 removal, before reorg)
# Useful for auditing what reorganize preserved, dropped, or rearranged.
# The old name --save-pre-reorg-json is still accepted as a back-compat alias.
pdomain-ocr --save-json --save-reorganize-diagnostics page.png

# Warn (don't fail) if reorganize drops any words
pdomain-ocr --validate-reorg page.png

# [experimental] Enable drop of figure-internal OCR words during
# reorganize. Two steps are gated by this flag:
#   * Step Layout-2b — lines fully inside detected figure regions
#     with no body-text overlap.
#   * Step B2 — figure-internal heuristic noise.
# Default keeps all words. Footnote / header / footer / abandoned
# regions are NEVER dropped, regardless of this flag.
pdomain-ocr --experimental-drop-layout-words page.png   # also: --edl
```

Plain `--no-reorg` emits raw OCR and skips layout detection. Combine it
with `--extract-illustrations` only when you want raw text plus illustration
crops; in that case layout detection still runs for crop discovery.

### Always-on noise-drop warning

When reorganize removes words it considered figure-internal noise, the CLI
always emits a warning to stderr. Removal happens via Step Layout-2b or Step B2
inside `pdomain-book-tools`. The warning includes:

- the page filename and the count of dropped words;
- a quoted sample of the first few dropped tokens;
- a hint pointing at `--save-json --save-reorganize-diagnostics` so you
  can re-run and inspect the full pure-OCR / post-noise / post-reorg
  bundle.

This warning is intentionally always on so figure-noise drops don't pass
unnoticed. There is no quiet flag. File an issue if you need one.

## JSON Contract

When `--save-json` is enabled, each sidecar uses the same document
envelope shape as `pdomain-book-tools`. Downstream tools can rely on the
top-level keys `source_lib`, `source_identifier`, `source_path`, and
`pages`. `source_identifier` is the input filename, `source_path` is the
input path seen by the CLI, and `pages` contains exactly one page for
each image sidecar.

## Misc

```sh
# Print the installed version
pdomain-ocr --version

# Skip the background GitHub-tag check (offline runs, locked-down
# networks, or just to silence the upgrade notice).
# Can also be set persistently: export PD_OCR_NO_UPDATE_CHECK=1
pdomain-ocr --no-update-check page.png

# Built-in help — authoritative listing of every flag
pdomain-ocr --help
```

## Installer behavior

The `install.sh` and `install.ps1` bootstrap scripts install the wheel
asset from the latest GitHub Release, not a git ref. Before installing, each
script checks the wheel against the `sha256` digest GitHub reports for that
asset. A missing, malformed, or mismatched digest stops the install. Both
scripts pass `https://pdomain.github.io/pdomain-index-pip/simple/` to `uv` as a
named `--index` with `--index-strategy first-index`, so `pdomain-book-tools`
resolves only from the pdomain package index. They
default the uv tool environment to Python 3.13; set
`PD_OCR_INSTALL_PYTHON` before running either script to use another
supported Python version.

### Environment variables

| Variable | Effect |
| --- | --- |
| `PD_OCR_NO_UPDATE_CHECK=1` | Skip the background GitHub-tag upgrade-notice request (same as `--no-update-check`). |
| `PD_OCR_NO_GPU_NUDGE=1` | Silence the one-line "GPU detected but installed CPU-only" message printed on startup when `nvidia-smi` is on `PATH` but the `[gpu]` extra wasn't installed. See the FAQ in [README.md](../../README.md#faq) for details. |
| `PD_OCR_INSTALL_PYTHON` | Installer-only override for the Python version passed to `uv tool install --python`; defaults to `3.13`. |
| `PD_OCR_DEBUG=1` | On per-image processing errors, also print the full traceback to stderr. If the background update check fails, print `update check failed: {type}: {message}` or `update check failed: {reason}`. |
| `PD_OCR_REORGANIZE_STRICT=1` | Read by `pdomain-book-tools`'s `reorganize_page()`. When set, words dropped during reorganize raise `ReorganizeDroppedWordsError` instead of being re-added with a warning. Useful in CI to fail loudly on pipeline regressions. |
| `HF_HOME`, `HF_HUB_CACHE` | Override the Hugging Face model cache location (default `~/.cache/huggingface/hub`). Honored by the upstream `huggingface_hub` library — pdomain-ocr-cli does not read these directly. |

The CLI sets `PD_OCR_LAYOUT_DEBUG` and `PD_OCR_LAYOUT_DEBUG_FILE`
automatically as an internal IPC channel to the layout backend. Control them
through `--layout-debug` / `--layout-debug-dir`; do not override them manually.

### Conflicting flags / no-op combinations

When you pass a flag combination that can't take effect, `pdomain-ocr` emits a
`warning:` to stderr and proceeds. It ignores the redundant flag rather than
treating it as fatal. The current set:

- `--no-reorg` + `--save-reorganize-diagnostics` — diagnostics are produced
  only when reorganize runs.
- `--no-reorg` + `--validate-reorg` — validation compares pre/post
  reorganize word lists.
- `--layout-model none` + `--layout-debug` — no layout model runs, so no
  debug artifact is written.
- `--no-reorg` + `--layout-debug` — the debug report is written from
  inside `reorganize_page`, which is skipped.
- `--layout-debug-dir` without `--layout-debug` — the directory is only
  used when the debug artifact is enabled.
- `--save-reorganize-diagnostics` without `--save-json` — the diagnostic
  bundle is written alongside the regular `.json` output, which requires
  `--save-json`.
- `--no-reorg` + `--experimental-drop-layout-words` — the drop is applied
  inside `reorganize_page`, which is skipped.
- `--no-reorg` + `--no-illustration-placeholders` — placeholder emission
  happens inside `reorganize_page`, which is skipped.

## Full flag table

| Flag | Short | Default | Purpose |
| --- | --- | --- | --- |
| `--hf-repo REPO_ID` | | `pdomain/pdomain-ocr-models` | HF Hub repo for OCR models. |
| `--model-version TAG` | | commit behind `v0.7` | HF revision / tag. |
| `--det-filename PATH` | | `detection/pdomain-all-detection-model-finetuned.pt` | Detection-model path within the HF repo. |
| `--reco-filename PATH` | | `recognition/pdomain-all-recognition-model-finetuned.pt` | Recognition-model path within the HF repo. |
| `--detection PT_FILE` | `-d` | — | Local detection `.pt`; requires `--recognition` too. |
| `--recognition PT_FILE` | `-g` | — | Local recognition `.pt`; requires `--detection` too. |
| `--output-dir DIR` | `-o` | input's dir | Where `.txt` (and `.json`, crops) are written. |
| `--recursive` | `-r`, `-R` | off | Recurse into subdirectories of input dirs. |
| `--batch-pages N` | | `4` | Pages per OCR batch. Must be `>= 1`. |
| `--save-json` | | off | Write the reorganized doc as `<image>.json`. |
| `--no-reorg` | | off | Skip `reorganize_page()` and, unless `--extract-illustrations` is set, layout detection; emit raw OCR. |
| `--save-reorganize-diagnostics` | | off | With `--save-json`: also write the pure-OCR + post-noise diagnostic snapshots as JSON+TXT siblings. Old alias: `--save-pre-reorg-json`. |
| `--validate-reorg` | | off | Warn if reorganize drops any OCR words. |
| `--experimental-drop-layout-words` | `--edl` | off | [experimental] Enable drop of figure-internal OCR words during reorganize: Step Layout-2b (lines fully inside figure regions with no body-text overlap) and Step B2 (figure-internal heuristic noise). Footnote / header / footer / abandoned regions are NEVER dropped, regardless of this flag. |
| `--straight-quotes` | `-sq` | off | Curly → straight ASCII quotes. |
| `--em-dash-to-double-hyphen` | `-ed` | off | Em dash → `--`. |
| `--no-update-check` | | off | Skip the background GitHub-tag upgrade-notice request. Also via `PD_OCR_NO_UPDATE_CHECK=1`. |
| `--layout-model {none,contour,pp-doclayout-plus-l}` | | `pp-doclayout-plus-l` | Layout backend. |
| `--layout-checkpoint PATH_OR_REPO` | | — | Fine-tuned PP-DocLayout checkpoint. |
| `--layout-confidence THRESHOLD` | | `0.5` | Region-confidence threshold (0..1). |
| `--extract-illustrations` | | off | Crop figure / decoration / table regions. |
| `--no-illustration-placeholders` | | off | Suppress empty figure / decoration / table placeholder blocks in the reorganized output. Caption text is preserved. No effect with `--no-reorg`. |
| `--layout-debug` | | off | Write layout debug text. |
| `--layout-debug-dir DIR` | | output dir | Where layout debug text goes. |
| `--version` | | — | Print version and exit. |
