---
Status: active
Owner: CT
Created: 2026-05-03
Last verified: 2026-11-07
Kind: process
---

# pdomain-ocr-cli

Turn scanned book pages into clean `.txt` files. No setup required —
install it and point it at an image.

## What pdomain-ocr does

Point it at a page scan (or a folder of them) and it writes a `.txt`
file next to each image. Two things make the output more useful than
plain OCR:

- **Layout-aware reorganization.** Before reading the words, `pdomain-ocr`
  looks at the whole page and figures out what each part is: the body
  text, the figures, the captions underneath them, the running title at
  the top, the page number at the bottom, and any sidenotes in the
  margin. It uses that map to put the text together in the right order.
  Captions stay with their figures, running titles and page numbers stay
  at the top, and sidenotes stay separate from the paragraphs they sit
  next to. By default, `pdomain-ocr` drops no OCR words. The opt-in flag
  `--experimental-drop-layout-words` (`--edl`) lets it drop noise found
  inside figures, and it always prints a warning when that happens. More
  in
  [docs/architecture/layout-aware-ocr.md](docs/architecture/layout-aware-ocr.md).
- **Auto-rotation.** If a page was scanned sideways or upside down,
  `pdomain-ocr` re-runs the OCR at 90° / 180° / 270° and keeps the
  orientation that reads best.

