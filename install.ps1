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

param(
    [switch]$AutoUpdateCheck,
    [switch]$SkipModels,
    [string]$PrepareUpdate,
    [string]$CheckStagedRuntime,
    [switch]$ProbeVcRuntimeRegistration,
    [switch]$Uninstall,
    [switch]$UninstallPreview,
    [switch]$RemoveVcRuntime,
    [switch]$RemoveUv,
    [switch]$RemoveModels,
    [switch]$RemovePython
)

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
        if ($Query -match "CUDA (?:UMD )?Version\s*:\s*([0-9]+\.[0-9]+)") {
            return $Matches[1]
        }
    } catch {
    }

    try {
        $Plain = & nvidia-smi 2>$null | Out-String
        if ($Plain -match "CUDA (?:UMD )?Version:\s*([0-9]+\.[0-9]+)") {
            return $Matches[1]
        }
    } catch {
    }

    return $null
}

function Write-GpuSetupHint {
    Write-Host "This installer does not install the NVIDIA driver. OCR still works on CPU."
    Write-Host "To use an NVIDIA GPU:"
    Write-Host "  1. Install driver 525 or newer: https://www.nvidia.com/en-us/drivers/"
    Write-Host "  2. Reboot if the driver installer asks you to."
    Write-Host "  3. Run nvidia-smi and confirm it lists the GPU."
    Write-Host "  4. Run this installer again. It downloads the CUDA build of PyTorch."
    Write-Host "Step-by-step: https://github.com/pdomain/pdomain-ocr-simple-gui/blob/master/docs/usage/nvidia-gpu-setup.md"
}

# The functions below have no side effects when defined. Tests load them from
# this file's syntax tree and replace the cmdlets they call with fakes.

function Test-IsWindowsHost {
    # Windows PowerShell 5.1 has no $IsWindows; it only runs on Windows.
    return ($PSVersionTable.PSVersion.Major -lt 6) -or [bool]$IsWindows
}

function Install-Uv {
    # Run astral's uv installer in a child PowerShell, the command uv's own
    # documentation gives for Windows. That installer calls `exit 1` when it
    # fails, and under `irm | iex` an exit in this window would close it.
    # `-ExecutionPolicy Bypass` applies to the child process only; the
    # user's saved policy is not changed.
    param([string]$ShellPath = (Get-Process -Id $PID).Path, [string]$StagingPath)
    $global:LASTEXITCODE = $null
    $PreviousUnmanaged = $env:UV_UNMANAGED_INSTALL
    $PreviousInstall = $env:UV_INSTALL_DIR
    $PreviousLegacy = $env:CARGO_DIST_FORCE_INSTALL_DIR
    try {
        if ($StagingPath) {
            $env:UV_UNMANAGED_INSTALL = $StagingPath
            $env:UV_INSTALL_DIR = $null
            $env:CARGO_DIST_FORCE_INSTALL_DIR = $null
        }
        & $ShellPath -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" |
            ForEach-Object { Write-Host $_ }
    } finally {
        $env:UV_UNMANAGED_INSTALL = $PreviousUnmanaged
        $env:UV_INSTALL_DIR = $PreviousInstall
        $env:CARGO_DIST_FORCE_INSTALL_DIR = $PreviousLegacy
    }
    if ($LASTEXITCODE -ne 0) {
        throw "The uv installer failed (exit code $LASTEXITCODE); see its message above. If your organization sets the PowerShell execution policy, ask an administrator to install uv: https://docs.astral.sh/uv/getting-started/installation/"
    }
}

function Get-WindowsUvDestination {
    $Forced = $env:UV_INSTALL_DIR
    if (-not $Forced) {
        $Forced = $env:CARGO_DIST_FORCE_INSTALL_DIR
    }
    if (-not $Forced) {
        $Forced = $env:UV_UNMANAGED_INSTALL
    }
    if ($Forced) {
        $CargoHome = if ($env:CARGO_HOME) { $env:CARGO_HOME } else { Join-Path $HOME ".cargo" }
        if ([IO.Path]::GetFullPath($Forced) -eq [IO.Path]::GetFullPath($CargoHome)) {
            $Forced = Join-Path $Forced "bin"
        }
        return [IO.Path]::GetFullPath($Forced)
    }
    if ($env:XDG_BIN_HOME) {
        return [IO.Path]::GetFullPath($env:XDG_BIN_HOME)
    }
    if ($env:XDG_DATA_HOME) {
        return [IO.Path]::GetFullPath((Join-Path $env:XDG_DATA_HOME "../bin"))
    }
    return Join-Path $HOME ".local/bin"
}

function Initialize-WindowsUv {
    param([Parameter(Mandatory = $true)][string]$WorkDir)
    $Destination = Get-WindowsUvDestination
    $Uv = Join-Path $Destination "uv.exe"
    if (Test-Path -LiteralPath $Uv -PathType Leaf) {
        $env:PATH = $Destination + [IO.Path]::PathSeparator + $env:PATH
        return
    }
    $Staging = Join-Path $WorkDir "uv-bootstrap"
    Install-Uv -StagingPath $Staging
    if (-not (Test-Path -LiteralPath (Join-Path $Staging "uv.exe") -PathType Leaf)) {
        throw "The uv installer finished without producing uv.exe."
    }
    $Bootstrap = [pscustomobject]@{
        Destination = $Destination
        Staging = $Staging
        OriginalPath = $env:PATH
        ModifyPath = -not ($env:UV_NO_MODIFY_PATH -or $env:UV_UNMANAGED_INSTALL)
    }
    $env:PATH = $Staging + [IO.Path]::PathSeparator + $env:PATH
    return $Bootstrap
}

function Publish-WindowsUv {
    param([string]$EnvironmentPath, $Bootstrap)
    $Python = Join-Path $EnvironmentPath "Scripts/python.exe"
    $Code = @"
import sys
from pathlib import Path

try:
    from pdomain_ops.suite.component_files import install_staged_uv
    from pdomain_ops.suite.components import ComponentRegistry
except ModuleNotFoundError:
    raise SystemExit(77)

stage, destination = map(Path, sys.argv[1:])
registry = ComponentRegistry()
app = "pdomain-ocr-cli"
main = install_staged_uv(registry, app, stage / "uv.exe", destination / "uv.exe")
if main is not None:
    for name in ("uvx.exe", "uvw.exe"):
        if (stage / name).is_file():
            install_staged_uv(registry, app, stage / name, destination / name)
"@
    $Code | & $Python -I - $Bootstrap.Staging $Bootstrap.Destination
    if ($LASTEXITCODE -eq 77) {
        # Previously released wheels work without the component registry. Use a
        # same-directory rename so an existing executable is never overwritten.
        New-Item -ItemType Directory -Path $Bootstrap.Destination -Force | Out-Null
        foreach ($Name in @("uv.exe", "uvx.exe", "uvw.exe")) {
            $Source = Join-Path $Bootstrap.Staging $Name
            $Destination = Join-Path $Bootstrap.Destination $Name
            if (-not (Test-Path -LiteralPath $Source -PathType Leaf) -or
                (Test-Path -LiteralPath $Destination)) {
                continue
            }
            $Candidate = Join-Path $Bootstrap.Destination (".uv-stage-" + [guid]::NewGuid().ToString("N"))
            try {
                [IO.File]::Copy($Source, $Candidate)
                [IO.File]::Move($Candidate, $Destination)
            } catch [IO.IOException] {
                if (-not (Test-Path -LiteralPath $Destination -PathType Leaf)) {
                    throw
                }
            } finally {
                Remove-Item -LiteralPath $Candidate -Force -ErrorAction SilentlyContinue
            }
        }
    } elseif ($LASTEXITCODE -ne 0) {
        throw "Could not publish the staged uv installation."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Bootstrap.Destination "uv.exe") -PathType Leaf)) {
        throw "Could not find the persistent uv installation."
    }
    $env:PATH = $Bootstrap.Destination + [IO.Path]::PathSeparator + $Bootstrap.OriginalPath
    if ($Bootstrap.ModifyPath) {
        try {
            Add-WindowsUserPath -Directory $Bootstrap.Destination
        } catch {
            Write-Warning "Could not add uv to your user PATH. Add this directory manually: $($Bootstrap.Destination)"
        }
    }
}

