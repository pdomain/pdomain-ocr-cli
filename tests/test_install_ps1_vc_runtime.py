"""Real-pwsh tests for install.ps1's Windows-only helper functions.

install.ps1 must stay one self-contained file for `irm | iex`, so these tests
load its function definitions from the script's syntax tree, without running
its main body. Each test then replaces the cmdlets a helper calls (download,
signature check, elevated start, file versions) with PowerShell fakes, so the
Windows branches run on any pwsh host.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

INSTALLER = Path(__file__).resolve().parents[1] / "install.ps1"

LOAD_FUNCTIONS = f"""
$ErrorActionPreference = "Stop"
$InstallerAst = [System.Management.Automation.Language.Parser]::ParseFile(
    '{INSTALLER}', [ref]$null, [ref]$null)
$Definitions = $InstallerAst.FindAll({{
    param($Node)
    $Node -is [System.Management.Automation.Language.FunctionDefinitionAst]
}}, $false)
foreach ($Definition in $Definitions) {{
    . ([scriptblock]::Create($Definition.Extent.Text))
}}
"""

# Root of the real vc_redist.x64.exe 14.52.37029 chain, read on 2026-11-13.
MICROSOFT_ROOT_2011 = "8F43288AD272F3103B6FB1428485EA3014C0BCFE"

MICROSOFT_SIGNER = (
    "CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington, C=US"
)


def _pwsh(body: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "case.ps1"
    _ = script.write_text(LOAD_FUNCTIONS + body, encoding="utf-8")
    return subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(script)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )


def _pe_bytes(major: int, minor: int) -> bytes:
    """Smallest file Get-PeLinkerVersion accepts: DOS stub, PE signature,
    COFF header and the first bytes of the optional header."""
    data = bytearray(0x40 + 28)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x40)
    data[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<H", data, 0x40 + 24, 0x20B)
    data[0x40 + 26] = major
    data[0x40 + 27] = minor
    return bytes(data)


def test_runtime_registration_selects_only_exact_microsoft_package(tmp_path: Path) -> None:
    result = _pwsh(
        """
$Packages = @(
    [pscustomobject]@{ PSChildName = '{11111111-1111-1111-1111-111111111111}';
        DisplayName = 'Microsoft Visual C++ 2015-2022 Redistributable (x64) - 14.44.35211';
        DisplayVersion = '14.44.35211.0'; Publisher = 'Microsoft Corporation' },
    [pscustomobject]@{ PSChildName = '{22222222-2222-2222-2222-222222222222}';
        DisplayName = 'Microsoft Visual C++ 2015-2022 Redistributable (x86) - 14.44.35211';
        DisplayVersion = '14.44.35211.0'; Publisher = 'Microsoft Corporation' },
    [pscustomobject]@{ PSChildName = '{33333333-3333-3333-3333-333333333333}';
        DisplayName = 'Microsoft Visual C++ 2015-2022 Redistributable (x64) - 14.44.35211';
        DisplayVersion = '14.44.35211.0'; Publisher = 'Other Vendor' }
)
Select-VcRuntimeRegistration -Entries $Packages | ForEach-Object {
    "$($_.PackageId)|$($_.Version)|$($_.Architecture)"
}
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "11111111-1111-1111-1111-111111111111|14.44.35211.0|x64"