The first time you run it, it downloads the models it needs
(roughly 150 MB total). After that it works offline — no account or
sign-up. For specifics on what the tool downloads and from where, see
[Technical details](#technical-details) at the bottom.

Supported Python versions for the package are `>=3.11,<3.14`. The
installer defaults to Python 3.13 for the managed `uv tool`
environment, but the wheel is tested on Python 3.11, 3.12, and 3.13.

---

## GPU acceleration (optional)

`pdomain-ocr` works fine on CPU. Add an NVIDIA GPU and it goes faster — worth
it when you're running through a whole book rather than one page.

> ⚠️ **Heads up — disk space.** The NVIDIA path pulls in the CUDA
> Toolkit and CUDA-flavored PyTorch wheels — roughly 10 GB total. CPU
> mode is a fine starting point if that's tight.

- **NVIDIA on Linux/Windows** — install the [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) (13 or newer for the GPU extra), then run the install script; it auto-detects CUDA.
- **Apple Silicon Mac** — kicks in automatically, nothing to install. *(Unverified — feedback welcome.)*
- **No GPU** — nothing to do; CPU is the default.

Already installed without a GPU? Re-run the install script — it
swaps the install in place. See the [FAQ](#faq) for switching to GPU,
the "GPU detected but installed CPU-only" nudge, troubleshooting, and
when a GPU is (or isn't) worth it.

---

## Install

**Linux / macOS:**

```sh
curl -sSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh | sh
```

**Windows (PowerShell):**

Run this in Windows PowerShell. It works under the default `Restricted`
execution policy and does not change your policy.

```powershell
irm https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1 | iex
```

You do not need an administrator PowerShell. `pdomain-ocr` installs for your
own account. On Windows the script also checks for the Microsoft Visual C++
Redistributable (x64), which PyTorch needs. If it is missing or too old, the
script downloads Microsoft's installer, checks that Microsoft signed it, and asks
Windows for administrator permission for that step only. It never restarts
Windows. If a restart is needed, it tells you.

Both scripts install the wheel from the latest GitHub Release and pass
the self-hosted `pdomain-index-pip` package index. They also detect
NVIDIA CUDA automatically and select the matching PyTorch build. Set
`PD_OCR_INSTALL_PYTHON` before running the script to override the
installer Python version; the default is `3.13`. The PowerShell script is
self-contained for piped `irm ... | iex` installs; a checked-out helper
script is only used as a development override.

---

## Usage

```sh
# OCR a single image (output written alongside as page.txt)
pdomain-ocr page.png

# Multiple images
pdomain-ocr page1.png page2.png page3.png

# Process all images in a directory
pdomain-ocr images/

# Process a directory tree recursively, mirroring structure into output/
pdomain-ocr -r images/ -o output/

# Also save the reorganized OCR document as JSON
pdomain-ocr --save-json page.png

# Print the installed version
pdomain-ocr --version
```

The full flag reference (quote and em-dash normalization, model pinning,
layout-detector options, illustration extraction, debug output) lives in
[docs/usage/cli-usage.md](docs/usage/cli-usage.md). `pdomain-ocr --help` lists everything
authoritatively.

---

## FAQ

### How do I switch from CPU-only to GPU?

Re-run the install script. It re-detects `nvidia-smi` on every run,
has uv pick the matching PyTorch CUDA build, and (when CUDA ≥ 13)
opts into the `pdomain-book-tools[gpu]` extra (`cupy-cuda13x`).
`uv tool install --reinstall` swaps the existing install in place.

```sh
# Linux / macOS
curl -sSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh | sh
```

```powershell
# Windows
irm https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1 | iex
```

CUDA 12 still gets the matching PyTorch wheel, but the CuPy stack is
skipped (`cupy-cuda13x` requires CUDA 13).

### Why am I seeing a "GPU detected but installed CPU-only" message?

On startup, `pdomain-ocr` runs a cheap check. If your host has an NVIDIA GPU
(`nvidia-smi` on `PATH`, exits 0) but pdomain-ocr was installed without the
`[gpu]` extra (CuPy isn't importable), it prints a one-line nudge to
stderr. The nudge suggests the reinstall command. The probe is
fail-soft: it swallows any error and lets the OCR run proceed normally.

To silence it persistently (e.g. you've decided CPU-only is right for
this host):

```sh
export PD_OCR_NO_GPU_NUDGE=1
```

### Is a GPU worth it for my workload?

For one-off pages, most of the time goes into loading the models, not
reading the words — CPU feels about the same. The GPU pays off when
you're processing tens or hundreds of pages in a single run.

### The GPU isn't being used — what's wrong?

A few things to check:

- **`nvidia-smi` not found** — NVIDIA driver / toolkit isn't
  available in your environment. Install the [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads).
- **Running in Docker / devcontainer** — make sure the container was
  started with `--gpus all` and the NVIDIA Container Toolkit is
  configured on the host (see
  [Running in a Container](#running-in-a-container-with-nvidia-gpu)).
- **GPU still not used after that** — re-run the install script; it
  re-detects on each run.

For the deep mechanics (PyTorch CUDA build selection, what the install
script does, disk / VRAM budgets), see
[Technical details](#technical-details).

### On a server or in a container, OCR fails with "libxcb.so.1: cannot open shared object file"

OpenCV, which reads and cleans up the page images, needs a few X11 and
OpenGL libraries. Every desktop Linux has them. Minimal servers and
container images often don't. Install them once, as root:

| Distribution | Command |
|---|---|
| Ubuntu 24.04+, Debian 13+ | `apt install libgl1 libsm6 libice6 libx11-6 libxext6 libxcb1 libglib2.0-0t64` |
| Older Ubuntu and Debian | `apt install libgl1 libsm6 libice6 libx11-6 libxext6 libxcb1 libglib2.0-0` |
| Fedora, AlmaLinux, RHEL | `dnf install mesa-libGL libSM libICE libX11 libXext libxcb glib2` |
| Arch | `pacman -S libglvnd mesa libsm libice libx11 libxext libxcb glib2` |
| openSUSE | `zypper in Mesa-libGL1 libSM6 libICE6 libX11-6 libXext6 libxcb1 libglib-2_0-0 libgthread-2_0-0` |

These lists were tested on 2026-11-14 in Ubuntu 24.04 and 22.04, Debian 13,
Fedora 45, AlmaLinux 9.8, Arch and openSUSE Tumbleweed containers. Alpine is
not supported, because PyTorch publishes no wheels for it.

### Why is the first run so slow?

That's the one-time model download (~150 MB) and initialization.
Later runs reuse the cache.

### Windows: OCR fails with "WinError 126" loading `c10.dll`

The Microsoft Visual C++ Redistributable (x64) is missing or out of date.
PyTorch prints a warning about it just before this error. Re-run the install
script, which installs it, or install it yourself from an administrator
account:

1. Download <https://aka.ms/vc14/vc_redist.x64.exe>, Microsoft's
   [latest supported redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
2. Run `vc_redist.x64.exe /install /passive /norestart`.
3. Run `pdomain-ocr` again. You do not need to reinstall it.

A standard account needs an administrator to approve or run step 2. Set
`PD_OCR_SKIP_VC_RUNTIME=1` before the install script to stop it installing the
runtime; it then fails with these steps instead.

### Where are the models cached?

`~/.cache/huggingface/hub` by default; override with `$HF_HOME` or
`$HF_HUB_CACHE`. See [Network calls](#network-calls-the-tool-makes)
for what's downloaded and from where, and [Uninstall](#uninstall) for
how to remove the cache.

### Model trust boundary

OCR and layout model checkpoints are trusted inputs. The default model
source is maintained by this project, and the default `--model-version`
is pinned to the commit behind the tag `v0.7`. Tags and branch names can
move; a commit SHA cannot. Custom `--hf-repo`, local `--detection` / `--recognition`,
and `--layout-checkpoint` values should only come from sources you
trust.

---

## Running in a Container with NVIDIA GPU

You'll need the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) configured on your host and the container run with `--gpus all`. Then install as normal inside the container.

---

## Uninstall

```sh
uv tool uninstall pdomain-ocr-cli
```

To also remove the cached models, check your `HF_HOME` environment variable for the cache location:

```sh
echo $HF_HOME   # custom location if set
# Default location:
rm -rf ~/.cache/huggingface/hub/models--pdomain--pdomain-ocr-models
```

---

## Technical details

### What's under the hood

- **Text recognition:** [DocTR](https://github.com/mindee/doctr)
  (detection + recognition), with weights fine-tuned on
  public-domain book scans.
- **Layout detection:** [PP-DocLayout_plus-L](https://github.com/PaddlePaddle/PaddleOCR)
  (RT-DETR-based), Apache-2.0 licensed.
- **Pipeline glue:** [pdomain-book-tools](https://github.com/pdomain/pdomain-book-tools)
  — owns the OCR predictor wrapper, layout adapter, and the
  `reorganize_page()` step that turns OCR output into reading-order
  text.

### Network calls the tool makes

`pdomain-ocr` does not collect telemetry or call home with usage data. It
makes exactly these outbound requests:

1. **Model downloads** (first run only, then cached):
   - OCR weights from
     [`pdomain/pdomain-ocr-models`](https://huggingface.co/pdomain/pdomain-ocr-models)
     on `huggingface.co`.
   - Layout weights from
     [`CT2534/PP-DocLayout_plus-L`](https://huggingface.co/CT2534/PP-DocLayout_plus-L)
     on `huggingface.co`.
   - No Hugging Face account required.
   - Cached at `~/.cache/huggingface/hub` by default; override with
     `$HF_HOME` or `$HF_HUB_CACHE`.
2. **Version check** (every run, in the background):
   - `GET https://api.github.com/repos/pdomain/pdomain-ocr-cli/tags?per_page=100`
   - 3-second timeout; if a newer release tag exists, prints a one-line
     upgrade notice to stderr.
   - Best-effort: it suppresses any network or parse error, and never
     blocks startup. With `PD_OCR_DEBUG=1` it prints a one-line
     `update check failed: ...` message to stderr.
   - Bypass entirely with `--no-update-check`, or persistently via
     the `PD_OCR_NO_UPDATE_CHECK=1` env var (e.g. offline runs or
     locked-down networks).

If you need to run fully offline after the first install, both of
these are cache-friendly. Once models are cached and the update check
is suppressed (`--no-update-check` or `PD_OCR_NO_UPDATE_CHECK=1`), no
further network access is required.

### The install script

`install.sh` / `install.ps1` are bootstrap helpers — re-run them any
time to upgrade or to switch between CPU and GPU. They:

- Install [uv](https://docs.astral.sh/uv/) if it isn't already on PATH.
- Resolve the latest non-prerelease GitHub Release via the GitHub API
  (`install.sh` uses `gh` instead if it is authenticated) and download
  the published `.whl` asset.
- Check the downloaded wheel against the `sha256` digest GitHub reports
  for it, and refuse to install if the digest is missing or does not
  match.
- Use Python 3.13 by default for the uv tool environment. Override with
  `PD_OCR_INSTALL_PYTHON` if you need another supported Python version.
- Detect NVIDIA CUDA via `nvidia-smi`. If found, pass
  `--torch-backend auto` so uv picks the PyTorch CUDA build that matches
  the driver, and (when CUDA ≥ 13) add
  `--with 'pdomain-book-tools[gpu]'` for `cupy-cuda13x`.
- Run `uv tool install --reinstall <wheel>` with
  `--index-strategy first-index` and a named `--index` for the
  self-hosted `pdomain-index-pip` (for `pdomain-book-tools`).
- Stop with an error, and never print `Done`, if `uv` fails. A `uv` too
  old for `--torch-backend` gets a hint to run `uv self update`. When `uv`
  reports a network failure after its own retries, the script tries twice
  more, 15 and then 45 seconds later. Resolver, authentication and hash
  errors are not retried.
- On Windows, run the `uv` installer in a separate PowerShell process with
  `-ExecutionPolicy Bypass`, the command uv's documentation gives. That
  installer calls `exit` when it fails, which would otherwise close your
  window. Your saved execution policy is not changed.
- On Windows, check that the installed Visual C++ runtime is at least as new
  as the newest MSVC toolset that built any installed `.dll` or `.pyd`. See
  [WinError 126](#windows-ocr-fails-with-winerror-126-loading-c10dll).

Once installed, `pdomain-ocr` itself only does the two outbound requests
listed above.

### Manual install

If you'd rather not pipe `curl | sh`, you can run the install yourself
with [uv](https://docs.astral.sh/uv/). The install script wraps
`uv tool install` against the wheel asset on the latest GitHub Release —
nothing here uses `pip`.

Install uv first:

```sh
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows (PowerShell): uv's documented command. Bypass applies only to
# this one child process.
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

CPU install (uses the self-hosted `pdomain-index-pip` PEP 503 index for
`pdomain-book-tools`):

```sh
uv tool install git+https://github.com/pdomain/pdomain-ocr-cli \
    --index-strategy first-index \
    --index pdomain=https://pdomain.github.io/pdomain-index-pip/simple/
```

NVIDIA GPU install. `--torch-backend auto` makes uv read your driver
version and pick the matching PyTorch CUDA build. Keep the `[gpu]` extra
only for **CUDA 13 or later**; on CUDA 12, drop the `--with` line:

```sh
uv tool install git+https://github.com/pdomain/pdomain-ocr-cli \
    --with 'pdomain-book-tools[gpu]' \
    --index-strategy first-index \
    --index pdomain=https://pdomain.github.io/pdomain-index-pip/simple/ \
    --torch-backend auto
```

These are the flags the installers use. A named `--index` with
`--index-strategy first-index` makes `pdomain-book-tools` resolve only from
the pdomain index, so another index cannot supply a package with that name.
`--torch-backend` needs a recent uv; if uv rejects it, run `uv self update`.

Do not add `download.pytorch.org/whl/cuXXX` as an extra `--index`. That
index also serves old copies of common packages such as `packaging` (24.1
at most). Under `first-index`, uv then takes those packages from it alone,
and the resolve fails because `pdomain-ops` needs `packaging>=26`.
`--torch-backend` sends only PyTorch packages to the PyTorch index.

The `[gpu]` extra on `pdomain-book-tools` 0.31.0 opts into `cupy-cuda13x`.
Use `nvidia-smi` to read your CUDA version.
Disk / VRAM budgets are below in
[GPU acceleration mechanics](#gpu-acceleration-mechanics).

In practice, re-running the install script is simpler — it does
the detection and assembles these flags for you.

### GPU acceleration mechanics

How the pieces fit together when you opt in:

- **`pdomain-ocr-cli`** — the app.
- **CUDA Toolkit** — NVIDIA's runtime that lets programs talk to
  your GPU. Required on Linux / Windows for the CUDA path; the
  Apple Silicon path uses Metal via PyTorch's MPS backend instead.
- **CUDA-enabled PyTorch wheels** — the same PyTorch you'd install
  on CPU, compiled to call into CUDA. The install script passes
  `--torch-backend auto`, and uv picks the build that matches your
  NVIDIA driver. (CUDA 13 or newer is required for the `[gpu]`
  extra.)
- **OCR / layout model weights** — downloaded on first run; not
  GPU-specific.

To pick a build yourself, pass an explicit value such as
`--torch-backend cu128` instead of `auto`; `uv tool install --help` lists
the values your uv knows.

Rough disk + memory budget for the NVIDIA path:

- CUDA Toolkit: ~2–4 GB download, ~5–12 GB installed (depends on
  the components you select).
- CUDA-enabled PyTorch wheels: ~1–3 GB on top.
- Runtime VRAM with both OCR + layout models loaded: a few GB —
  fits comfortably on any modern dedicated NVIDIA card.

---

## Development

Working on `pdomain-ocr-cli` itself? See [`DEVELOPMENT.md`](DEVELOPMENT.md) for the full
developer guide. It covers `just setup`, the editable side-by-side workflow with
`pdomain-book-tools` / `pdomain-ops` (`just local-setup`,
`just local-dev`), the project layout, and the release process.
Releases are blocked until all runtime dependencies, including
`pdomain-ops`, resolve from `pdomain-index-pip` instead of a local path.

Quick start:

```sh
git clone https://github.com/pdomain/pdomain-ocr-cli
cd pdomain-ocr-cli
just setup            # regular dev setup against the pinned pdomain-book-tools version
# — or —
just local-dev        # also clones ../pdomain-book-tools and installs it editable
```