function Add-WindowsUserPath {
    param([string]$Directory)
    $UserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ([Environment]::ExpandEnvironmentVariables("$UserPath") -split ";" -notcontains $Directory) {
        $NewPath = if ($UserPath) { "$Directory;$UserPath" } else { $Directory }
        [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    }
}

function Invoke-NativeCaptured {
    # Run a native command, echo its stdout and stderr as it runs, and return
    # the exit code with the combined text. Stderr lines must not become
    # terminating errors, so the error preference is relaxed for this call.
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @()
    )
    $Lines = New-Object System.Collections.Generic.List[string]
    $PreviousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    # A command that never starts leaves $LASTEXITCODE at the previous
    # command's value, often 0, so clear it first.
    $global:LASTEXITCODE = $null
    try {
        try {
            & $FilePath @ArgumentList 2>&1 | ForEach-Object {
                $Line = "$_"
                Write-Host $Line
                $Lines.Add($Line)
            }
        } catch {
            throw "Could not run '$FilePath': $($_.Exception.Message)"
        }
        $ExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreviousPreference
    }
    if ($null -eq $ExitCode) {
        throw "'$FilePath' did not report an exit code, so it may not have run."
    }
    return [pscustomobject]@{
        ExitCode = $ExitCode
        Output = ($Lines -join "`n")
    }
}

function Test-UvLacksTorchBackend {
    # A uv older than the --torch-backend option rejects it, for example
    # "unexpected argument '--torch-backend' found". Updating uv is the fix;
    # retrying cannot help.
    param([string]$Output)
    return $Output -match "torch-backend"
}

function Test-UvTransientFailure {
    # uv retries network errors itself and reports "Request failed after N
    # retries" once it gives up; that is the only failure worth retrying.
    # A resolver failure ("No solution found"), including one caused by a
    # 401/403 index, a hash mismatch or an incompatible Python, is permanent.
    param([string]$Output)
    if ($Output -match "No solution found") {
        return $false
    }
    return $Output -match "Request failed after \d+ retr"
}

function Invoke-UvToolInstall {
    # Run `uv tool install`, retrying only uv-reported network failures. uv
    # already retried each request three times; the extra attempts wait
    # longer, for an index that is down for a minute rather than a moment.
    param(
        [Parameter(Mandatory = $true)][string[]]$UvArgs,
        [int[]]$RetryDelaysSeconds = @(15, 45)
    )
    $MaxAttempts = $RetryDelaysSeconds.Count + 1
    for ($Attempt = 1; $Attempt -le $MaxAttempts; $Attempt++) {
        $Result = Invoke-NativeCaptured -FilePath "uv" -ArgumentList $UvArgs
        if ($Result.ExitCode -eq 0) {
            return
        }
        if (Test-UvLacksTorchBackend $Result.Output) {
            throw "uv tool install failed with exit code $($Result.ExitCode). pdomain-ocr was not installed. This uv is too old for the --torch-backend option, which picks the PyTorch CUDA build. Run: uv self update (or update uv with the package manager that installed it). Then run the installer again."
        }
        $Transient = Test-UvTransientFailure $Result.Output
        if (-not $Transient) {
            throw "uv tool install failed with exit code $($Result.ExitCode). pdomain-ocr was not installed. See the uv error above."
        }
        if ($Attempt -eq $MaxAttempts) {
            throw "uv tool install failed with exit code $($Result.ExitCode) after $MaxAttempts attempts because of network errors. pdomain-ocr was not installed. Check your connection, then run the installer again."
        }
        $Delay = $RetryDelaysSeconds[$Attempt - 1]
        Write-Host ""
        Write-Host "uv could not reach a package index (attempt $Attempt of $MaxAttempts). Trying again in $Delay seconds..."
        Start-Sleep -Seconds $Delay
    }
}

function Get-PeLinkerVersion {
    # Return the linker version in a PE file's optional header, or $null when
    # the file is not a PE image. MSVC's linker version equals its toolset
    # version, for example 14.42 for Visual Studio 2022 17.12.
    param([Parameter(Mandatory = $true)][string]$Path)
    $Stream = [System.IO.File]::OpenRead($Path)
    try {
        $Reader = New-Object System.IO.BinaryReader($Stream)
        if ($Stream.Length -lt 0x40 -or $Reader.ReadUInt16() -ne 0x5A4D) {
            return $null
        }
        $Stream.Position = 0x3C
        $PeOffset = $Reader.ReadInt32()
        if ($PeOffset -lt 0x40 -or ($PeOffset + 28) -gt $Stream.Length) {
            return $null
        }
        $Stream.Position = $PeOffset
        if ($Reader.ReadUInt32() -ne 0x00004550) {
            return $null
        }
        # Signature (4) + COFF header (20) + optional-header magic (2).
        $Stream.Position = $PeOffset + 26
        $Major = [int]$Reader.ReadByte()
        $Minor = [int]$Reader.ReadByte()
        return New-Object System.Version($Major, $Minor)
    } finally {
        $Stream.Dispose()
    }
}

function Get-MsvcToolsetFloor {
    # The Visual C++ runtime must be at least as new as the newest MSVC
    # toolset that built any installed binary. Microsoft documents this rule:
    # https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
    # Read it from the installed files instead of fixing a version here:
    # torch 2.15.0, for example, was linked with toolset 14.42.
    param([Parameter(Mandatory = $true)][string]$EnvironmentPath)
    $RuntimeNames = @("msvcp140", "vcruntime140", "concrt140", "vccorlib140")
    $Floor = $null
    $Newest = $null
    if (-not (Test-Path -LiteralPath $EnvironmentPath -PathType Container)) {
        return [pscustomobject]@{ Version = $null; File = $null; Found = $false }
    }
    Get-ChildItem -Path $EnvironmentPath -Recurse -File -Include "*.dll", "*.pyd" -ErrorAction SilentlyContinue |
        ForEach-Object {
            $Base = $_.BaseName.ToLowerInvariant()
            $IsRuntimeCopy = $false
            foreach ($Name in $RuntimeNames) {
                if ($Base.StartsWith($Name)) { $IsRuntimeCopy = $true }
            }
            if (-not $IsRuntimeCopy) {
                $Linker = $null
                try {
                    $Linker = Get-PeLinkerVersion -Path $_.FullName
                } catch {
                    # A locked or unreadable file cannot raise the floor.
                }
                if ($Linker -and $Linker.Major -eq 14 -and (-not $Floor -or $Linker -gt $Floor)) {
                    $Floor = $Linker
                    $Newest = $_.FullName
                }
            }
        }
    return [pscustomobject]@{ Version = $Floor; File = $Newest; Found = $true }
}

function Get-VcRuntimeFileVersions {
    # File versions of the x64 runtime DLLs that PyTorch loads from the
    # system directory. A missing DLL maps to $null.
    $SystemDir = Join-Path $env:SystemRoot "System32"
    if (-not [Environment]::Is64BitProcess) {
        # A 32-bit PowerShell sees SysWOW64 as System32; Sysnative is the
        # real 64-bit directory.
        $SystemDir = Join-Path $env:SystemRoot "Sysnative"
    }
    $Versions = [ordered]@{}
    foreach ($Name in @("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll")) {
        $Path = Join-Path $SystemDir $Name
        if (Test-Path -LiteralPath $Path) {
            $Info = (Get-Item -LiteralPath $Path).VersionInfo
            $Versions[$Name] = New-Object System.Version($Info.FileMajorPart, $Info.FileMinorPart)
        } else {
            $Versions[$Name] = $null
        }
    }
    return $Versions
}

function Get-VcRuntimeStatus {
    # Decide whether the installed x64 runtime satisfies $Minimum (a
    # major.minor version, or $null to require only that the DLLs exist).
    param([System.Version]$Minimum)
    $Versions = Get-VcRuntimeFileVersions
    $Missing = @($Versions.Keys | Where-Object { -not $Versions[$_] })
    $Oldest = $null
    foreach ($Name in $Versions.Keys) {
        $Version = $Versions[$Name]
        if ($Version -and (-not $Oldest -or $Version -lt $Oldest)) { $Oldest = $Version }
    }
    $Adequate = ($Missing.Count -eq 0) -and ((-not $Minimum) -or ($Oldest -ge $Minimum))
    return [pscustomobject]@{
        Adequate = $Adequate
        Missing = $Missing
        Installed = $Oldest
        Minimum = $Minimum
    }
}