@pytest.mark.parametrize("mode", ["preview", "cancel", "remove"])
def test_windows_app_uninstall_requires_confirmation(tmp_path: Path, mode: str) -> None:
    tool = tmp_path / "pdomain-ocr-cli"
    tool.mkdir()
    receipt = tool / "uv-receipt.toml"
    receipt.touch()
    answer = "REMOVE" if mode == "remove" else "cancel"
    switch = "-Preview" if mode == "preview" else ""
    result = _pwsh(
        f"""
function uv {{
    $global:LASTEXITCODE = 0
    if ($args -join ' ' -eq 'tool dir') {{ return '{tmp_path}' }}
    if ($args -join ' ' -eq 'tool uninstall --offline pdomain-ocr-cli') {{
        Remove-Item -LiteralPath '{receipt}'
        return
    }}
    throw 'Unexpected uv operation'
}}
function Read-Host {{ return '{answer}' }}
Invoke-CliUninstall {switch}
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert str(receipt) in result.stdout
    assert receipt.exists() == (mode != "remove")


@pytest.mark.parametrize(
    ("remove_runtime", "legacy_sibling"), [(False, False), (True, False), (True, True)]
)
def test_windows_uninstall_releases_claim_after_receipt_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, remove_runtime: bool, legacy_sibling: bool
) -> None:
    if find_spec("pdomain_ops.suite.components") is None:
        pytest.skip("shared registry is not available in this environment")
    tool = tmp_path / "pdomain-ocr-cli"
    installed = tool / "Scripts/python.exe"
    installed.parent.mkdir(parents=True)
    _ = installed.write_text('#!/bin/sh\nshift\nexec "$TEST_PYTHON" "$@"\n')
    installed.chmod(0o755)
    uv = tmp_path / "uv"
    _ = uv.write_text(
        '#!/bin/sh\nif [ "$2" = dir ]; then printf "%s\\n" "$TEST_DEFAULT_TOOLS"; '
        'else rm -f "$TEST_RECEIPT"; fi\n'
    )
    default_tools = tmp_path / "default-tools"
    monkeypatch.setenv("TEST_DEFAULT_TOOLS", str(default_tools))
    monkeypatch.setenv("HOME", str(tmp_path))
    if legacy_sibling:
        (default_tools / "pdomain-ocr-simple-gui").mkdir(parents=True)
    uv.chmod(0o755)
    receipt = tool / "uv-receipt.toml"
    receipt.touch()
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setenv("TEST_RECEIPT", str(receipt))
    monkeypatch.setenv("TEST_PYTHON", sys.executable)
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path / "suite"))
    registration = tmp_path / "runtime.json"
    _ = registration.write_text(
        '{"PackageId":"11111111-1111-1111-1111-111111111111","Architecture":"x64",'
        '"Version":"14.44.35211.0","UninstallPath":"C:/Package Cache/VC_redist.x64.exe"}'
    )
    monkeypatch.setenv("TEST_REGISTRATION_FILE", str(registration))
    _ = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
from pathlib import Path
from pdomain_ops.suite.components import ComponentRegistry
from pdomain_ops.suite.runtime_components import RuntimeRegistration, record_runtime_use
record = RuntimeRegistration.from_json(Path(os.environ["TEST_REGISTRATION_FILE"]).read_text())
assert record_runtime_use(ComponentRegistry(), "pdomain-ocr-cli", record, installed_here=True)
""",
        ],
        check=True,
    )
    selection = "-RuntimePackage (Get-VcRuntimeRegistration)" if remove_runtime else ""
    result = _pwsh(
        f"""
function Get-VcRuntimeRegistration {{
    if (Test-Path -LiteralPath $env:TEST_REGISTRATION_FILE) {{
        Get-Content -LiteralPath $env:TEST_REGISTRATION_FILE -Raw | ConvertFrom-Json
    }}
}}
function Invoke-RegisteredVcRuntimeRemoval {{
    param($Package, [scriptblock]$CanRemove, [switch]$Confirmed)
    if (-not $Confirmed -or -not (& $CanRemove) -or (Test-Path -LiteralPath $env:TEST_RECEIPT)) {{
        throw 'Runtime removal was not confirmed after app uninstall'
    }}
    Remove-Item -LiteralPath $env:TEST_REGISTRATION_FILE
    'removed'
}}
Invoke-UninstallWithClaimRelease -Tool '{tool}' -Receipt '{receipt}' {selection}
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines()[-1] == "True"
    assert not receipt.exists()
    registry = tmp_path / "suite/components.json"
    if remove_runtime and not legacy_sibling:
        assert not registration.exists()
        assert not registry.exists()
    else:
        assert registration.exists()
        assert '"claims": []' in registry.read_text()


def test_windows_removes_only_the_managed_python_shown_in_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if find_spec("pdomain_ops.suite.python_components") is None:
        pytest.skip("shared registry is not available in this environment")
    source = Path(sys.base_prefix).resolve()
    if source in {Path("/usr"), Path("/usr/local")}:
        pytest.skip("this fixture needs a standalone Python build")
    base = Path(sys._base_executable).resolve()
    root = tmp_path / "python"
    build = root / "cpython-3.13.14-windows-x86_64-none"
    _ = shutil.copytree(source, build, symlinks=True)
    interpreter = build / base.relative_to(source)
    other = root / "cpython-3.13.13-windows-x86_64-none"
    other.mkdir()
    tools = tmp_path / "tools"
    tool = tools / "pdomain-ocr-cli"
    _ = subprocess.run(
        ["uv", "--offline", "venv", "--python", str(interpreter), str(tool)], check=True
    )
    launcher = tool / "Scripts/python.exe"
    launcher.parent.mkdir(parents=True)
    _ = launcher.write_text('#!/bin/sh\nshift\nexec "$TEST_PYTHON" "$@"\n')
    launcher.chmod(0o755)
    (tool / "uv-receipt.toml").touch()
    uv = tmp_path / "uv.exe"
    _ = uv.write_text(
        f"""#!{sys.executable}
import os, shutil, sys
args = sys.argv[1:]
if args[:2] == ["tool", "dir"]:
    print(os.environ["TEST_BINS" if "--bin" in args else "TEST_TOOLS"])
elif args == ["python", "dir"]:
    print(os.environ["TEST_ROOT"])
elif args[:2] == ["tool", "uninstall"]:
    shutil.rmtree(os.environ["TEST_TOOL"])
else:
    assert args[:4] == ["--offline", "python", "uninstall", "--install-dir"]
    assert args[4:] == [os.environ["TEST_ROOT"], "cpython-3.13.14-windows-x86_64-none"]
    shutil.rmtree(os.environ["TEST_BUILD"])
"""
    )
    uv.chmod(0o755)
    (tmp_path / "uv").symlink_to(uv)
    for key, value in {
        "HOME": str(tmp_path),
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "PYTHONPATH": os.pathsep.join(path for path in sys.path if Path(path).is_absolute()),
        "PD_SUITE_DATA_DIR": str(tmp_path / "suite"),
        "TEST_PYTHON": str(tool / "bin/python"),
        "TEST_TOOLS": str(tools),
        "TEST_TOOL": str(tool),
        "TEST_ROOT": str(root),
        "TEST_BUILD": str(build),
        "TEST_BINS": str(tmp_path / "bin"),
        "UV_TOOL_DIR": str(tools),
        "UV_TOOL_BIN_DIR": str(tmp_path / "bin"),
    }.items():
        monkeypatch.setenv(key, value)
    _ = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from pathlib import Path
from pdomain_ops.suite.components import ComponentProbe, ComponentRegistry
from pdomain_ops.suite.python_components import managed_python_from_executable
item = managed_python_from_executable(Path(sys.argv[1]), Path(sys.argv[2]))
assert item is not None
assert ComponentRegistry().record_created(
    "pdomain-ocr-cli", "installer",
    ComponentProbe("python", item.identity, item.fingerprint), item.fingerprint(),
)
""",
            str(root),
            str(interpreter),
        ],
        check=True,
    )
    result = _pwsh(
        f"""
if ((& uv tool dir | Out-String).Trim() -ne '{tools}') {{ throw 'Fixture uv is not active' }}
function Read-Host {{ return 'REMOVE' }}
Invoke-CliUninstall -RemovePython
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"  {build}" in result.stdout
    assert f"Removed managed Python: {build}" in result.stdout
    assert not build.exists()
    assert not tool.exists()
    assert other.is_dir()
    assert uv.is_file()


def test_windows_claim_respects_runtime_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if find_spec("pdomain_ops.suite.components") is None:
        pytest.skip("shared registry is not available in this environment")
    python = tmp_path / "Scripts/python.exe"
    python.parent.mkdir()
    _ = python.write_text('#!/bin/sh\nshift\nexec "$TEST_PYTHON" "$@"\n')
    python.chmod(0o755)
    registry = tmp_path / "components.json"
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TEST_PYTHON", sys.executable)
    script = f"""
function Get-VcRuntimeRegistration {{
    [pscustomobject]@{{ PackageId = '11111111-1111-1111-1111-111111111111';
        Version = '14.44.35211.0'; Architecture = 'x64'; UninstallPath = 'C:/Package Cache/VC_redist.x64.exe' }}
}}
Register-VcRuntimeClaim -EnvironmentPath '{tmp_path}'
(Get-CliRuntimeCleanupPackage -Tool '{tmp_path}').UninstallPath
"""
    result = _pwsh(script, tmp_path)
    assert result.returncode == 0, result.stderr
    assert not registry.exists()
    _ = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json
from pdomain_ops.suite.components import ComponentProbe, ComponentRegistry
package = dict(PackageId="11111111-1111-1111-1111-111111111111", Version="14.44.35211.0",
               Architecture="x64", UninstallPath="C:/Package Cache/VC_redist.x64.exe")
stamp = json.dumps(package, sort_keys=True, separators=(",", ":"))
probe = ComponentProbe("vc-runtime", "x64:11111111-1111-1111-1111-111111111111", lambda: stamp)
assert ComponentRegistry().record_created("pdomain-ocr-simple-gui", "installer", probe, stamp)
""",
        ],
        check=True,
    )
    result = _pwsh(script, tmp_path)
    assert result.returncode == 0, result.stderr
    record = registry.read_text()
    assert '"installed_by": "pdomain-ocr-simple-gui"' in record
    assert '"pdomain-ocr-cli"' in record
    assert "VC_redist.x64.exe" not in result.stdout
    _ = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pdomain_ops.suite.components import ComponentRegistry; "
            "ComponentRegistry().release('pdomain-ocr-simple-gui')",
        ],
        check=True,
    )
    final = _pwsh(script, tmp_path)
    assert final.returncode == 0, final.stderr
    assert final.stdout.strip() == "C:/Package Cache/VC_redist.x64.exe"


