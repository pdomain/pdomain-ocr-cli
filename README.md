---
Status: active
Owner: CT
Created: 2026-05-03
Last verified: 2026-11-15
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

The installers cache the default models. A first OCR run fetches any missing
files. Once the files are cached, OCR can run offline without an account.
See the [network requests and model sources](#network-calls-the-tool-makes).

Supported Python versions for the package are `>=3.11,<3.14`. The
installer defaults to Python 3.13 for the managed `uv tool`
environment, but the wheel is tested on Python 3.11, 3.12, and 3.13.

---

## GPU acceleration (optional)

`pdomain-ocr` works fine on CPU. Add an NVIDIA GPU and it goes faster — worth
it when you're running through a whole book rather than one page.

> ⚠️ **Heads up — disk space.** The CUDA build of PyTorch is roughly
> 2–3 GB. CPU mode is smaller if disk space is tight.

- **NVIDIA on Linux/Windows** — install [driver 525 or newer](https://www.nvidia.com/en-us/drivers/), then run the install script. It reads `nvidia-smi` and downloads the matching PyTorch build. The steps are in the [GPU setup guide](https://github.com/pdomain/pdomain-ocr-simple-gui/blob/master/docs/usage/nvidia-gpu-setup.md). The installer does not install the driver.
- **Apple Silicon Mac** — kicks in automatically, nothing to install. *(Unverified — feedback welcome.)*
- **No GPU** — nothing to do; CPU is the default.

Already installed without a GPU? Re-run the install script — it
swaps the install in place. See the [FAQ](#faq) for switching to GPU,
the "PyTorch is the CPU build" nudge, troubleshooting, and
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

### Skip model downloads during installation

The installer caches the default detection, recognition, and layout files.
If you want to download them later, use the skip flag for your platform.

```sh
curl -fsSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh |
  sh -s -- --skip-models
```

```powershell
$installer = 'https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1'
& ([scriptblock]::Create((Invoke-RestMethod $installer))) -SkipModels
```

The skip flag also works with the update-check flag below. Run
`pdomain-ocr download-models` later to fill the cache, or let the first OCR run
fetch any missing files. If the installer cannot download a model, it warns
you and keeps the CLI installed.

### Install with automatic update checks

Automatic checks are off by default. To enable them during installation,
choose either the flag or the environment variable for your platform.

#### Linux and macOS

```sh
# Installer flag
curl -fsSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh |
  sh -s -- --auto-update-check

# Environment variable
curl -fsSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh |
  PD_OCR_INSTALL_AUTO_UPDATE_CHECK=1 sh
```

#### Windows PowerShell

```powershell
$installer = 'https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1'

# Installer flag
& ([scriptblock]::Create((Invoke-RestMethod $installer))) -AutoUpdateCheck

# Environment variable
$env:PD_OCR_INSTALL_AUTO_UPDATE_CHECK = '1'
Invoke-RestMethod $installer | Invoke-Expression
```

The installer saves your choice. If Windows asks you to restart, run
`pdomain-ocr update --auto-check on` after restarting. See the
[settings and precedence rules](docs/usage/cli-usage.md#automatic-update-checks).

---

## Update an installed CLI

`pdomain-ocr update --check` shows your installed version and the latest stable GitHub release.
Run `pdomain-ocr update` to review the new version and confirm installation. Use
`pdomain-ocr update --yes` for an unattended update.

The updater supports `uv tool` installations. It verifies the new CLI and
tries to restore the previous version if verification fails. On Windows,
exit code 0 acknowledges the handoff. Wait for the worker to report an
update, a rollback, or the need for recovery. If the update stops before
reporting a result, run the recovery command printed before activation.
For editable or package-managed installations, use the tool you originally
installed with.

If your installed version lacks the update command, rerun the [installer](#install).

Automatic update checks are off by default. See how to
[save or override that setting](docs/usage/cli-usage.md#automatic-update-checks).

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

Re-run the install script. It re-detects `nvidia-smi` on every run and
has uv pick the matching PyTorch CUDA build.
`uv tool install --reinstall` swaps the existing install in place.

```sh
# Linux / macOS
curl -sSL https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.sh | sh
```

```powershell
# Windows
irm https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1 | iex
```

### Why am I seeing a "GPU detected but PyTorch is the CPU build" message?

On startup, `pdomain-ocr` runs a cheap check. If your host has an NVIDIA GPU
(`nvidia-smi` on `PATH`, exits 0) but PyTorch cannot see CUDA, it prints a
one-line nudge to stderr. The nudge suggests the reinstall command. The
probe is fail-soft: it swallows any error and lets the OCR run proceed
normally.

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

- **`nvidia-smi` not found** — the NVIDIA driver is not available
  in your environment. Install [driver 525 or newer](https://www.nvidia.com/en-us/drivers/),
  then re-run the install script. The
  [GPU setup guide](https://github.com/pdomain/pdomain-ocr-simple-gui/blob/master/docs/usage/nvidia-gpu-setup.md)
  has the steps.
- **Running in Docker / devcontainer** — make sure the container was
  started with `--gpus all` and the NVIDIA Container Toolkit is
  configured on the host (see
  [Running in a Container](#running-in-a-container-with-nvidia-gpu)).
- **GPU still not used after that** — re-run the install script; it
  re-detects on each run.

See [how GPU installation works](docs/architecture/installation-and-updates.md#gpu-acceleration-mechanics)
for CUDA build selection and disk and memory estimates.

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

The first run initializes the OCR models. If the installer skipped a model or
could not fetch it, the first run downloads it. Later runs reuse the cache.

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

Use custom OCR and layout models only from sources you trust.
See [default model revisions and trust checks](docs/architecture/cli-orchestration.md#trust-and-network-boundaries).

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

The CLI uses Hugging Face for model files and GitHub for update checks.
It sends no usage telemetry. Once the models are cached, normal OCR runs
work offline with automatic update checks off.

The default weights come from the
[OCR model repository](https://huggingface.co/pdomain/pdomain-ocr-models)
and the [layout model repository](https://huggingface.co/CT2534/PP-DocLayout_plus-L).
See [installation and updates](docs/architecture/installation-and-updates.md)
for release verification, package sources, manual installation, and GPU details.

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