function Get-CertificateOrganizations {
    # Every O= value in a certificate subject, one per relative name. A
    # quoted value that contains ", O=..." stays inside its own field.
    param([Parameter(Mandatory = $true)]$Certificate)
    $Fields = $Certificate.SubjectName.Format($true) -split "`r?`n"
    foreach ($Field in $Fields) {
        $Clean = $Field.Trim().TrimEnd(",").Trim()
        if ($Clean.StartsWith("O=")) {
            $Clean.Substring(2)
        }
    }
}

function Get-CertificateRootThumbprint {
    # Thumbprint of the root at the end of the certificate's chain. Windows
    # already checked revocation for Get-AuthenticodeSignature.
    param([Parameter(Mandatory = $true)]$Certificate)
    $Chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
    try {
        $Chain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
        $null = $Chain.Build($Certificate)
        $Elements = $Chain.ChainElements
        return $Elements[$Elements.Count - 1].Certificate.Thumbprint
    } finally {
        $Chain.Dispose()
    }
}

function Assert-MicrosoftSignature {
    # Require a valid Authenticode signature whose signer's only
    # organization is exactly "Microsoft Corporation" and whose chain ends at
    # Microsoft Root Certificate Authority 2011. That root signed
    # vc_redist.x64.exe 14.52.37029 on 2026-11-13. A root a user added to
    # their own store cannot pass this check.
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string[]]$TrustedRoots = @("8F43288AD272F3103B6FB1428485EA3014C0BCFE")
    )
    $Signature = Get-AuthenticodeSignature -FilePath $Path
    $Certificate = $Signature.SignerCertificate
    if ("$($Signature.Status)" -ne "Valid" -or -not $Certificate) {
        throw "The downloaded Visual C++ Redistributable is not validly signed (status '$($Signature.Status)'). It was not run."
    }
    $Organizations = @(Get-CertificateOrganizations -Certificate $Certificate)
    if ($Organizations.Count -ne 1 -or $Organizations[0] -cne "Microsoft Corporation") {
        throw "The downloaded Visual C++ Redistributable is signed by '$($Certificate.Subject)', not Microsoft Corporation. It was not run."
    }
    $Root = Get-CertificateRootThumbprint -Certificate $Certificate
    if ($TrustedRoots -notcontains $Root) {
        throw "The downloaded Visual C++ Redistributable's signature chains to root '$Root', not Microsoft Root Certificate Authority 2011. It was not run."
    }
    Write-Host "Signature verified: $($Certificate.Subject)"
}

function Start-ElevatedInstaller {
    # Start a program with the "runas" verb, wait, and return its exit code.
    # Process.Start is used instead of Start-Process: Windows PowerShell 5.1's
    # Start-Process turns a cancelled UAC prompt into an InvalidOperationException
    # without the Windows error code, while Process.Start raises a
    # Win32Exception carrying 1223 (seen on Windows 11, 2026-11-13).
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Arguments
    )
    $Info = New-Object System.Diagnostics.ProcessStartInfo
    $Info.FileName = $FilePath
    $Info.Arguments = $Arguments
    $Info.Verb = "runas"
    $Info.UseShellExecute = $true
    $Process = [System.Diagnostics.Process]::Start($Info)
    try {
        $Process.WaitForExit()
        return $Process.ExitCode
    } finally {
        $Process.Dispose()
    }
}

function Test-UacCancelled {
    # True when any exception in the chain is Windows error 1223, "the
    # operation was cancelled by the user".
    param($Exception)
    for ($Current = $Exception; $Current; $Current = $Current.InnerException) {
        $Native = $Current -as [System.ComponentModel.Win32Exception]
        if ($Native -and $Native.NativeErrorCode -eq 1223) {
            return $true
        }
    }
    return $false
}

function Select-VcRuntimeRegistration {
    param([object[]]$Entries)
    foreach ($Entry in $Entries) {
        if ($Entry.Publisher -cne "Microsoft Corporation" -or
            $Entry.DisplayName -notmatch '^Microsoft Visual C\+\+ [0-9]{4}(?:-[0-9]{4})? Redistributable \(x64\) - 14\.[0-9.]+$' -or
            $Entry.DisplayVersion -notmatch '^14\.[0-9]+\.[0-9]+(?:\.[0-9]+)?$') {
            continue
        }
        $PackageId = [guid]::Empty
        if (-not [guid]::TryParseExact($Entry.PSChildName, "B", [ref]$PackageId)) {
            continue
        }
        $UninstallPath = $null
        if ($Entry.UninstallString -match '^"([A-Za-z]:\\[^"]+\\VC_redist\.x64\.exe)"\s+/uninstall(?:\s+/[^\s]+)*\s*$') {
            $UninstallPath = $Matches[1]
        }
        [pscustomobject]@{
            PackageId = $PackageId.ToString("D")
            Version = $Entry.DisplayVersion
            Architecture = "x64"
            UninstallPath = $UninstallPath
        }
    }
}

function Get-VcRuntimeRegistration {
    $Entries = @(
        foreach ($Location in @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        )) {
            if (Test-Path -LiteralPath $Location) {
                Get-ChildItem -LiteralPath $Location | Get-ItemProperty
            }
        }
    )
    Select-VcRuntimeRegistration -Entries $Entries | Sort-Object PackageId, Version -Unique
}

function Register-VcRuntimeClaim {
    param([Parameter(Mandatory = $true)][string]$EnvironmentPath, [switch]$InstalledHere)
    $Previous = $env:PDOMAIN_OCR_VC_RUNTIME_CLAIM
    $PreviousCreated = $env:PDOMAIN_OCR_VC_RUNTIME_CREATED
    try {
        $Python = [System.IO.Path]::Combine($EnvironmentPath, "Scripts", "python.exe")
        if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
            return
        }
        $Packages = @(Get-VcRuntimeRegistration)
        if ($Packages.Count -ne 1) {
            return
        }
        $env:PDOMAIN_OCR_VC_RUNTIME_CLAIM = ConvertTo-Json -InputObject $Packages[0] -Compress
        $env:PDOMAIN_OCR_VC_RUNTIME_CREATED = if ($InstalledHere) { "1" } else { "0" }
        $Code = @"
import os

try:
    from pdomain_ops.suite.components import ComponentRegistry
    from pdomain_ops.suite.runtime_components import RuntimeRegistration, record_runtime_use
except ModuleNotFoundError:
    raise SystemExit(0)

record_runtime_use(
    ComponentRegistry(),
    "pdomain-ocr-cli",
    RuntimeRegistration.from_json(os.environ["PDOMAIN_OCR_VC_RUNTIME_CLAIM"]),
    installed_here=os.environ.get("PDOMAIN_OCR_VC_RUNTIME_CREATED") == "1",
)
"@
        $Code | & $Python -I -
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Setup could not verify shared runtime ownership. Keep the Visual C++ Redistributable installed."
        }
    } catch {
        Write-Warning "Setup could not verify shared runtime ownership. Keep the Visual C++ Redistributable installed."
    } finally {
        $env:PDOMAIN_OCR_VC_RUNTIME_CLAIM = $Previous
        $env:PDOMAIN_OCR_VC_RUNTIME_CREATED = $PreviousCreated
    }
}

function Invoke-RegisteredVcRuntimeRemoval {
    param(
        [Parameter(Mandatory = $true)]$Package,
        [Parameter(Mandatory = $true)][scriptblock]$CanRemove,
        [switch]$Confirmed
    )
    if (-not $Confirmed) {
        Write-Host "Microsoft Visual C++ Redistributable $($Package.Version) ($($Package.Architecture))"
        Write-Host "Other Windows apps may depend on this runtime. Removing it can stop them from starting."
        if ((Read-Host "Type REMOVE to confirm") -cne "REMOVE") {
            return "kept"
        }
    }
    if (-not (& $CanRemove)) {
        return "kept"
    }
    $Current = @(Get-VcRuntimeRegistration | Where-Object { $_.PackageId -ceq $Package.PackageId })
    if ($Current.Count -ne 1 -or $Current[0].Version -cne $Package.Version -or
        $Current[0].Architecture -cne $Package.Architecture -or
        -not $Current[0].UninstallPath -or $Current[0].UninstallPath -cne $Package.UninstallPath) {
        return "kept"
    }
    $Executable = $Current[0].UninstallPath
    $Lock = [System.IO.File]::Open($Executable, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        Assert-MicrosoftSignature -Path $Executable
        try {
            $Code = Start-ElevatedInstaller -FilePath $Executable -Arguments "/uninstall /passive /norestart"
        } catch {
            if (Test-UacCancelled $_.Exception) {
                return "kept"
            }
            throw
        }
    } finally {
        $Lock.Dispose()
    }
    switch ($Code) {
        1602 { return "kept" }
        3010 { return "restart-required" }
        1641 { return "restart-required" }
        0 {
            if (@(Get-VcRuntimeRegistration | Where-Object { $_.PackageId -ceq $Package.PackageId }).Count -eq 0) {
                return "removed"
            }
            throw "The Visual C++ runtime is still registered after removal."
        }
        default { throw "The Visual C++ runtime uninstaller failed (exit code $Code)." }
    }
}

