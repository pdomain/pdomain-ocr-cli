---
Status: active
Owner: CT
Created: 2026-11-21
Last verified: 2026-11-21
Kind: architecture
---

# Installation and updates

The CLI installers verify the published wheel, install it with uv, and cache
the default OCR models. The CLI updater reuses these installers.

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing release installation, package sources, model prefetch, CUDA setup, Windows runtime checks, or CLI updates.
- **Search terms:** installer, sha256, first-index, Windows runtime, model cache, download-models, update, CUDA.

## Release installation and integrity

The POSIX and PowerShell installers install the wheel from the latest GitHub
Release. They pass the pdomain index to `uv` as a named `--index` with
`--index-strategy first-index`, so a package listed on the pdomain index, such
as `pdomain-book-tools`, cannot resolve from another index. PyPI stays in the
index list for packages the pdomain index does not list.

The installers require a lowercase `sha256:` digest with 64 hex characters
before downloading. They reject the wheel if its bytes do not match the digest.
GitHub supplies both the wheel and its digest. This check detects a corrupted
download. A replaced release asset could provide a matching digest. The
verification covers the wheel itself. Dependency packages follow uv's
normal download and install checks.

On Linux and macOS, `install.sh` uses authenticated `gh` when available. It
falls back to the REST API if `gh` cannot supply the wheel URL and digest.
The parser takes both fields from the wheel's asset record. CR and CRLF
separators between asset entries cannot associate the source archive's digest
with the wheel. The script preserves the caller's `TMPDIR` for uv.

Windows PowerShell 5.1 needs TLS 1.2 before the first request. Its piped
installer runs without a companion file and skips Unix file permissions.
If uv is missing, the Windows script runs the uv bootstrap in a child
PowerShell with process-scoped `-ExecutionPolicy Bypass`. The bootstrap can
exit on failure without closing the caller's window. The user's saved
execution policy stays in place. The shell installer checks that uv is on
`PATH` after bootstrapping it.

The installers retry when uv reports `Request failed after N retries`. They
wait 15 seconds before the second attempt and 45 seconds before the third.
`No solution found`, including index errors 401 and 403, fails immediately.
Authentication and integrity failures also stop the install. The shell installer
streams uv's output through `tee` and returns uv's exit code on failure.
PowerShell clears `$LASTEXITCODE` before native calls in the install loop and
throws when uv fails to start or returns an error. A failed install never prints
`Done`. Older uv versions that reject `--torch-backend` get an update hint.

## Windows Visual C++ runtime

After installing, `install.ps1` checks the Visual C++ runtime on Windows. It
reads the linker version of every `.dll` and `.pyd` in the tool environment,
skipping bundled runtime copies, and takes the newest MSVC 14.x version as the
floor. Microsoft requires the runtime to be at least as new as the toolset that
built a binary. The check compares the file versions of `msvcp140.dll`,
`vcruntime140.dll` and `vcruntime140_1.dll` in the 64-bit system directory with
that floor.

