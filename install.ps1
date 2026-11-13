# Install pdomain-ocr as a standalone tool using uv.
#
# Usage (run in PowerShell):
#   irm https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1 | iex
#
# Manual CUDA override (if auto-detection fails):
#   $env:CUDA_VERSION = "13.0"   # replace with your version
#   irm https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1 | iex
#
# Python override:
#   $env:PD_OCR_INSTALL_PYTHON = "3.12"
#   irm https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1 | iex

$ErrorActionPreference = "Stop"

# Windows PowerShell 5.1 can default to TLS versions GitHub refuses. -bor keeps
# whatever else the session already allows.
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

function Get-CudaVersion {
    if ($env:CUDA_VERSION) {
        return $env:CUDA_VERSION
    }

    if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
        return $null
    }

    try {
        $Query = & nvidia-smi -q 2>$null | Out-String
        if ($Query -match "CUDA Version\s*:\s*([0-9]+\.[0-9]+)") {
            return $Matches[1]
        }
    } catch {
    }

    try {
        $Plain = & nvidia-smi 2>$null | Out-String
        if ($Plain -match "CUDA Version:\s*([0-9]+\.[0-9]+)") {
            return $Matches[1]
        }
    } catch {
    }

    return $null
}

function Get-CudaTag {
    param([Parameter(Mandatory = $true)][string]$CudaVer)
    return "cu" + ($CudaVer -replace "\.", "")
}

function Get-BookToolsExtras {
    param([Parameter(Mandatory = $true)][string]$CudaVer)
    try {
        $Version = [version]$CudaVer
    } catch {
        return ""
    }
    if ($Version.Major -ge 13) {
        return "[gpu]"
    }
    return ""
}

$HelperPath = $null
if ($PSScriptRoot) {
    $HelperPath = Join-Path $PSScriptRoot "scripts/install-cuda-detect.ps1"
}
if ($HelperPath -and (Test-Path $HelperPath)) {
    . $HelperPath
}

$Repo = "pdomain/pdomain-ocr-cli"
$PdIndexUrl = "https://pdomain.github.io/pdomain-index-pip/simple/"
$PythonVersion = if ($env:PD_OCR_INSTALL_PYTHON) { $env:PD_OCR_INSTALL_PYTHON } else { "3.13" }

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found -- installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + $env:PATH
}