function Install-VcRuntime {
    # Download Microsoft's x64 Visual C++ Redistributable, check that
    # Microsoft signed it, and run it elevated. Only this step asks for
    # administrator rights. Returns "installed" or "restart-required"; throws
    # on any other outcome. Never restarts Windows.
    param(
        [Parameter(Mandatory = $true)][string]$WorkDir,
        [string]$Url = "https://aka.ms/vc14/vc_redist.x64.exe",
        [switch]$ReportExisting
    )
    $Installer = Join-Path $WorkDir "vc_redist.x64.exe"
    Write-Host "Downloading the Microsoft Visual C++ Redistributable (x64) from $Url ..."
    $PreviousProgress = $ProgressPreference
    $ProgressPreference = "SilentlyContinue"
    try {
        Invoke-WebRequest -Uri $Url -OutFile $Installer -UseBasicParsing
    } finally {
        $ProgressPreference = $PreviousProgress
    }

    # Hold the file open, readable but not writable, from the signature check
    # until the installer exits, so nothing can replace it in between.
    $Lock = [System.IO.File]::Open($Installer, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
        Assert-MicrosoftSignature -Path $Installer

        Write-Host ""
        Write-Host "Windows will ask for administrator permission to install the Visual C++ runtime."
        Write-Host "Only this step needs it; pdomain-ocr itself is installed for your user account."
        try {
            $Code = Start-ElevatedInstaller -FilePath $Installer -Arguments "/install /passive /norestart"
        } catch {
            if (Test-UacCancelled $_.Exception) {
                throw "The Visual C++ runtime was not installed: the administrator prompt was cancelled."
            }
            throw "The Visual C++ runtime installer could not be started: $($_.Exception.Message)"
        }
    } finally {
        $Lock.Dispose()
    }

    if ($null -eq $Code) {
        throw "The Visual C++ runtime installer did not report an exit code."
    }
    switch ($Code) {
        0 { return "installed" }
        1638 {
            if ($ReportExisting) { return "already-installed" }
            return "installed"
        }
        3010 { return "restart-required" }
        1641 { return "restart-required" }
        1602 { throw "The Visual C++ runtime installation was cancelled (exit code 1602)." }
        # Seen on Windows 11 with UAC turned off: a standard user's RunAs
        # start is not elevated, and the installer is denied.
        5 { throw "The Visual C++ runtime installer was denied access (exit code 5): it needs an administrator account." }
        default { throw "The Visual C++ runtime installer failed with exit code $Code." }
    }
}

function Write-VcRuntimeHelp {
    Write-Host ""
    Write-Host "pdomain-ocr needs the Microsoft Visual C++ Redistributable (x64). Without it,"
    Write-Host "OCR fails with 'WinError 126' while loading torch\lib\c10.dll."
    Write-Host "To install it yourself, or to ask an administrator to:"
    Write-Host "  1. Download https://aka.ms/vc14/vc_redist.x64.exe"
    Write-Host "  2. Run: vc_redist.x64.exe /install /passive /norestart"
    Write-Host "  3. Run pdomain-ocr again. No reinstall of pdomain-ocr is needed."
    Write-Host "Microsoft's page: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist"
}

function Confirm-VcRuntime {
    # Make sure the installed tool's native libraries can load. Returns
    # $true when Windows must be restarted before OCR can run.
    param(
        [Parameter(Mandatory = $true)][string]$EnvironmentPath,
        [Parameter(Mandatory = $true)][string]$WorkDir
    )
    $Floor = Get-MsvcToolsetFloor -EnvironmentPath $EnvironmentPath
    if (-not $Floor.Found) {
        Write-Host "WARNING: $EnvironmentPath was not found, so only the runtime DLLs' presence is checked."
    }
    $Status = Get-VcRuntimeStatus -Minimum $Floor.Version
    $Needed = if ($Floor.Version) { "$($Floor.Version) or newer" } else { "any version" }
    if ($Status.Adequate) {
        Write-Host "Visual C++ runtime $($Status.Installed) found; pdomain-ocr needs $Needed."
        Register-VcRuntimeClaim -EnvironmentPath $EnvironmentPath
        return $false
    }

    if ($Status.Missing.Count -gt 0) {
        Write-Host "The Microsoft Visual C++ runtime (x64) is missing: $($Status.Missing -join ', ') not found."
    } else {
        Write-Host "Visual C++ runtime $($Status.Installed) is older than $($Floor.Version), which $($Floor.File) needs."
    }

    if ($env:PD_OCR_SKIP_VC_RUNTIME -eq "1") {
        Write-VcRuntimeHelp
        throw "PD_OCR_SKIP_VC_RUNTIME=1 is set, so the runtime was not installed. pdomain-ocr is installed but cannot run OCR until the runtime is."
    }

    $WasAbsent = $false
    if ((Test-IsWindowsHost) -and -not $Status.Installed -and $Status.Missing.Count -eq 3) {
        try {
            $WasAbsent = @(Get-VcRuntimeRegistration).Count -eq 0
        } catch {
            $WasAbsent = $false
        }
    }

    try {
        $Outcome = Install-VcRuntime -WorkDir $WorkDir -ReportExisting
    } catch {
        Write-VcRuntimeHelp
        throw "pdomain-ocr is installed, but OCR cannot run yet. $($_.Exception.Message)"
    }
    if ($Outcome -eq "restart-required") {
        return $true
    }

    $After = Get-VcRuntimeStatus -Minimum $Floor.Version
    if ($After.Missing.Count -gt 0) {
        Write-VcRuntimeHelp
        throw "The Visual C++ runtime installer finished, but $($After.Missing -join ', ') is still missing."
    }
    if (-not $After.Adequate) {
        # Microsoft's newest runtime is now installed, so nothing more can be
        # done here. Some binary claims a newer toolset; OCR usually works.
        Write-Host "WARNING: Visual C++ runtime $($After.Installed) is the newest Microsoft offers, but"
        Write-Host "         $($Floor.File) was built with toolset $($Floor.Version)."
        Write-Host "         If pdomain-ocr fails to load a DLL, install a newer runtime when one is released."
        return $false
    }
    Write-Host "Visual C++ runtime $($After.Installed) installed."
    Register-VcRuntimeClaim -EnvironmentPath $EnvironmentPath -InstalledHere:($WasAbsent -and $Outcome -eq "installed")
    return $false
}

function Initialize-ManagedPython {
    param([string]$Version, [string]$WorkDir)
    try {
        $FindArgs = @("python", "find", "--no-project", "--no-python-downloads", "--", $Version)
        $Existing = Invoke-NativeCaptured -FilePath uv -ArgumentList $FindArgs
        if ($Existing.ExitCode -eq 0) {
            return
        }
        $Install = Invoke-NativeCaptured -FilePath uv -ArgumentList @(
            "--color", "never", "python", "install", "--no-bin", $Version
        )
        if ($Install.ExitCode -ne 0) {
            return
        }
        $Candidate = (& uv @FindArgs | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
            return
        }
        $Code = @(
            'import json'
            'import sys'
            'from pathlib import Path'
            'path = Path(sys._base_executable).resolve()'
            'info = path.stat()'
            'print(json.dumps([str(path), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]))'
        ) -join [Environment]::NewLine
        $Proof = ($Code | & $Candidate -I - | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $Proof) {
            Set-Content -LiteralPath (Join-Path $WorkDir "python-install.log") -Encoding ASCII -Value $Install.Output
            Set-Content -LiteralPath (Join-Path $WorkDir "python-proof.json") -Encoding ASCII -Value $Proof
        }
    } catch {
        Write-Warning "Setup could not establish fresh Python ownership."
    }
}