If a DLL is missing or too old, the installer downloads
`https://aka.ms/vc14/vc_redist.x64.exe`. It runs the file only if Authenticode
reports `Valid`, the signer's only organization field is exactly `Microsoft
Corporation`, and the chain ends at Microsoft Root Certificate Authority 2011,
thumbprint `8F43288AD272F3103B6FB1428485EA3014C0BCFE`. It holds the file open
for reading only, from the check until the installer exits, so the file cannot
be replaced in between. It then starts `/install /passive /norestart` through `Process.Start` with
the `runas` verb, the only elevated step. `Start-Process` is not used because
Windows PowerShell 5.1 drops the Windows error code when the user cancels
the prompt.

Exit codes 0 and 1638 count as installed. 3010 and 1641 finish with a restart
notice; the script never restarts Windows. 1602, 5, a cancelled prompt
(Windows error 1223), a missing exit code and any other code fail with manual
steps. `PD_OCR_SKIP_VC_RUNTIME=1` skips installation and gives the same steps.
A runtime still older than the floor after installation triggers a warning.

If the tool environment is missing, the check reports that it can only require
the three DLLs to exist. It skips unreadable files. The
[Windows proof](../research/2026-11-13-windows-installer-proof.md) records
the tested installer runs.

## Model cache and installer preferences

The installers run `uv tool install --reinstall <wheel>` and default to
Python 3.13. `PD_OCR_INSTALL_PYTHON` selects another
supported version. Apple Silicon installs use a native shell when possible.

After uv installs the wheel, the installer locates the new launcher with
`uv tool dir --bin`. It checks the launcher's help for `download-models`
before calling it. Older releases fall back to downloading models during OCR.
The download command uses the same pinned detection, recognition, and layout
sources as the default OCR run. The normal Hugging Face cache stores the files.
`--skip-models` and `-SkipModels` skip this step. Download failures warn and
leave the CLI installed. A Windows runtime restart defers prefetch.

The installer saves an automatic-check preference only when requested.
`--auto-update-check` and `-AutoUpdateCheck` take precedence over
`PD_OCR_INSTALL_AUTO_UPDATE_CHECK`. Omitting both preserves the existing file.
If the Windows runtime needs a restart, the installer prints the CLI command
to save the requested preference after restarting.
For config paths and runtime precedence, see the
[usage guide](../usage/cli-usage.md#automatic-update-checks).

## Update check and installation

The explicit update command reads GitHub's latest stable release and compares
it with the installed version. `--check` stops after the comparison. Apply
requires a uv-managed tool installation and confirmation or `--yes`.
The launcher passes the approved release tag to the bundled installer, which
stops before downloading if the resolved tag changed. The updater preserves
the current Python minor version unless the installer Python setting overrides
it. It leaves the saved automatic-check preference in place.

The bundled installer stages the verified wheel before taking the live uv
lock. The updater creates a private environment with `uv venv --relocatable`
on the live installation filesystem. It installs the staged wheel there so
dependency installation cannot compete for the live lock. The updater maps
the staged receipt to the existing launcher and checks runtime prerequisites.
On Windows, PowerShell waits for the CLI and its launcher to exit before
starting the activation worker.

The worker runs outside the tool environment and takes uv's live directory
lock and waits for running OCR commands to release their shared lock.
It parks the old environment on the same filesystem, outside the directory
where uv discovers installed tools. It moves the candidate into the original
path. The existing launcher still targets that path, so it stays in place.
The worker checks the exact approved version and imports the OCR runtime
without loading models. If either check fails, the worker attempts to restore
the old environment offline. A failed restore leaves the journal and any
parked environment available for recovery.

The CLI prints a recovery command before activation. It calls the worker
through a Python interpreter outside the replaceable environment. The worker
flushes the phase record before each move and flushes the affected directories
afterward. On Windows, it also requests a write-through directory move.
Recovery takes the same locks and checks the recorded identities.
It leaves the backup in place if an external command changed the installation.

The opt-in background check reads `/repos/pdomain/pdomain-ocr-cli/tags?per_page=100`
from GitHub with a three-second timeout. It prints a notice to stderr when a
newer stable tag exists. The explicit update command reads
`/repos/pdomain/pdomain-ocr-cli/releases/latest`. Model files come from Hugging Face.
See [CLI orchestration](cli-orchestration.md#trust-and-network-boundaries)
for checkpoint trust and background-check diagnostics.

### Update verification

The Linux and native Windows installed-wheel tests covered activation after
a running command released its shared lock. On Windows, prefetch reused
cached models in the offline test. The Windows tests
also covered wrong-version rollback and recovery after interrupting the
worker following either directory move. The public launcher stayed in
place. Sudden power loss remains untested.

- Implementation: [update command](../../pdomain_ocr_cli/_self_update.py),
  [candidate staging](../../pdomain_ocr_cli/_update_stage.py), and
  [activation worker](../../pdomain_ocr_cli/_update_worker.py).
- Regression coverage: [CLI update](../../tests/test_cli_update.py),
  [staging](../../tests/test_update_stage.py), and
  [worker recovery](../../tests/test_update_worker_validation.py).

## Manual installation from source

The commands below install from the repository with [uv](https://docs.astral.sh/uv/).
For the published release, use the [install guide](../../README.md#install).

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
version and pick the matching PyTorch CUDA build:

```sh
uv tool install git+https://github.com/pdomain/pdomain-ocr-cli \
    --index-strategy first-index \
    --index pdomain=https://pdomain.github.io/pdomain-index-pip/simple/ \
    --torch-backend auto
```

The named index follows the same [package-source rule](#release-installation-and-integrity)
as the installers. If uv rejects `--torch-backend`, run `uv self update`.

Do not add `download.pytorch.org/whl/cuXXX` as an extra `--index`. That
index also serves old copies of common packages such as `packaging` (24.1
at most). Under `first-index`, uv then takes those packages from it alone,
and the resolve fails because `pdomain-ops` needs `packaging>=26`.
`--torch-backend` sends only PyTorch packages to the PyTorch index.

## GPU acceleration mechanics

On Linux and Windows, the installers use `nvidia-smi` to detect the NVIDIA
driver and reported CUDA version. When detection succeeds, uv selects the
PyTorch CUDA build through `--torch-backend auto`. Apple Silicon uses
PyTorch's MPS backend. CPU and GPU runs use the same OCR and layout models.
The CLI does not need CuPy.

To pick a build yourself, pass an explicit value such as
`--torch-backend cu128` instead of `auto`; `uv tool install --help` lists
the values your uv knows.

Rough disk + memory budget for the NVIDIA path:

- If you install the standalone CUDA Toolkit, allow roughly 2 to 4 GB
  for the download and 5 to 12 GB on disk. The selected components affect size.
- CUDA-enabled PyTorch wheels add roughly 1 to 3 GB.
- Running OCR with layout detection can use a few GB of GPU memory.
