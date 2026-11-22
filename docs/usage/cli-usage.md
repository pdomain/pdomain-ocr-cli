---
Status: active
Owner: CT
Created: 2026-05-19
Last verified: 2026-11-15
Kind: usage
---

# Full usage options

Use this guide to choose OCR options, prepare model files, and manage updates.
See the [install guide](../../README.md#install) to get started.
Run `pdomain-ocr --help` for the options available in your installed version.

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

Supported file extensions include `.avif`, `.bmp`, `.gif`, `.heic`, `.heif`,
`.j2k`, `.jp2`, `.jpeg`, `.jpf`, `.jpg`, `.jpx`, `.pbm`, `.pgm`, `.png`,
`.pnm`, `.ppm`, `.tif`, `.tiff`, and `.webp`. Extensions are case-insensitive.
The CLI warns when it skips other files.

### Image resource limits

Images over 100 MiB or 100 million pixels fail with a message naming the
file and limit. OCR continues with the other images. Large pages can make
batches smaller than `--batch-pages` requests. These limits are fixed, and
there is no per-image timeout. See [how the CLI limits image sizes and batches](../architecture/cli-orchestration.md#execution-invariants).

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

ASCII output normalization is deferred. See the [roadmap](../roadmap.md),
[design](../specs/2026-07-21-normalize-output-design.md), and
[deferred issue](../issues/2026-07-19-normalize-output-flag-deferred.md).

## Model selection

The installer caches the default models. OCR fetches missing files when
needed. The default OCR revision is the commit behind `v0.7` in
`pdomain/pdomain-ocr-models` on Hugging Face. Use `--model-version` to select a
different revision.

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

Use custom OCR weights and layout checkpoints only from sources you trust.
The CLI warns about unpinned model revisions and custom checkpoint sources.
See [model sources and trust checks](../architecture/cli-orchestration.md#trust-and-network-boundaries).

## Layout detection

Layout detection helps place captions, marginal notes, and page numbers in
reading order. `--no-reorg` skips layout unless you request
`--extract-illustrations` for crops.
See [how layout-aware OCR works](../architecture/layout-aware-ocr.md).

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

Reorganization puts OCR text in reading order. Use `--no-reorg` for raw OCR.
Use `--validate-reorg` to warn about missing words after reorganization.

```sh
pdomain-ocr --no-reorg page.png
pdomain-ocr --validate-reorg page.png
pdomain-ocr --save-json --save-reorganize-diagnostics page.png
pdomain-ocr --experimental-drop-layout-words page.png
```

With `--save-json`, diagnostics save three text and JSON pairs for each page.
The regular pair contains the final text and document. The `.pure-ocr` pair
shows raw OCR, and the `.post-noise` pair shows the text after noise removal
and before reorganization. The old `--save-pre-reorg-json` alias still works.

`--experimental-drop-layout-words` (also `--edl`) allows removal of OCR words
inside figures. The default keeps every word. This flag keeps footnotes, headers,
footers, and abandoned regions. See the [layout behavior and related flags](../architecture/layout-aware-ocr.md#related-flags).

### Always-on noise-drop warning

When figure-noise removal drops words, the CLI always prints the page name,
the count, and a sample of dropped words to stderr. Rerun with
`--save-json --save-reorganize-diagnostics` to compare the three snapshots.

## JSON Contract

Each `--save-json` sidecar contains one page in `pages`. It also includes
`source_lib`, `source_identifier` (the input filename), and `source_path`
(the input path the CLI received).

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

See the [install guide](../../README.md#install) for each platform. The
installer caches the default detection, recognition, and layout models.
Use the [skip flag](../../README.md#skip-model-downloads-during-installation)
to defer downloads. Run `pdomain-ocr download-models` to fill the cache later.

| Command | What it does |
| --- | --- |
| `pdomain-ocr update --check` | Show the latest stable release. |
| `pdomain-ocr update` | Ask before updating a `uv tool` installation. |
| `pdomain-ocr update --yes` | Update without asking. |

The updater checks the approved version and loads the OCR runtime through
the installed launcher. If the check fails, the worker tries to restore the
previous installation. On Windows, exit code 0 acknowledges the handoff.
Wait for the worker to report an update, a rollback, or the need for recovery.

If the update stops before it reports a result, run the recovery command
printed before activation. It works even if the launcher cannot start. If
recovery reports a conflict, keep the journal and parked environment.

If an input named `update` is in the current directory, run the updater from
another directory. Use `./update` to select the OCR input explicitly.

See [how installation and updates work](../architecture/installation-and-updates.md).

### Environment variables

| Variable | Effect |
| --- | --- |
| `PD_OCR_NO_UPDATE_CHECK=1` | Turn off automatic update checks. |
| `PD_OCR_AUTO_UPDATE_CHECK=1` or `0` | Override the saved background-check preference for this run. |
| `PD_OCR_INSTALL_AUTO_UPDATE_CHECK=1` or `0` | Save the background-check preference during installation. |
| `PD_OCR_NO_GPU_NUDGE=1` | Hide the [CUDA startup notice](../../README.md#faq). |
| `PD_OCR_INSTALL_PYTHON` | Choose the installer Python version. The default is `3.13`. |
| `PD_OCR_DEBUG=1` | Show a traceback for image errors and a message for failed automatic update checks. |
| `PD_OCR_REORGANIZE_STRICT=1` | Raise an error if reorganization drops words. By default, unexpected drops are restored with a warning. |
| `HF_HOME`, `HF_HUB_CACHE` | Change the model cache location. The default is `~/.cache/huggingface/hub`. |

Use `--layout-debug` and `--layout-debug-dir` to control layout reports.

### Conflicting flags / no-op combinations

The CLI warns and continues when an option has no effect.

| Option | When it has no effect |
| --- | --- |
| `--save-reorganize-diagnostics` | With `--no-reorg` or without `--save-json`. |
| `--validate-reorg`, `--experimental-drop-layout-words`, `--no-illustration-placeholders` | With `--no-reorg`. |
| `--layout-debug` | With `--layout-model none` or `--no-reorg`. |
| `--layout-debug-dir` | Without `--layout-debug`. |

## Automatic update checks

Automatic checks are off by default. The [install guide](../../README.md#install-with-automatic-update-checks)
shows both ways to turn them on during installation. The installer flag takes
precedence over the environment variable. With the flag omitted, set
`PD_OCR_INSTALL_AUTO_UPDATE_CHECK=0` to turn checks off. Leave both unset to
keep your saved preference.

Change your preference later with `pdomain-ocr update --auto-check on` or
`pdomain-ocr update --auto-check off`. You can also set `auto_check = true`
or `auto_check = false` in `update.toml`.

- Linux and macOS use `$XDG_CONFIG_HOME/pdomain-ocr/` or
  `~/.config/pdomain-ocr/` when `XDG_CONFIG_HOME` is unset.
- Windows uses `%APPDATA%\pdomain-ocr\`.

`PD_OCR_AUTO_UPDATE_CHECK=1` or `0` takes precedence over the saved setting.
`--no-update-check` and `PD_OCR_NO_UPDATE_CHECK=1` always turn off automatic
checks. Run `pdomain-ocr update --check` to check on demand.

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
| `--experimental-drop-layout-words` | `--edl` | off | Allow reorganization to remove OCR words inside figures. |
| `--straight-quotes` | `-sq` | off | Curly → straight ASCII quotes. |
| `--em-dash-to-double-hyphen` | `-ed` | off | Em dash → `--`. |
| `--no-update-check` | | off | Turn off automatic update checks for this run. |
| `--layout-model {none,contour,pp-doclayout-plus-l}` | | `pp-doclayout-plus-l` | Layout backend. |
| `--layout-checkpoint PATH_OR_REPO` | | — | Fine-tuned PP-DocLayout checkpoint. |
| `--layout-confidence THRESHOLD` | | `0.5` | Region-confidence threshold (0..1). |
| `--extract-illustrations` | | off | Crop figure / decoration / table regions. |
| `--no-illustration-placeholders` | | off | Suppress empty figure / decoration / table placeholder blocks in the reorganized output. Caption text is preserved. No effect with `--no-reorg`. |
| `--layout-debug` | | off | Write layout debug text. |
| `--layout-debug-dir DIR` | | output dir | Where layout debug text goes. |
| `--version` | | — | Print version and exit. |