function Register-SharedPythonTools {
    param([string]$EnvironmentPath, [string]$WorkDir)
    $Python = [IO.Path]::Combine($EnvironmentPath, "Scripts", "python.exe")
    $UvPath = (Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if (-not $UvPath -or -not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        return
    }
    try {
        $Managed = (& $UvPath python dir | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $Managed) {
            return
        }
        $Code = @"
import json
import sys
from pathlib import Path
try:
    from pdomain_ops.suite.components import ComponentProbe, ComponentRegistry
    from pdomain_ops.suite.python_components import ManagedPython, claim_existing_tools, uv_installed_build
except ModuleNotFoundError:
    raise SystemExit(0)

registry = ComponentRegistry()
app = "pdomain-ocr-cli"
uv, root = map(Path, sys.argv[1:3])
base = Path(sys._base_executable).resolve()
if len(sys.argv) == 4:
    work = Path(sys.argv[3])
    log = work / "python-install.log"
    proof = work / "python-proof.json"
    if log.is_file() and proof.is_file():
        key = uv_installed_build(log.read_text())
        if key is not None and root.is_absolute() and base.is_relative_to(root.resolve() / key):
            info = base.stat()
            actual = [str(base), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]
            if actual == json.loads(proof.read_text()):
                item = ManagedPython(root, key, base)
                fingerprint = item.fingerprint()
                if fingerprint is not None:
                    registry.record_created(
                        app, "installer", ComponentProbe("python", item.identity, item.fingerprint), fingerprint,
                    )
claim_existing_tools(registry, app, uv, root, base)
"@
        $PythonArgs = @("-I", "-", $UvPath, $Managed)
        if ($WorkDir) {
            $PythonArgs += $WorkDir
        }
        $Code | & $Python @PythonArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Setup could not verify shared uv and Python ownership. Keep both tools installed."
        }
    } catch {
        Write-Warning "Setup could not verify shared uv and Python ownership. Keep both tools installed."
    }
}

function Complete-WindowsInstall {
    # Check the Visual C++ runtime for the installed tool. Returns $true when
    # Windows must restart before OCR can run.
    param([Parameter(Mandatory = $true)][string]$WorkDir, $UvBootstrap)
    $global:LASTEXITCODE = $null
    $ToolDir = (& uv tool dir | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $ToolDir) {
        throw "'uv tool dir' failed with exit code $LASTEXITCODE; cannot check the Visual C++ runtime."
    }
    $EnvironmentPath = Join-Path $ToolDir "pdomain-ocr-cli"
    $RestartRequired = Confirm-VcRuntime -EnvironmentPath $EnvironmentPath -WorkDir $WorkDir
    if ($UvBootstrap) {
        Publish-WindowsUv -EnvironmentPath $EnvironmentPath -Bootstrap $UvBootstrap
    }
    Register-SharedPythonTools -EnvironmentPath $EnvironmentPath -WorkDir $WorkDir
    return $RestartRequired
}

function Get-InstalledLauncher {
    $ToolBin = (& uv tool dir --bin | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $ToolBin) {
        throw "pdomain-ocr was installed, but uv could not locate its launcher."
    }
    $LauncherName = if (Test-IsWindowsHost) { "pdomain-ocr.exe" } else { "pdomain-ocr" }
    return Join-Path $ToolBin $LauncherName
}

function Get-CliRuntimeCleanupPackage {
    param([string]$Tool)
    $Python = [IO.Path]::Combine($Tool, "Scripts", "python.exe")
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf) -or
        (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $Tool) "pdomain-ocr-simple-gui"))) {
        return
    }
    $Packages = @(Get-VcRuntimeRegistration)
    if ($Packages.Count -ne 1 -or -not $Packages[0].UninstallPath) {
        return
    }
    $Previous = $env:PDOMAIN_OCR_VC_RUNTIME_CLAIM
    try {
        $env:PDOMAIN_OCR_VC_RUNTIME_CLAIM = ConvertTo-Json -InputObject $Packages[0] -Compress
        $Code = @"
import os
try:
    from pdomain_ops.suite.components import ComponentRegistry
    from pdomain_ops.suite.runtime_components import RuntimeRegistration, preview_runtime_cleanup
except ModuleNotFoundError:
    raise SystemExit(1)
package = RuntimeRegistration.from_json(os.environ["PDOMAIN_OCR_VC_RUNTIME_CLAIM"])
raise SystemExit(0 if preview_runtime_cleanup(ComponentRegistry(), "pdomain-ocr-cli", package) else 1)
"@
        $Code | & $Python -I -
        if ($LASTEXITCODE -eq 0) {
            return $Packages[0]
        }
    } finally {
        $env:PDOMAIN_OCR_VC_RUNTIME_CLAIM = $Previous
    }
}

function Write-CliRuntimeBridge {
    param([string]$Destination)
    $Definitions = foreach ($Name in @(
        "Get-CertificateOrganizations", "Get-CertificateRootThumbprint", "Assert-MicrosoftSignature",
        "Start-ElevatedInstaller", "Test-UacCancelled", "Select-VcRuntimeRegistration",
        "Get-VcRuntimeRegistration", "Invoke-RegisteredVcRuntimeRemoval"
    )) {
        "function $Name {" + (Get-Command $Name -CommandType Function).Definition + "}"
    }
    $Actions = {
        if ($Action -eq "probe") {
            ConvertTo-Json -InputObject @(Get-VcRuntimeRegistration) -Compress
        } elseif ($Action -eq "remove") {
            $Package = ConvertFrom-Json -InputObject $env:PDOMAIN_OCR_CONFIRMED_RUNTIME
            Invoke-RegisteredVcRuntimeRemoval -Package $Package -CanRemove { $true } -Confirmed
        } else {
            throw "Unknown runtime cleanup action."
        }
    }.ToString()
    $Newline = [Environment]::NewLine
    $Header = 'param([string]$Action)', '$ErrorActionPreference = "Stop"'
    ($Header + $Definitions + $Actions) -join $Newline |
        Set-Content -LiteralPath $Destination -Encoding UTF8
}