$ExtraIndex = ""
$BookToolsExtras = ""

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $CudaVer = Get-CudaVersion

    if ($CudaVer) {
        $CudaTag = Get-CudaTag $CudaVer
        $ExtraIndex = "https://download.pytorch.org/whl/$CudaTag"
        Write-Host "Detected CUDA $CudaVer -- will install PyTorch with $CudaTag support."

        $BookToolsExtras = Get-BookToolsExtras $CudaVer
        if ($BookToolsExtras -eq "[gpu]") {
            Write-Host "CUDA $CudaVer >= 13 -- enabling pdomain-book-tools[gpu] (cupy-cuda13x)."
        } else {
            Write-Host "CUDA $CudaVer < 13 -- installing CPU-only book-tools (cupy-cuda13x needs CUDA 13)."
        }
    } else {
        Write-Host ""
        Write-Host "WARNING: NVIDIA GPU detected but CUDA version could not be determined."
        Write-Host "         Installing CPU-only build of pdomain-ocr."
        Write-Host ""
        Write-Host "         To install the GPU build instead, re-run with a manual override:"
        Write-Host "           `$env:CUDA_VERSION = `"13.0`"   # replace with your CUDA version"
        Write-Host "           irm https://raw.githubusercontent.com/pdomain/pdomain-ocr-cli/master/install.ps1 | iex"
        Write-Host ""
        Write-Host "         Find your CUDA version by running:  nvidia-smi"
        Write-Host "         and looking for the 'CUDA Version' field in the output."
        Write-Host ""
    }
} else {
    Write-Host "No GPU detected -- installing CPU-only PyTorch."
}

$ReleaseUrl = "https://api.github.com/repos/$Repo/releases/latest"
Write-Host "Resolving latest release via GitHub API..."
$Release = Invoke-RestMethod -Uri $ReleaseUrl
$ReleaseTag = $Release.tag_name
$WheelAsset = $Release.assets |
    Where-Object { $_.name -like "*.whl" -or $_.browser_download_url -like "*.whl" } |
    Select-Object -First 1

if (-not $WheelAsset) {
    throw "Latest release $ReleaseTag has no wheel asset attached."
}

$WheelUrl = $WheelAsset.browser_download_url
$WheelName = if ($WheelAsset.name) {
    $WheelAsset.name
} else {
    Split-Path -Leaf ([Uri]$WheelUrl).AbsolutePath
}

# Fail closed on any missing or malformed digest, before downloading. A
# digest that is absent or not a well-formed sha256 means we cannot verify
# the wheel we're about to fetch, so refuse rather than install unverified.
# Use the case-SENSITIVE -cnotmatch: plain -notmatch is case-insensitive in
# PowerShell, which would accept uppercase hex here while install.sh (grep,
# case-sensitive by default) rejects it — the spec requires lowercase only,
# and both installers must agree on what they accept.
$WheelDigest = $WheelAsset.digest
if (-not $WheelDigest -or $WheelDigest -cnotmatch '^sha256:[0-9a-f]{64}$') {
    throw "Latest release $ReleaseTag wheel asset '$WheelName' has no verifiable sha256 digest (got: '$WheelDigest'). Refusing to install an unverified wheel."
}
$WheelDigestHex = $WheelDigest.Substring(7)

Write-Host "Latest release: $ReleaseTag"
Write-Host "Wheel asset:    $WheelUrl"
Write-Host "Wheel digest:   $WheelDigest"
Write-Host "pdomain-index-pip:       $PdIndexUrl"

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("pdomain-ocr-install-" + [guid]::NewGuid().ToString("N"))
$TempDirItem = New-Item -ItemType Directory -Path $TempDir
# Windows PowerShell 5.1 has no $IsWindows. An unset variable is falsy, so
# `-not $IsWindows` alone enters this branch and aborts on UnixFileMode
# before the download. UnixFileMode exists only on PowerShell 6+ off Windows.
if ($PSVersionTable.PSVersion.Major -ge 6 -and -not $IsWindows) {
    # New-Item's directory mode follows umask (e.g. 0777 at umask 0) — unlike
    # `mktemp -d`, which is always 0700. Without this, another local user
    # could replace the downloaded wheel between the Get-FileHash check below
    # and the `uv tool install` call, defeating digest verification.
    $TempDirItem.UnixFileMode = [System.IO.UnixFileMode]::UserRead -bor
        [System.IO.UnixFileMode]::UserWrite -bor
        [System.IO.UnixFileMode]::UserExecute
}

try {
    $WheelFile = Join-Path $TempDir $WheelName
    Write-Host "Downloading wheel..."
    Invoke-WebRequest -Uri $WheelUrl -OutFile $WheelFile

    # Verify the downloaded wheel against the digest GitHub reported for it,
    # BEFORE calling `uv tool install`. A digest that doesn't match the bytes
    # we actually fetched means the download was tampered with or corrupted;
    # either way, installing it would be worse than failing here.
    $WheelActualHex = (Get-FileHash -Algorithm SHA256 -Path $WheelFile).Hash.ToLowerInvariant()
    if ($WheelActualHex -ne $WheelDigestHex) {
        throw "Wheel digest mismatch for $WheelFile.`n  expected: sha256:$WheelDigestHex`n  actual:   sha256:$WheelActualHex"
    }
    Write-Host "Digest verified: sha256:$WheelActualHex"

    Write-Host "Installing pdomain-ocr $ReleaseTag from $WheelName..."
    # "first-index" makes uv stop looking once a package name resolves on an
    # index, in index-URL order. The pdomain index is bound via a named
    # `--index` (not the deprecated `--extra-index-url`): uv ranks
    # --index/UV_INDEX strictly above --extra-index-url, and passing --index
    # explicitly on the CLI replaces (rather than merges with) any UV_INDEX
    # the environment supplies. Verified against real uv 0.11.32 with local
    # decoy indexes: a hostile UV_INDEX env var beats --extra-index-url but
    # cannot beat this --index binding, and the pdomain --index is always
    # listed before the CUDA extra --index below, so it's still checked
    # first under first-index.
    $UvArgs = @(
        "tool", "install", "--python", $PythonVersion, "--reinstall", $WheelFile,
        "--index-strategy", "first-index", "--index", "pdomain=$PdIndexUrl"
    )
    if ($BookToolsExtras) {
        $UvArgs += @("--with", "pdomain-book-tools$BookToolsExtras")
    }
    if ($ExtraIndex) {
        $UvArgs += @("--index", "pytorch-cuda=$ExtraIndex")
    }
    & uv @UvArgs
} finally {
    Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Done! Run: pdomain-ocr page.png"
Write-Host "If 'pdomain-ocr' is not found, ensure uv's tool bin is on your PATH."
Write-Host "  uv tool update-shell"