def test_windows_setup_claims_only_known_uv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if find_spec("pdomain_ops.suite.python_components") is None:
        pytest.skip("shared registry is not available in this environment")
    python = tmp_path / "Scripts/python.exe"
    python.parent.mkdir()
    _ = python.write_text('#!/bin/sh\nshift\nexec "$TEST_PYTHON" "$@"\n')
    python.chmod(0o755)
    uv = tmp_path / "uv"
    _ = uv.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_PYTHON_ROOT"\n')
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setenv("TEST_PYTHON", sys.executable)
    monkeypatch.setenv("TEST_PYTHON_ROOT", str(tmp_path / "python"))
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
    registry = tmp_path / "components.json"
    script = f"Register-SharedPythonTools -EnvironmentPath '{tmp_path}'"
    initial = _pwsh(script, tmp_path)
    assert initial.returncode == 0, initial.stdout + initial.stderr
    assert not registry.exists()
    _ = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from pathlib import Path
from pdomain_ops.suite.component_files import ComponentFile
from pdomain_ops.suite.components import ComponentProbe, ComponentRegistry
item = ComponentFile(Path(sys.argv[1]))
stamp = item.fingerprint()
assert ComponentRegistry().record_created(
    "pdomain-ocr-simple-gui", "installer", ComponentProbe("uv", item.identity, item.fingerprint), stamp,
)
""",
            str(uv),
        ],
        check=True,
    )
    reused = _pwsh(script, tmp_path)
    assert reused.returncode == 0, reused.stdout + reused.stderr
    record = registry.read_text()
    assert '"pdomain-ocr-cli"' in record
    assert '"installed_by": "pdomain-ocr-simple-gui"' in record


@pytest.mark.parametrize(
    ("case", "keep_uv", "keep_model"),
    [
        ("confirmed", False, False),
        ("default", True, True),
        ("cancel", True, True),
        ("legacy", True, True),
        ("late-legacy", True, True),
        ("other-tool", True, False),
        ("changed", False, True),
    ],
)
def test_windows_opt_in_cleanup_keeps_unselected_and_unsafe_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, keep_uv: bool, keep_model: bool
) -> None:
    if find_spec("pdomain_ops.suite.model_components") is None:
        pytest.skip("shared registry is not available in this environment")
    tools = tmp_path / "tools"
    tool = tools / "pdomain-ocr-cli"
    python = tool / "Scripts/python.exe"
    python.parent.mkdir(parents=True)
    _ = python.write_text('#!/bin/sh\nshift\nexec "$TEST_PYTHON" "$@"\n')
    python.chmod(0o755)
    receipt = tool / "uv-receipt.toml"
    receipt.touch()
    uv = tmp_path / "uv.exe"
    _ = uv.write_text(
        f"""#!{sys.executable}
import os, shutil, sys
if sys.argv[2] == "dir":
    print(os.environ["TEST_BINS" if "--bin" in sys.argv else "TEST_TOOLS"])
else:
    shutil.rmtree(os.environ["TEST_TOOL"])