function Get-WindowsSharedCleanupCode {
    @"
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

preview = sys.argv[1] == "-"
if not preview:
    sys.path.insert(0, sys.argv[1])
try:
    from pdomain_ops.suite.component_files import ComponentFile
    from pdomain_ops.suite.component_siblings import macos_ocr_sibling_absent, other_uv_tools_absent
    from pdomain_ops.suite.components import ComponentRegistry
    from pdomain_ops.suite.model_components import preview_cached_models, remove_model_entry
    from pdomain_ops.suite.paths import installed_toml_path
    from pdomain_ops.suite.python_components import managed_python_from_executable
except ModuleNotFoundError:
    raise SystemExit(77)

app = "pdomain-ocr-cli"
sibling = "pdomain-ocr-simple-gui"
uv, receipt = map(Path, sys.argv[2:4])
managed_uv_dir = Path(sys.argv[5])
registry = ComponentRegistry()

def uv_dir(options, *, default=False):
    env = os.environ.copy()
    if default:
        for key in ("UV_TOOL_DIR", "UV_TOOL_BIN_DIR"):
            env.pop(key, None)
    try:
        result = subprocess.run(
            [str(uv), "tool", "dir", *options], env=env, check=True,
            capture_output=True, text=True, timeout=10,
        )
        path = Path(result.stdout.strip())
        if path.is_absolute():
            return path.resolve()
    except (OSError, RuntimeError, subprocess.SubprocessError):
        pass
    return None

def absent(candidates):
    for path in candidates:
        try:
            path.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            return False
        return False
    return True

def guards():
    root = receipt.parent.parent.resolve()
    default = uv_dir((), default=True)
    bins = (uv_dir(("--bin",)), uv_dir(("--bin",), default=True))
    if default is None or any(path is None for path in bins):
        return None
    local = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and (not local or not Path(local).is_absolute()):
        return None
    markers = [default / sibling]
    if local:
        markers.append(Path(local) / "Programs" / sibling / "install-manifest.json")
    for bin_dir in set(bins):
        markers.extend(bin_dir / f"{name}.exe" for name in (sibling, f"{sibling}-desktop"))

    def siblings_safe():
        return absent(markers) and macos_ocr_sibling_absent(
            app, home=Path.home(), tool_dir=root, bin_dir=bins[0], installed_apps=installed_toml_path(),
        )

    def tools_safe(departing=None):
        known_scope = root == default or bool(os.environ.get("PD_SUITE_DATA_DIR"))
        return known_scope and siblings_safe() and other_uv_tools_absent(
            (root, default), departing_tool=departing,
        )

    return siblings_safe, tools_safe

def uv_selections():
    if uv.name.casefold() != "uv.exe" or uv.parent.resolve() != managed_uv_dir.resolve():
        return []
    known = {
        item.identity: item.fingerprint
        for item in registry.list()
        if item.kind == "uv" and item.claims == (app,)
    }
    selections = []
    for path in (uv.with_name("uvx.exe"), uv.with_name("uvw.exe"), uv):
        try:
            item = ComponentFile(path)
            stamp = known.get(item.identity)
            if stamp is not None and item.fingerprint() == stamp:
                selections.append((item, stamp))
        except (OSError, ValueError):
            continue
    return selections

def preview_data(selections):
    paths = [str(item.path) for item, _stamp in selections]
    payload = json.dumps(list(zip(paths, (stamp for _item, stamp in selections), strict=True)))
    return {"paths": paths, "token": hashlib.sha256(payload.encode()).hexdigest()}

def model_data(selections):
    return preview_data([(item, item.fingerprint) for item in selections])

def python_selections(root, base):
    try:
        item = managed_python_from_executable(root, base)
        if item is not None:
            for record in registry.list():
                if (
                    record.kind == "python" and record.identity == item.identity
                    and record.claims == (app,) and item.fingerprint() == record.fingerprint
                ):
                    return [(item, record.fingerprint)]
    except (OSError, ValueError):
        pass
    return []

def shared_preview():
    plan = {}
    check = guards()
    if check is None:
        return plan
    siblings_safe, tools_safe = check
    if tools_safe(app) and (items := uv_selections()):
        plan["uv"] = preview_data(items)
    if tools_safe(app):
        try:
            reported = subprocess.run(
                [str(uv), "python", "dir"], check=True, capture_output=True,
                text=True, timeout=10,
            ).stdout.strip()
            root = Path(reported)
            base = Path(sys._base_executable).resolve()
            if items := python_selections(root, base):
                plan["python"] = preview_data(items)
                plan["python_root"] = str(root)
                plan["python_base"] = str(base)
        except (OSError, subprocess.SubprocessError):
            pass
    if siblings_safe():
        try:
            from huggingface_hub.constants import HF_HUB_CACHE
        except ModuleNotFoundError:
            return plan
        cache = Path(HF_HUB_CACHE).absolute()
        if items := preview_cached_models(registry, app, cache):
            plan["models"] = model_data(items)
            plan["cache"] = str(cache)
    return plan

def cleanup_shared(plan):
    check = guards()
    if check is None:
        print("Kept shared components because their locations could not be verified.")
        return
    siblings_safe, tools_safe = check
    if "models" in plan:
        items = preview_cached_models(registry, app, Path(plan["cache"]))
        if model_data(items)["token"] == plan["models"]:
            for item in items:
                if remove_model_entry(registry, app, item, siblings_safe=siblings_safe):
                    print(f"Removed model cache entry: {item.path}")
                else:
                    print(f"Kept model cache entry: {item.path}")
        else:
            print("Kept model cache entries because ownership changed after preview.")
    if "python" in plan and not Path(sys.base_prefix).resolve().is_relative_to(
        Path(sys.argv[1]).resolve() / "cleanup-python"
    ):
        print("Kept managed Python because the cleanup interpreter could not be staged.")
    elif "python" in plan:
        items = python_selections(Path(plan["python_root"]), Path(plan["python_base"]))
        if preview_data(items)["token"] == plan["python"]:
            for item, stamp in items:
                if registry.remove(
                    "python", item.identity, app, item.fingerprint,
                    lambda: item.remove(uv, stamp, run=lambda cmd: subprocess.run(
                        cmd, check=True, timeout=60,
                    )),
                    expected_fingerprint=stamp, siblings_safe=tools_safe,
                ):
                    print(f"Removed managed Python: {item.path}")
                else:
                    print(f"Kept managed Python: {item.path}")
        else:
            print("Kept managed Python because ownership changed after preview.")
    if "uv" in plan:
        items = uv_selections()
        if preview_data(items)["token"] == plan["uv"]:
            for item, stamp in items:
                if registry.remove(
                    "uv", item.identity, app, item.fingerprint, lambda: item.remove(stamp),
                    expected_fingerprint=stamp, siblings_safe=tools_safe,
                ):
                    print(f"Removed uv file: {item.path}")
                else:
                    print(f"Kept uv file: {item.path}")
        else:
            print("Kept uv files because ownership changed after preview.")

if preview:
    print(json.dumps(shared_preview()))
    raise SystemExit(0)
"@
}

function Get-WindowsSharedCleanupPreview {
    param([string]$Tool, [string]$Receipt)
    $Python = Join-Path $Tool "Scripts/python.exe"
    $Uv = (Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if (-not $Uv -or -not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        return
    }
    try {
        $Code = Get-WindowsSharedCleanupCode
        $Json = $Code | & $Python -I - - $Uv $Receipt - (Get-WindowsUvDestination) | Out-String
        if ($LASTEXITCODE -eq 0) {
            ConvertFrom-Json -InputObject $Json
        }
    } catch {
        Write-Warning "Could not verify shared component cleanup."
    }
}

function Invoke-UninstallWithClaimRelease {
    param([string]$Tool, [string]$Receipt, $RuntimePackage, [string]$SharedSelection)
    $Python = [IO.Path]::Combine($Tool, "Scripts", "python.exe")
    $UvPath = (Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if (-not $UvPath -or -not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        return $false
    }
    $Scratch = Join-Path ([IO.Path]::GetTempPath()) ("pdomain-ocr-remove-" + [guid]::NewGuid().ToString("N"))
    $PreviousConfirmed = $env:PDOMAIN_OCR_CONFIRMED_RUNTIME
    $PreviousSelection = $env:PDOMAIN_OCR_CONFIRMED_SHARED
    try {
        New-Item -ItemType Directory -Path $Scratch | Out-Null
        $RuntimeShell = ""
        $env:PDOMAIN_OCR_CONFIRMED_RUNTIME = $null
        $env:PDOMAIN_OCR_CONFIRMED_SHARED = $SharedSelection
        if ($RuntimePackage) {
            Write-CliRuntimeBridge -Destination (Join-Path $Scratch "runtime.ps1")
            $RuntimeShell = (Get-Process -Id $PID).Path
            $env:PDOMAIN_OCR_CONFIRMED_RUNTIME = ConvertTo-Json -InputObject $RuntimePackage -Compress
        }
        $Stage = @"
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

try:
    import filelock
    import platformdirs
    from pdomain_ops.suite import (
        component_files, component_siblings, components, model_components, paths, python_components,
        runtime_components,
    )
except ModuleNotFoundError:
    raise SystemExit(77)

destination = Path(sys.argv[1])
tool = Path(sys.prefix).resolve()
base = Path(sys._base_executable).resolve()
if base.is_relative_to(tool) or not base.is_file():
    raise RuntimeError("Expected a retained Python interpreter")
sources = destination / "pdomain_ops" / "suite"
sources.mkdir(parents=True)
for package in (sources.parent, sources):
    (package / "__init__.py").touch()
for module in (
    component_files, component_siblings, components, model_components, paths, python_components,
    runtime_components,
):
    path = Path(module.__file__)
    shutil.copy2(path, sources / path.name)
for dependency in (filelock, platformdirs):
    path = Path(dependency.__file__).parent
    shutil.copytree(path, destination / path.name, ignore=shutil.ignore_patterns("__pycache__"))
plan = json.loads(os.environ.get("PDOMAIN_OCR_CONFIRMED_SHARED") or "{}")
if "python" in plan and Path(plan["python_base"]) == base:
    try:
        item = python_components.managed_python_from_executable(Path(plan["python_root"]), base)
        stamp = item.fingerprint() if item is not None else None
        if stamp is not None and item is not None:
            payload = json.dumps([(str(item.path), stamp)])
            if hashlib.sha256(payload.encode()).hexdigest() == plan["python"]:
                base = item.stage_cleanup_interpreter(destination / "cleanup-python", stamp)
    except (OSError, ValueError):
        pass
print(base)
"@
        $Base = ($Stage | & $Python -I - $Scratch | Out-String).Trim()
        if ($LASTEXITCODE -eq 77) {
            return $false
        }
        if ($LASTEXITCODE -ne 0 -or -not $Base) {
            throw "Could not prepare registry-aware OCR CLI removal."
        }
        $Remove = @"
from pdomain_ops.suite.runtime_components import RuntimeRegistration, remove_runtime

data = os.environ.get("PDOMAIN_OCR_CONFIRMED_RUNTIME")
selection = os.environ.get("PDOMAIN_OCR_CONFIRMED_SHARED")
def uninstall():
    subprocess.run([sys.argv[2], "tool", "uninstall", "--offline", "pdomain-ocr-cli"], check=True)
    if receipt.exists() or receipt.is_symlink():
        raise RuntimeError("uv did not remove the OCR CLI receipt")

def cleanup_runtime():
    package = RuntimeRegistration.from_json(data)
    bridge = Path(sys.argv[1]) / "runtime.ps1"
    command = [sys.argv[4], "-NoProfile", "-NonInteractive", "-File", str(bridge)]

    def action(name):
        return subprocess.run([*command, name], check=True, capture_output=True, text=True, timeout=600).stdout

    def probe():
        entries = json.loads(action("probe"))
        if not entries:
            return None
        if len(entries) != 1:
            raise RuntimeError("Windows reported multiple runtime packages; keeping the runtime")
        return RuntimeRegistration.from_json(json.dumps(entries[0]))

    def remove(_package):
        result = action("remove").strip().splitlines()
        return bool(result) and result[-1] == "removed"

    check = guards()
    if check is not None and remove_runtime(
        registry, app, package, probe=probe, uninstall=remove, siblings_safe=check[0],
    ):
        print("Removed the Visual C++ runtime.")
    else:
        print("Kept the Visual C++ runtime.")

def cleanup():
    if data:
        cleanup_runtime()
    if selection:
        cleanup_shared(json.loads(selection))

registry.release(app, uninstall=uninstall, cleanup=cleanup if data or selection else None)
"@
        if (-not $RuntimeShell) {
            $RuntimeShell = "-"
        }
        $Code = (Get-WindowsSharedCleanupCode) + [Environment]::NewLine + $Remove
        $Code | & $Base -I - $Scratch $UvPath $Receipt $RuntimeShell (Get-WindowsUvDestination) |
            ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) {
            throw "Registry-aware OCR CLI removal did not finish. Review the output before retrying."
        }
        return $true
    } finally {
        $env:PDOMAIN_OCR_CONFIRMED_RUNTIME = $PreviousConfirmed
        $env:PDOMAIN_OCR_CONFIRMED_SHARED = $PreviousSelection
        Remove-Item -LiteralPath $Scratch -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-CliUninstall {
    param(
        [switch]$Preview, [switch]$RemoveRuntime, [switch]$RemoveUv, [switch]$RemoveModels,
        [switch]$RemovePython
    )
    $ToolDir = (& uv tool dir | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $ToolDir -or -not [IO.Path]::IsPathRooted($ToolDir)) {
        throw "uv did not report an absolute tool directory. No files were removed."
    }
    $Tool = Join-Path $ToolDir "pdomain-ocr-cli"
    $Receipt = Join-Path $Tool "uv-receipt.toml"
    if (-not (Test-Path -LiteralPath $Tool)) {
        Write-Host "OCR CLI is already absent from $ToolDir."
        return
    }
    if (-not (Test-Path -LiteralPath $Receipt -PathType Leaf) -or
        ((Get-Item -LiteralPath $Tool).Attributes -band [IO.FileAttributes]::ReparsePoint) -or
        ((Get-Item -LiteralPath $Receipt).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Cannot verify the OCR CLI uv receipt at $Receipt."
    }
    Write-Host "CLI environment: $Tool"
    Write-Host "CLI receipt: $Receipt"
    Write-Host "Uninstall keeps shared dependencies by default. Models, settings, and OCR files stay."
    $SharedSelection = @{}
    if ($Preview -or $RemoveUv -or $RemoveModels -or $RemovePython) {
        $Plan = Get-WindowsSharedCleanupPreview -Tool $Tool -Receipt $Receipt
        if (($Preview -or $RemoveUv) -and $Plan.uv) {
            Write-Host "uv executables eligible for opt-in removal:"
            $Plan.uv.paths | ForEach-Object { Write-Host "  $_" }
            if ($RemoveUv) {
                $SharedSelection.uv = $Plan.uv.token
            }
        } elseif ($RemoveUv) {
            Write-Host "Keeping uv. Setup could not verify sole ownership or other tools still use it."
        }
        if (($Preview -or $RemoveModels) -and $Plan.models) {
            Write-Host "OCR model snapshot entries eligible for opt-in removal:"
            $Plan.models.paths | ForEach-Object { Write-Host "  $_" }
            Write-Host "Shared model blobs and your OCR inputs and outputs stay."
            if ($RemoveModels) {
                $SharedSelection.models = $Plan.models.token
                $SharedSelection.cache = $Plan.cache
            }
        } elseif ($RemoveModels) {
            Write-Host "Keeping model cache entries. Setup could not verify sole ownership."
        }
        if (($Preview -or $RemovePython) -and $Plan.python) {
            Write-Host "Managed Python eligible for opt-in removal:"
            $Plan.python.paths | ForEach-Object { Write-Host "  $_" }
            if ($RemovePython) {
                $SharedSelection.python = $Plan.python.token
                $SharedSelection.python_root = $Plan.python_root
                $SharedSelection.python_base = $Plan.python_base
            }
        } elseif ($RemovePython) {
            Write-Host "Keeping managed Python. Setup could not verify sole ownership or other tools still use it."
        }
    }
    $RuntimePackage = if ($Preview -or $RemoveRuntime) { Get-CliRuntimeCleanupPackage -Tool $Tool } else { $null }
    if ($RuntimePackage) {
        Write-Host "Tracked Microsoft Visual C++ Redistributable $($RuntimePackage.Version) ($($RuntimePackage.Architecture))"
        Write-Host "Registered uninstaller: $($RuntimePackage.UninstallPath)"
        Write-Host "Other Windows apps may depend on this runtime. Removing it can stop them from starting."
    } elseif ($RemoveRuntime) {
        Write-Host "Keeping the Visual C++ runtime. Setup could not verify provenance and sole ownership."
    }
    if ($Preview) {
        return
    }
    if ((Read-Host "Type REMOVE to uninstall OCR CLI") -cne "REMOVE") {
        Write-Host "Uninstall canceled."
        return
    }
    if ($RuntimePackage -and (Read-Host "Type REMOVE RUNTIME to also remove the Visual C++ runtime") -cne "REMOVE RUNTIME") {
        $RuntimePackage = $null
        Write-Host "Keeping the Visual C++ runtime."
    }
    $ConfirmedShared = if ($SharedSelection.Count) {
        ConvertTo-Json -InputObject $SharedSelection -Compress
    }
    if (Invoke-UninstallWithClaimRelease -Tool $Tool -Receipt $Receipt -RuntimePackage $RuntimePackage -SharedSelection $ConfirmedShared) {
        return
    }
    & uv tool uninstall --offline pdomain-ocr-cli
    if ($LASTEXITCODE -ne 0 -or (Test-Path -LiteralPath $Receipt)) {
        throw "uv did not confirm OCR CLI removal."
    }
}

function Invoke-ModelPrefetch {
    param([string]$Launcher)
    $ModelSource = $env:PDOMAIN_OCR_MODEL_SOURCE
    try {
        if (-not $Launcher) {
            $Launcher = Get-InstalledLauncher
        }
        $HelpText = & $Launcher --help | Out-String
        if ($LASTEXITCODE -ne 0 -or -not $HelpText.Contains("download-models")) {
            Write-Warning "Model prefetch is unavailable. Models will download on the first OCR run."
            return
        }
        $env:PDOMAIN_OCR_MODEL_SOURCE = "installer"
        & $Launcher download-models
        if ($LASTEXITCODE -ne 0) {
            throw "The model download command failed with exit code $LASTEXITCODE."
        }
    } catch {
        Write-Warning "Model prefetch failed. Models will download on the first OCR run, or retry with: pdomain-ocr download-models"
    } finally {
        $env:PDOMAIN_OCR_MODEL_SOURCE = $ModelSource
    }
}

function Write-InstallSummary {
    param([bool]$RestartRequired)
    Write-Host ""
    if ($RestartRequired) {
        Write-Host "Done, but Windows must restart before OCR can run: the Visual C++ runtime"
        Write-Host "installer asked for a restart. This installer never restarts Windows itself."
        Write-Host "After restarting, run: pdomain-ocr page.png"
    } else {
        Write-Host "Done! Run: pdomain-ocr page.png"
    }
    Write-Host "If 'pdomain-ocr' is not found, ensure uv's tool bin is on your PATH."
    Write-Host "  uv tool update-shell"
}

if ($Uninstall -or $UninstallPreview) {
    if (-not (Test-IsWindowsHost)) {
        throw "This PowerShell uninstall entry point requires Windows."
    }
    Invoke-CliUninstall -Preview:$UninstallPreview -RemoveRuntime:$RemoveVcRuntime -RemoveUv:$RemoveUv -RemoveModels:$RemoveModels -RemovePython:$RemovePython
    return
}

if ($ProbeVcRuntimeRegistration) {
    if (-not (Test-IsWindowsHost)) {
        throw "Visual C++ runtime registration is available on Windows only."
    }
    ConvertTo-Json -InputObject @(Get-VcRuntimeRegistration) -Compress
    return
}

if ($CheckStagedRuntime) {
    if (-not (Test-IsWindowsHost) -or
        -not (Test-Path -LiteralPath $CheckStagedRuntime -PathType Container)) {
        throw "CheckStagedRuntime requires a staged Windows environment."
    }
    $RuntimeWorkDir = Split-Path -Parent $CheckStagedRuntime
    if (Confirm-VcRuntime -EnvironmentPath $CheckStagedRuntime -WorkDir $RuntimeWorkDir) {
        throw "Restart Windows before retrying the OCR update."
    }
    return
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
$AutoUpdatePreference = if ($AutoUpdateCheck -or $env:PD_OCR_INSTALL_AUTO_UPDATE_CHECK -ceq "1") {
    "on"
} elseif ($env:PD_OCR_INSTALL_AUTO_UPDATE_CHECK -ceq "0") {
    "off"
} elseif ($env:PD_OCR_INSTALL_AUTO_UPDATE_CHECK) {
    throw "PD_OCR_INSTALL_AUTO_UPDATE_CHECK must be 0 or 1."
}

$TorchBackend = ""

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $CudaVer = Get-CudaVersion

    if ($CudaVer) {
        # uv picks the PyTorch CUDA build that matches the driver. PyPI's
        # Windows torch wheels are CPU-only, so this matters on Windows too.
        # Do not add download.pytorch.org/whl/cuXXX as an --index instead:
        # it also serves old copies of common packages (packaging 24.1 at
        # most), and under first-index uv then takes `packaging` from it
        # alone, so the resolve fails (pdomain-ops needs packaging>=26).
        # OCR uses that PyTorch build and does not install CuPy.
        $TorchBackend = "auto"
        Write-Host "Detected CUDA $CudaVer -- uv will pick the matching PyTorch CUDA build."
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
        Write-GpuSetupHint
    }
} else {
    Write-Host "No GPU detected -- installing CPU-only PyTorch."
    Write-GpuSetupHint
}

$ReleaseUrl = "https://api.github.com/repos/$Repo/releases/latest"
Write-Host "Resolving latest release via GitHub API..."
$Release = Invoke-RestMethod -Uri $ReleaseUrl
$ReleaseTag = $Release.tag_name
$ExpectedReleaseTag = $env:PDOMAIN_OCR_EXPECTED_RELEASE_TAG
if ($ExpectedReleaseTag -and $ReleaseTag -cne $ExpectedReleaseTag) {
    $FoundReleaseTag = if ($ReleaseTag) { $ReleaseTag } else { "<unknown>" }
    throw "Expected release $ExpectedReleaseTag but found $FoundReleaseTag. Check for updates again."
}
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
if ([IO.Path]::GetFileName($WheelName) -cne $WheelName -or $WheelName -notlike "*.whl") {
    throw "Invalid wheel filename: $WheelName"
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

$UvBootstrap = $null
try {
    $WheelFile = Join-Path $TempDir $WheelName
    Write-Host "Downloading wheel..."
    Invoke-WebRequest -Uri $WheelUrl -OutFile $WheelFile -UseBasicParsing

    # Verify the downloaded wheel against the digest GitHub reported for it,
    # BEFORE calling `uv tool install`. A digest that doesn't match the bytes
    # we actually fetched means the download was tampered with or corrupted;
    # either way, installing it would be worse than failing here.
    $WheelActualHex = (Get-FileHash -Algorithm SHA256 -Path $WheelFile).Hash.ToLowerInvariant()
    if ($WheelActualHex -ne $WheelDigestHex) {
        throw "Wheel digest mismatch for $WheelFile.`n  expected: sha256:$WheelDigestHex`n  actual:   sha256:$WheelActualHex"
    }
    Write-Host "Digest verified: sha256:$WheelActualHex"

    if ($PrepareUpdate) {
        $StagingDir = New-Item -ItemType Directory -Path $PrepareUpdate
        if ($PSVersionTable.PSVersion.Major -ge 6 -and -not $IsWindows) {
            $StagingDir.UnixFileMode = $TempDirItem.UnixFileMode
        }
        Copy-Item -LiteralPath $WheelFile -Destination (Join-Path $PrepareUpdate $WheelName)
        $CandidateTemp = Join-Path $PrepareUpdate "candidate.tmp"
        Set-Content -LiteralPath $CandidateTemp -Encoding ASCII -Value @(
            $WheelName, $PythonVersion, $TorchBackend, $WheelActualHex
        )
        Move-Item -LiteralPath $CandidateTemp -Destination (Join-Path $PrepareUpdate "candidate")
        return
    }

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        $UserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        if ($UserPath) {
            $env:PATH = [Environment]::ExpandEnvironmentVariables($UserPath) + [IO.Path]::PathSeparator + $env:PATH
        }
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "uv not found -- checking the uv install directory..."
        if (Test-IsWindowsHost) {
            $UvBootstrap = Initialize-WindowsUv -WorkDir $TempDir
        } else {
            irm https://astral.sh/uv/install.ps1 | iex
        }
        if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
            throw "Could not find uv after setup. Open a new PowerShell window and run this installer again."
        }
    }

    Write-Host "Installing pdomain-ocr $ReleaseTag from $WheelName..."
    # "first-index" makes uv stop looking once a package name resolves on an
    # index, in index-URL order. The pdomain index is bound via a named
    # `--index` (not the deprecated `--extra-index-url`): uv ranks
    # --index/UV_INDEX strictly above --extra-index-url, and passing --index
    # explicitly on the CLI replaces (rather than merges with) any UV_INDEX
    # the environment supplies. Verified against real uv 0.11.32 with local
    # decoy indexes: a hostile UV_INDEX env var beats --extra-index-url but
    # cannot beat this --index binding. When CUDA was detected,
    # --torch-backend auto lets uv choose the PyTorch CUDA build.
    $UvArgs = @(
        "tool", "install", "--python", $PythonVersion, "--reinstall", $WheelFile,
        "--index-strategy", "first-index", "--index", "pdomain=$PdIndexUrl"
    )
    if ($TorchBackend) {
        $UvArgs += @("--torch-backend", $TorchBackend)
    }
    if (Test-IsWindowsHost) {
        Initialize-ManagedPython -Version $PythonVersion -WorkDir $TempDir
    }
    Invoke-UvToolInstall -UvArgs $UvArgs

    $RestartRequired = $false
    if (Test-IsWindowsHost) {
        $RestartRequired = Complete-WindowsInstall -WorkDir $TempDir -UvBootstrap $UvBootstrap
    }
} finally {
    if ($UvBootstrap -and ($env:PATH -split [IO.Path]::PathSeparator)[0] -eq $UvBootstrap.Staging) {
        $env:PATH = $UvBootstrap.OriginalPath
    }
    Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
}

$Launcher = $null
if ($RestartRequired) {
    if (-not $SkipModels) {
        Write-Warning "After restarting Windows, run: pdomain-ocr download-models. Models can also download on the first OCR run."
    }
    if ($AutoUpdatePreference) {
        throw "pdomain-ocr was installed. After restarting Windows, run: pdomain-ocr update --auto-check $AutoUpdatePreference"
    }
} elseif ($AutoUpdatePreference) {
    $Launcher = Get-InstalledLauncher
    try {
        & $Launcher update --auto-check $AutoUpdatePreference
        if ($LASTEXITCODE -ne 0) {
            throw "The update preference command failed with exit code $LASTEXITCODE."
        }
    } catch {
        throw "pdomain-ocr was installed, but the update preference could not be saved. Run: pdomain-ocr update --auto-check $AutoUpdatePreference"
    }
}

if (-not $RestartRequired -and -not $SkipModels) {
    Invoke-ModelPrefetch -Launcher $Launcher
}

Write-InstallSummary -RestartRequired $RestartRequired