"""
    )
    uv.chmod(0o755)
    cache = tmp_path / "cache"
    revision = "ab" * 20
    model = cache / "models--org--ocr" / "snapshots" / revision / "cache.pt"
    model.parent.mkdir(parents=True)
    _ = model.write_text("tracked OCR model")
    user_model = model.with_name("untracked.pt")
    _ = user_model.write_text("external model")
    uvx = tmp_path / "uvx.exe"
    _ = uvx.write_text("pre-existing companion")
    output = tmp_path / "pages.txt"
    _ = output.write_text("OCR output")
    local = tmp_path / "local"
    manifest = local / "Programs/pdomain-ocr-simple-gui/install-manifest.json"
    if case in {"legacy", "late-legacy"}:
        manifest.parent.mkdir(parents=True)
    if case == "legacy":
        manifest.touch()
    if case == "other-tool":
        (tools / "another-tool").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("UV_INSTALL_DIR", str(tmp_path))
    monkeypatch.setenv("TEST_PYTHON", sys.executable)
    monkeypatch.setenv("TEST_BINS", str(tmp_path))
    monkeypatch.setenv("TEST_TOOL", str(tool))
    monkeypatch.setenv("TEST_TOOLS", str(tools))
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path / "suite"))
    monkeypatch.setenv("HF_HUB_CACHE", str(cache))
    _ = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from pathlib import Path
from pdomain_ops.suite.component_files import ComponentFile
from pdomain_ops.suite.components import ComponentProbe, ComponentRegistry
from pdomain_ops.suite.model_components import ModelCacheEntry
registry = ComponentRegistry()
uv, cache = map(Path, sys.argv[1:3])
entries = (("uv", ComponentFile(uv)), ("model", ModelCacheEntry(cache, "org/ocr", sys.argv[3], "cache.pt")))
for kind, item in entries:
    assert registry.record_created(
        "pdomain-ocr-cli", "installer", ComponentProbe(kind, item.identity, item.fingerprint),
        item.fingerprint(),
    )
""",
            str(uv),
            str(cache),
            revision,
        ],
        check=True,
    )
    confirmation = "'NO'" if case == "cancel" else "'REMOVE'"
    change = ""
    if case == "changed":
        change = f"Add-Content -LiteralPath '{model}' -Value 'replacement'"
    elif case == "late-legacy":
        change = f"New-Item -ItemType File -Path '{manifest}' | Out-Null"
    flags = "" if case == "default" else "-RemoveUv -RemoveModels"
    result = _pwsh(
        f"""
function uv {{ & '{uv}' @args }}
function Get-Command {{ [pscustomobject]@{{ Source = '{uv}' }} }}
function Read-Host {{ {change}; {confirmation} }}
Invoke-CliUninstall {flags}
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert receipt.exists() is (case == "cancel")
    assert uv.exists() is keep_uv, result.stdout
    assert model.exists() is keep_model, result.stdout
    assert uvx.read_text() == "pre-existing companion"
    assert user_model.read_text() == "external model"
    assert output.read_text() == "OCR output"
    if case == "confirmed":
        assert f"  {uv}" in result.stdout
        assert f"  {model}" in result.stdout


@pytest.mark.parametrize(
    ("existing", "changed", "recorded"),
    [(True, False, False), (False, True, False), (False, False, True)],
)
def test_windows_setup_records_only_the_fresh_python_used_by_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool, changed: bool, recorded: bool
) -> None:
    if find_spec("pdomain_ops.suite.python_components") is None:
        pytest.skip("shared registry is not available in this environment")
    managed = tmp_path / "python"
    key = "cpython-3.13.18-windows-x86_64-none"
    base = managed / key / "python.exe"
    tool_python = tmp_path / "Scripts/python.exe"
    for interpreter in (base, tool_python):
        interpreter.parent.mkdir(parents=True)
        _ = interpreter.write_text(
            f"""#!{sys.executable}
import os, sys
sys._base_executable = os.environ["TEST_BASE"]
sys.argv = sys.argv[2:]
exec(sys.stdin.read())
"""
        )
        interpreter.chmod(0o755)
    marker = tmp_path / "installed"
    if existing:
        marker.touch()
    uv = tmp_path / "uv"
    _ = uv.write_text(
        f"""#!{sys.executable}
import os, sys
from pathlib import Path
marker = Path(os.environ["TEST_MARKER"])
if sys.argv[2] == "find":
    if not marker.is_file():
        raise SystemExit(1)
    print(os.environ["TEST_BASE"])
elif sys.argv[2] == "dir":
    print(os.environ["TEST_MANAGED"])
else:
    marker.touch()
    print("Installed Python 3.13.18")
    print(" + " + os.environ["TEST_KEY"])
"""
    )
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setenv("TEST_MANAGED", str(managed))
    monkeypatch.setenv("TEST_MARKER", str(marker))
    monkeypatch.setenv("TEST_BASE", str(base))
    monkeypatch.setenv("TEST_KEY", key)
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path))
    change = "Add-Content -LiteralPath $env:TEST_BASE -Value '# replaced'" if changed else ""
    result = _pwsh(
        f"""
Initialize-ManagedPython -Version '3.13' -WorkDir '{tmp_path}'
{change}
Register-SharedPythonTools -EnvironmentPath '{tmp_path}' -WorkDir '{tmp_path}'
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    registry = tmp_path / "components.json"
    assert registry.exists() is recorded, result.stdout + result.stderr
    if recorded:
        assert '"installed_by": "pdomain-ocr-cli"' in registry.read_text()
        assert key in registry.read_text()


@pytest.mark.parametrize(
    ("prior_package", "outcome", "created"),
    [
        (False, "installed", "True"),
        (True, "installed", "False"),
        (False, "already-installed", "False"),
    ],
)
def test_only_verified_fresh_windows_install_is_recorded(
    tmp_path: Path, prior_package: bool, outcome: str, created: str
) -> None:
    result = _pwsh(
        f"""
function Test-IsWindowsHost {{ return $true }}
function Get-MsvcToolsetFloor {{ return [pscustomobject]@{{ Found = $true; Version = [version]'14.40' }} }}
$script:Installed = $false
function Get-VcRuntimeStatus {{
    if ($script:Installed) {{ return [pscustomobject]@{{ Adequate = $true; Installed = [version]'14.50' }} }}
    return [pscustomobject]@{{ Adequate = $false; Missing = @('a', 'b', 'c'); Installed = $null }}
}}
function Get-VcRuntimeRegistration {{ if (${str(prior_package).lower()}) {{ 'previous-package' }} }}
function Install-VcRuntime {{
    param($WorkDir, [switch]$ReportExisting)
    if (-not $ReportExisting) {{ throw 'The install outcome must distinguish an existing package' }}
    $script:Installed = $true
    return '{outcome}'
}}
function Register-VcRuntimeClaim {{
    param($EnvironmentPath, [switch]$InstalledHere)
    Write-Host "created=$($InstalledHere.IsPresent)"
}}
Confirm-VcRuntime -EnvironmentPath '{tmp_path}' -WorkDir '{tmp_path}'
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert f"created={created}" in result.stdout


@pytest.mark.parametrize(
    ("confirmation", "exit_code", "expected"),
    [("no", 0, "kept"), ("REMOVE", 1602, "kept"), ("REMOVE", 0, "removed")],
)
def test_runtime_removal_requires_confirmation_and_reports_cancellation(
    tmp_path: Path, confirmation: str, exit_code: int, expected: str
) -> None:
    package = tmp_path / "VC_redist.x64.exe"
    package.touch()
    result = _pwsh(
        f"""
$script:Package = [pscustomobject]@{{
    PackageId = '11111111-1111-1111-1111-111111111111'; Version = '14.44.35211.0';
    Architecture = 'x64'; UninstallPath = '{package}'
}}
function Read-Host {{ return '{confirmation}' }}
function Get-VcRuntimeRegistration {{ return $script:Package }}
function Assert-MicrosoftSignature {{ param($Path) }}
function Start-ElevatedInstaller {{
    param($FilePath, $Arguments)
    if ($Arguments -ne '/uninstall /passive /norestart') {{ throw 'Unexpected arguments' }}
    if ({exit_code} -eq 0) {{ $script:Package = $null }}
    return {exit_code}
}}
Invoke-RegisteredVcRuntimeRemoval -Package $script:Package -CanRemove {{ $true }}
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "Other Windows apps may depend" in result.stdout
    assert result.stdout.splitlines()[-1] == expected


# --- uv bootstrap ----------------------------------------------------------


def _fake_shell(tmp_path: Path, exit_code: int) -> Path:
    shell = tmp_path / "fake-powershell"
    _ = shell.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$@" > {tmp_path / "shell.log"}\nexit {exit_code}\n',
        encoding="utf-8",
    )
    shell.chmod(0o755)
    return shell


def test_uv_bootstrap_runs_in_a_child_shell_with_process_only_bypass(tmp_path: Path) -> None:
    """astral's installer calls `exit` on failure, which would close the
    user's window under `irm | iex`, so it runs in a child process."""
    shell = _fake_shell(tmp_path, 0)
    result = _pwsh(f"Install-Uv -ShellPath '{shell}'\n'ok'", tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "shell.log").read_text(encoding="utf-8").splitlines() == [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        "irm https://astral.sh/uv/install.ps1 | iex",
    ]


def test_uv_bootstrap_failure_stops_the_installer(tmp_path: Path) -> None:
    shell = _fake_shell(tmp_path, 1)
    result = _pwsh(f"$global:LASTEXITCODE = 0\nInstall-Uv -ShellPath '{shell}'\n'ok'", tmp_path)
    assert result.returncode != 0
    assert "The uv installer failed (exit code 1)" in result.stderr
    assert "ok" not in result.stdout


def test_uv_bootstrap_reuses_uv_outside_path(tmp_path: Path) -> None:
    destination = tmp_path / "bin"
    destination.mkdir()
    existing = destination / "uv.exe"
    _ = existing.write_text("pre-existing")
    result = _pwsh(
        f"""
$env:UV_INSTALL_DIR = '{destination}'
function Install-Uv {{ throw "Existing uv was overlooked" }}
$Bootstrap = Initialize-WindowsUv -WorkDir '{tmp_path}'
if ($Bootstrap) {{ throw "An existing uv is not a bootstrap" }}
($env:PATH -split [IO.Path]::PathSeparator)[0]
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(destination)
    assert existing.read_text() == "pre-existing"


@pytest.mark.parametrize("external_companion", [False, True])
def test_uv_bootstrap_claims_only_its_staged_executables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, external_companion: bool
) -> None:
    if find_spec("pdomain_ops.suite.component_files") is None:
        pytest.skip("shared registry is not available in this environment")
    destination = tmp_path / "bin"
    destination.mkdir()
    if external_companion:
        _ = (destination / "uvx.exe").write_text("pre-existing")
    python = tmp_path / "Scripts/python.exe"
    python.parent.mkdir()
    _ = python.write_text('#!/bin/sh\nshift\nexec "$TEST_PYTHON" "$@"\n')
    python.chmod(0o755)
    monkeypatch.setenv("TEST_PYTHON", sys.executable)
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path / "suite"))
    result = _pwsh(
        f"""
$env:UV_INSTALL_DIR = '{destination}'
$env:UV_NO_MODIFY_PATH = "1"
function Install-Uv {{
    param([string]$StagingPath)
    New-Item -Path $StagingPath -ItemType Directory | Out-Null
    foreach ($File in @("uv.exe", "uvx.exe", "uvw.exe")) {{
        Set-Content -LiteralPath (Join-Path $StagingPath $File) -Value $File
    }}
}}
$Bootstrap = Initialize-WindowsUv -WorkDir '{tmp_path}'
if (Test-Path -LiteralPath (Join-Path $Bootstrap.Destination "uv.exe")) {{
    throw "The bootstrap should stay staged until the CLI is installed."
}}
Publish-WindowsUv -EnvironmentPath '{tmp_path}' -Bootstrap $Bootstrap
($env:PATH -split [IO.Path]::PathSeparator)[0]
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == str(destination)
    assert (destination / "uv.exe").read_text().strip() == "uv.exe"
    assert (destination / "uvw.exe").read_text().strip() == "uvw.exe"
    registry = (tmp_path / "suite/components.json").read_text()
    assert "uv.exe" in registry
    assert "uvw.exe" in registry
    assert ("uvx.exe" in registry) is not external_companion
    expected = "pre-existing" if external_companion else "uvx.exe"
    assert (destination / "uvx.exe").read_text().strip() == expected


def test_uv_bootstrap_with_an_older_wheel_preserves_existing_files(tmp_path: Path) -> None:
    destination = tmp_path / "bin"
    destination.mkdir()
    _ = (destination / "uvx.exe").write_text("pre-existing")
    stage = tmp_path / "staged"
    stage.mkdir()
    _ = (stage / "uv.exe").write_text("staged-uv")
    _ = (stage / "uvx.exe").write_text("staged-uvx")
    python = tmp_path / "Scripts/python.exe"
    python.parent.mkdir()
    _ = python.write_text("#!/bin/sh\nexit 77\n")
    python.chmod(0o755)
    result = _pwsh(
        f"""
$Bootstrap = [pscustomobject]@{{
    Staging = '{stage}'
    Destination = '{destination}'
    OriginalPath = $env:PATH
    ModifyPath = $false
}}
Publish-WindowsUv -EnvironmentPath '{tmp_path}' -Bootstrap $Bootstrap
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (destination / "uv.exe").read_text() == "staged-uv"
    assert (destination / "uvx.exe").read_text() == "pre-existing"


# --- native command runner -------------------------------------------------


def test_native_runner_fails_when_command_cannot_start(tmp_path: Path) -> None:
    """A command that never starts must not inherit a stale exit code of 0."""
    result = _pwsh(
        f"""
$global:LASTEXITCODE = 0
Invoke-NativeCaptured -FilePath '{tmp_path / "missing-uv"}' -ArgumentList @("tool", "install")
"returned"
""",
        tmp_path,
    )
    assert result.returncode != 0
    assert "Could not run" in result.stderr
    assert "returned" not in result.stdout


# --- uv failure classification ---------------------------------------------


def test_uv_failure_classification(tmp_path: Path) -> None:
    # Texts are real uv 0.11.26 output (see tests/test_install_ps1.py).
    result = _pwsh(
        """
$Http503 = "error: Request failed after 3 retries in 8.3s`n  Caused by: HTTP status server error (503 Service Unavailable)"
$Refused = "error: Request failed after 3 retries in 8.0s`n  Caused by: Connection refused (os error 111)"
$Auth401 = "  x No solution found when resolving dependencies:`nhint: An index URL could not be queried due to a lack of valid authentication credentials (401 Unauthorized)"
$NoVersion = "  x No solution found when resolving dependencies:`n  Because there is no version of markupsafe==0.0.1"
"{0} {1} {2} {3}" -f (Test-UvTransientFailure $Http503), (Test-UvTransientFailure $Refused),
    (Test-UvTransientFailure $Auth401), (Test-UvTransientFailure $NoVersion)
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["True", "True", "False", "False"]


# --- toolset floor ---------------------------------------------------------


def test_pe_linker_version_reads_header_and_rejects_other_files(tmp_path: Path) -> None:
    _ = (tmp_path / "c10.dll").write_bytes(_pe_bytes(14, 42))
    _ = (tmp_path / "notes.dll").write_bytes(b"not a PE image at all, just text" * 4)
    result = _pwsh(
        f"""
"$(Get-PeLinkerVersion -Path '{tmp_path / "c10.dll"}')"
"[$(Get-PeLinkerVersion -Path '{tmp_path / "notes.dll"}')]"
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["14.42", "[]"]


def test_toolset_floor_is_newest_msvc_binary_except_runtime_copies(tmp_path: Path) -> None:
    env = tmp_path / "env"
    (env / "Lib" / "site-packages" / "torch" / "lib").mkdir(parents=True)
    lib = env / "Lib" / "site-packages" / "torch" / "lib"
    _ = (lib / "c10.dll").write_bytes(_pe_bytes(14, 42))
    _ = (lib / "libiomp5md.dll").write_bytes(_pe_bytes(14, 29))
    # A bundled runtime copy and a non-MSVC linker must not raise the floor.
    _ = (lib / "msvcp140.dll").write_bytes(_pe_bytes(14, 50))
    _ = (lib / "vcruntime140_1.dll").write_bytes(_pe_bytes(14, 50))
    _ = (env / "Lib" / "site-packages" / "mingw.pyd").write_bytes(_pe_bytes(2, 40))
    _ = (env / "Lib" / "site-packages" / "readme.txt").write_bytes(_pe_bytes(14, 99))
    result = _pwsh(
        f"""
$Floor = Get-MsvcToolsetFloor -EnvironmentPath '{env}'
"$($Floor.Version)"
Split-Path -Leaf $Floor.File
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["14.42", "c10.dll"]


def test_toolset_floor_reports_missing_environment(tmp_path: Path) -> None:
    result = _pwsh(
        f"""
$Floor = Get-MsvcToolsetFloor -EnvironmentPath '{tmp_path / "absent"}'
"[$($Floor.Version)] $($Floor.Found)"
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[] False"


def test_toolset_floor_skips_unreadable_files(tmp_path: Path) -> None:
    env = tmp_path / "env"
    env.mkdir()
    _ = (env / "good.pyd").write_bytes(_pe_bytes(14, 44))
    locked = env / "locked.dll"
    _ = locked.write_bytes(_pe_bytes(14, 99))
    locked.chmod(0o000)
    try:
        result = _pwsh(
            f"""
$Floor = Get-MsvcToolsetFloor -EnvironmentPath '{env}'
"$($Floor.Version)"
""",
            tmp_path,
        )
    finally:
        locked.chmod(0o644)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "14.44"


def test_toolset_floor_is_empty_without_msvc_binaries(tmp_path: Path) -> None:
    (tmp_path / "env").mkdir()
    result = _pwsh(
        f"""
$Floor = Get-MsvcToolsetFloor -EnvironmentPath '{tmp_path / "env"}'
"[$($Floor.Version)]"
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


# --- runtime status --------------------------------------------------------


def _status(tmp_path: Path, versions: Mapping[str, str | None], minimum: str) -> list[str]:
    entries = "; ".join(
        f"'{name}' = " + (f"[version]'{v}'" if v else "$null") for name, v in versions.items()
    )
    result = _pwsh(
        f"""
function Get-VcRuntimeFileVersions {{ [ordered]@{{ {entries} }} }}
$Minimum = {f"[version]'{minimum}'" if minimum else "$null"}
$S = Get-VcRuntimeStatus -Minimum $Minimum
"$($S.Adequate)|$($S.Installed)|$($S.Missing -join ',')"
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip().split("|")


ALL_14_44 = {"msvcp140.dll": "14.44", "vcruntime140.dll": "14.44", "vcruntime140_1.dll": "14.44"}


def test_status_adequate_when_all_dlls_meet_floor(tmp_path: Path) -> None:
    assert _status(tmp_path, ALL_14_44, "14.42") == ["True", "14.44", ""]


def test_status_inadequate_when_a_dll_is_missing(tmp_path: Path) -> None:
    versions = {**ALL_14_44, "msvcp140.dll": None}
    assert _status(tmp_path, versions, "14.42") == ["False", "14.44", "msvcp140.dll"]


def test_status_inadequate_when_oldest_dll_is_below_floor(tmp_path: Path) -> None:
    versions = {**ALL_14_44, "msvcp140.dll": "14.29"}
    assert _status(tmp_path, versions, "14.42") == ["False", "14.29", ""]


def test_status_without_floor_only_needs_the_dlls(tmp_path: Path) -> None:
    versions = dict.fromkeys(ALL_14_44, "14.0")
    assert _status(tmp_path, versions, "") == ["True", "14.0", ""]


# --- installing the redistributable ----------------------------------------


def _install(
    tmp_path: Path,
    exit_code: str = "0",
    status: str = "Valid",
    organizations: str = "'Microsoft Corporation'",
    root: str = MICROSOFT_ROOT_2011,
    start_error: str = "",
) -> subprocess.CompletedProcess[str]:
    start_body = start_error or exit_code
    return _pwsh(
        f"""
function Invoke-WebRequest {{
    param([string]$Uri, [string]$OutFile, [switch]$UseBasicParsing)
    Add-Content -Path calls.log -Value "download $Uri basic=$UseBasicParsing"
    Set-Content -Path $OutFile -Value "fake exe"
}}
function Get-AuthenticodeSignature {{
    param([string]$FilePath)
    [pscustomobject]@{{
        Status = "{status}"
        SignerCertificate = [pscustomobject]@{{ Subject = "{MICROSOFT_SIGNER}" }}
    }}
}}
function Get-CertificateOrganizations {{ param($Certificate) @({organizations}) }}
function Get-CertificateRootThumbprint {{ param($Certificate) "{root}" }}
function Start-ElevatedInstaller {{
    param([string]$FilePath, [string]$Arguments)
    Add-Content -Path calls.log -Value "start $(Split-Path -Leaf $FilePath) $Arguments"
    {start_body}
}}
$Outcome = Install-VcRuntime -WorkDir '{tmp_path}'
"outcome=$Outcome"
""",
        tmp_path,
    )


def _calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "calls.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def test_install_runs_signed_official_redistributable_elevated(tmp_path: Path) -> None:
    result = _install(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "outcome=installed" in result.stdout
    assert _calls(tmp_path) == [
        "download https://aka.ms/vc14/vc_redist.x64.exe basic=True",
        "start vc_redist.x64.exe /install /passive /norestart",
    ]


def test_install_reports_restart_without_restarting(tmp_path: Path) -> None:
    result = _install(tmp_path, exit_code="3010")
    assert result.returncode == 0, result.stderr
    assert "outcome=restart-required" in result.stdout


def test_install_treats_already_installed_as_installed(tmp_path: Path) -> None:
    result = _install(tmp_path, exit_code="1638")
    assert result.returncode == 0, result.stderr
    assert "outcome=installed" in result.stdout


def test_install_fails_on_installer_cancel_and_error_codes(tmp_path: Path) -> None:
    cancelled_dir = tmp_path / "a"
    cancelled_dir.mkdir()
    cancelled = _install(cancelled_dir, "1602")
    assert cancelled.returncode != 0
    assert "cancelled (exit code 1602)" in cancelled.stderr
    failed_dir = tmp_path / "b"
    failed_dir.mkdir()
    failed = _install(failed_dir, "1603")
    assert failed.returncode != 0
    assert "failed with exit code 1603" in failed.stderr


def test_install_explains_access_denied_for_standard_user(tmp_path: Path) -> None:
    """Real result on Windows 11 with UAC off: a standard user gets exit 5."""
    result = _install(tmp_path, exit_code="5")
    assert result.returncode != 0
    assert "denied access (exit code 5)" in result.stderr
    assert "administrator account" in result.stderr


def test_install_reports_cancelled_uac_prompt(tmp_path: Path) -> None:
    result = _install(
        tmp_path,
        # Process.Start called from PowerShell surfaces as a
        # MethodInvocationException wrapping the Win32Exception.
        start_error=(
            "throw [System.Management.Automation.MethodInvocationException]::new("
            '"Exception calling Start", [System.ComponentModel.Win32Exception]::new(1223))'
        ),
    )
    assert result.returncode != 0
    assert "administrator prompt was cancelled" in result.stderr


def test_install_reports_other_start_failures_as_such(tmp_path: Path) -> None:
    result = _install(tmp_path, start_error='throw "file vanished"')
    assert result.returncode != 0
    assert "could not be started: file vanished" in result.stderr


def test_install_fails_without_exit_code(tmp_path: Path) -> None:
    result = _install(tmp_path, exit_code="$null")
    assert result.returncode != 0
    assert "did not report an exit code" in result.stderr


def test_install_never_runs_an_unsigned_download(tmp_path: Path) -> None:
    result = _install(tmp_path, status="NotSigned")
    assert result.returncode != 0
    assert "not validly signed" in result.stderr
    assert not any(c.startswith("start ") for c in _calls(tmp_path))


def test_install_never_runs_a_download_signed_by_someone_else(tmp_path: Path) -> None:
    for name, organizations in [
        ("other", "'Evil Corp'"),
        ("lower", "'microsoft corporation'"),
        ("two", "'Microsoft Corporation', 'Evil Corp'"),
        ("none", ""),
    ]:
        case = tmp_path / name
        case.mkdir()
        result = _install(case, organizations=organizations)
        assert result.returncode != 0, name
        assert "not Microsoft Corporation" in result.stderr, name
        assert not any(c.startswith("start ") for c in _calls(case)), name


def test_install_never_runs_a_download_from_another_root(tmp_path: Path) -> None:
    result = _install(tmp_path, root="0000000000000000000000000000000000000000")
    assert result.returncode != 0
    assert "not Microsoft Root Certificate Authority 2011" in result.stderr
    assert not any(c.startswith("start ") for c in _calls(tmp_path))


def _real_cert(subject: str) -> str:
    """PowerShell that builds a real self-signed certificate as $Cert."""
    return f"""
$Key = [System.Security.Cryptography.RSA]::Create(2048)
$Request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
    '{subject}', $Key, [System.Security.Cryptography.HashAlgorithmName]::SHA256,
    [System.Security.Cryptography.RSASignaturePadding]::Pkcs1)
$Cert = $Request.CreateSelfSigned([DateTimeOffset]::Now.AddDays(-1), [DateTimeOffset]::Now.AddDays(1))
"""


def test_certificate_organizations_reads_real_subject_fields(tmp_path: Path) -> None:
    result = _pwsh(
        _real_cert("CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, C=US")
        + "(Get-CertificateOrganizations -Certificate $Cert) -join '|'",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Microsoft Corporation"


def test_certificate_organizations_ignores_o_inside_quoted_values(tmp_path: Path) -> None:
    result = _pwsh(
        _real_cert('CN="x, O=Microsoft Corporation, y", O=Evil Corp, C=US')
        + "(Get-CertificateOrganizations -Certificate $Cert) -join '|'",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Evil Corp"


def test_root_thumbprint_of_self_signed_certificate_is_its_own(tmp_path: Path) -> None:
    result = _pwsh(
        _real_cert("CN=Test Root, O=Test")
        + "(Get-CertificateRootThumbprint -Certificate $Cert) -eq $Cert.Thumbprint",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


# --- the whole runtime step ------------------------------------------------


def _confirm(
    tmp_path: Path, statuses: list[str], install_result: str = "installed", skip: bool = False
) -> subprocess.CompletedProcess[str]:
    """`statuses` are successive Get-VcRuntimeStatus answers, as
    "adequate|installed|missing"."""
    answers = ", ".join(f"'{s}'" for s in statuses)
    install_body = f'"{install_result}"' if install_result != "throw" else 'throw "prompt refused"'
    skip_line = (
        '$env:PD_OCR_SKIP_VC_RUNTIME = "1"' if skip else "$env:PD_OCR_SKIP_VC_RUNTIME = $null"
    )
    return _pwsh(
        f"""
{skip_line}
$script:Answers = @({answers})
$script:Asked = 0
function Get-MsvcToolsetFloor {{
    param([string]$EnvironmentPath)
    [pscustomobject]@{{ Version = [version]'14.42'; File = 'C:\\env\\torch\\lib\\c10.dll'; Found = $true }}
}}
function Get-VcRuntimeStatus {{
    param([version]$Minimum)
    $Parts = $script:Answers[$script:Asked].Split('|')
    $script:Asked++
    [pscustomobject]@{{
        Adequate = [bool]::Parse($Parts[0])
        Installed = $(if ($Parts[1]) {{ [version]$Parts[1] }} else {{ $null }})
        Missing = @($Parts[2].Split(',') | Where-Object {{ $_ }})
        Minimum = $Minimum
    }}
}}
function Install-VcRuntime {{
    param([string]$WorkDir)
    Add-Content -Path calls.log -Value "install"
    {install_body}
}}
$Restart = Confirm-VcRuntime -EnvironmentPath 'C:\\env' -WorkDir '{tmp_path}'
"restart=$Restart"
""",
        tmp_path,
    )


def test_confirm_skips_install_when_runtime_is_adequate(tmp_path: Path) -> None:
    result = _confirm(tmp_path, ["True|14.44|"])
    assert result.returncode == 0, result.stderr
    assert "restart=False" in result.stdout
    assert "14.42 or newer" in result.stdout
    assert _calls(tmp_path) == []


@pytest.mark.parametrize("restart", [False, True])
def test_staged_runtime_check_completes_before_release_lookup(
    tmp_path: Path, restart: bool
) -> None:
    environment = tmp_path / "staged environment"
    environment.mkdir()
    result = _pwsh(
        f"""
$Text = [IO.File]::ReadAllText('{INSTALLER}')
$Text = $Text.Replace(
    ($Definitions | Where-Object Name -eq 'Test-IsWindowsHost').Extent.Text,
    'function Test-IsWindowsHost {{ $true }}'
)
$Text = $Text.Replace(
    ($Definitions | Where-Object Name -eq 'Confirm-VcRuntime').Extent.Text,
    'function Confirm-VcRuntime {{
        param([string]$EnvironmentPath, [string]$WorkDir)
        if ($EnvironmentPath -ne "{environment}" -or $WorkDir -ne "{tmp_path}") {{
            throw "Unexpected staging paths"
        }}
        $' + '{str(restart).lower()}' + '
    }}'
)
function Invoke-RestMethod {{ throw "Unexpected release lookup" }}
& ([scriptblock]::Create($Text)) -CheckStagedRuntime '{environment}'
"ready"
""",
        tmp_path,
    )
    if restart:
        assert result.returncode != 0
        assert "Restart Windows before retrying the OCR update." in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert "ready" in result.stdout


def test_confirm_installs_missing_runtime_and_rechecks(tmp_path: Path) -> None:
    result = _confirm(tmp_path, ["False||msvcp140.dll", "True|14.50|"])
    assert result.returncode == 0, result.stderr
    assert "msvcp140.dll not found" in result.stdout
    assert "restart=False" in result.stdout
    assert _calls(tmp_path) == ["install"]


def test_confirm_installs_when_runtime_is_older_than_floor(tmp_path: Path) -> None:
    result = _confirm(tmp_path, ["False|14.29|", "True|14.50|"])
    assert result.returncode == 0, result.stderr
    assert "older than 14.42" in result.stdout
    assert "c10.dll" in result.stdout


def test_confirm_reports_restart_required(tmp_path: Path) -> None:
    result = _confirm(tmp_path, ["False||msvcp140.dll"], install_result="restart-required")
    assert result.returncode == 0, result.stderr
    assert "restart=True" in result.stdout


def test_confirm_fails_with_manual_steps_when_install_is_refused(tmp_path: Path) -> None:
    result = _confirm(tmp_path, ["False||msvcp140.dll"], install_result="throw")
    assert result.returncode != 0
    assert "https://aka.ms/vc14/vc_redist.x64.exe" in result.stdout
    assert "/install /passive /norestart" in result.stdout
    assert "pdomain-ocr is installed, but OCR cannot run yet" in result.stderr


def test_confirm_fails_when_a_dll_is_still_missing_after_install(tmp_path: Path) -> None:
    result = _confirm(tmp_path, ["False||msvcp140.dll", "False||msvcp140.dll"])
    assert result.returncode != 0
    assert "msvcp140.dll is still missing" in result.stderr


def test_confirm_warns_when_newest_runtime_is_older_than_floor(tmp_path: Path) -> None:
    """After installing Microsoft's newest runtime there is nothing left to
    do, so an over-new toolset claim warns instead of failing the install."""
    result = _confirm(tmp_path, ["False|14.29|", "False|14.50|"])
    assert result.returncode == 0, result.stderr
    assert "WARNING: Visual C++ runtime 14.50 is the newest" in result.stdout
    assert "restart=False" in result.stdout


def test_confirm_honours_skip_variable_without_installing(tmp_path: Path) -> None:
    result = _confirm(tmp_path, ["False||msvcp140.dll"], skip=True)
    assert result.returncode != 0
    assert "PD_OCR_SKIP_VC_RUNTIME=1" in result.stderr
    assert _calls(tmp_path) == []


# --- Windows main-flow steps -----------------------------------------------


def _fake_uv_tool_dir(tmp_path: Path, exit_code: int) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    _ = uv.write_text(f"#!/bin/sh\necho '{tmp_path / 'tools'}'\nexit {exit_code}\n")
    uv.chmod(0o755)


def _complete(tmp_path: Path, exit_code: int) -> subprocess.CompletedProcess[str]:
    _fake_uv_tool_dir(tmp_path, exit_code)
    return _pwsh(
        f"""
$env:PATH = '{tmp_path / "bin"}' + [IO.Path]::PathSeparator + $env:PATH
function Confirm-VcRuntime {{
    param([string]$EnvironmentPath, [string]$WorkDir)
    Add-Content -Path checked.log -Value $EnvironmentPath
    $true
}}
$Restart = Complete-WindowsInstall -WorkDir '{tmp_path}'
"restart=$Restart"
""",
        tmp_path,
    )


def test_windows_step_checks_the_pdomain_tool_environment(tmp_path: Path) -> None:
    result = _complete(tmp_path, 0)
    assert result.returncode == 0, result.stderr
    checked = (tmp_path / "checked.log").read_text(encoding="utf-8").strip()
    assert checked == str(tmp_path / "tools" / "pdomain-ocr-cli")
    assert "restart=True" in result.stdout


def test_windows_step_fails_when_uv_tool_dir_fails(tmp_path: Path) -> None:
    result = _complete(tmp_path, 2)
    assert result.returncode != 0
    assert "'uv tool dir' failed with exit code 2" in result.stderr


def test_summary_tells_user_to_restart_without_restarting(tmp_path: Path) -> None:
    result = _pwsh(
        "Write-InstallSummary -RestartRequired $true\nWrite-InstallSummary -RestartRequired $false",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "Done, but Windows must restart before OCR can run" in result.stdout
    assert "never restarts Windows" in result.stdout
    assert result.stdout.count("Done!") == 1


def test_elevated_start_uses_process_start_with_runas() -> None:
    """Start-ElevatedInstaller must use Process.Start, which keeps the 1223
    code that Windows PowerShell 5.1's Start-Process loses on a UAC cancel."""
    script = INSTALLER.read_text(encoding="utf-8")
    body = script[script.index("function Start-ElevatedInstaller") :]
    body = body[: body.index("\nfunction ")]
    assert "[System.Diagnostics.Process]::Start($Info)" in body
    assert '$Info.Verb = "runas"' in body


def test_uac_cancel_detection_walks_the_exception_chain(tmp_path: Path) -> None:
    result = _pwsh(
        """
$Inner = [System.ComponentModel.Win32Exception]::new(1223)
$Wrapped = [System.Management.Automation.MethodInvocationException]::new("x", $Inner)
$Deep = [System.InvalidOperationException]::new("y", $Wrapped)
$Other = [System.ComponentModel.Win32Exception]::new(2)
"{0} {1} {2}" -f (Test-UacCancelled $Wrapped), (Test-UacCancelled $Deep), (Test-UacCancelled $Other)
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["True", "True", "False"]
