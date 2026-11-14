---
Status: active
Owner: CT
Created: 2026-11-13
Last verified: 2026-11-13
Kind: research
---

# Windows installer proof, 2026-11-13

## Agent Index

- **Kind:** research
- **Status:** active
- **Read when:** changing `install.ps1`, the Windows install instructions, or the Visual C++ runtime check, or judging what real Windows coverage exists.
- **Search terms:** Windows, PowerShell 5.1, execution policy, standard user, Visual C++ Redistributable, vc_redist, WinError 126, c10.dll, uv retry, 503.

## Goal

Find out whether a Windows user can install and run `pdomain-ocr` 0.9.3 with
`install.ps1`, and fix what stopped them. The owner's first attempt, on
2026-11-13, hit three failures:

- A `Restricted` execution policy made the uv installer close PowerShell.
- `uv` failed with HTTP 503 from the pdomain index, yet the script printed
  `Done`.
- OCR failed with `WinError 126` loading `torch\lib\c10.dll`, because the
  Visual C++ runtime was missing. Installing Microsoft's
  `vc_redist.x64.exe /install /passive /norestart` by hand fixed it.

## Method

All runs used the `omarchy-windows` VM, `dockurr/windows` 6.06 running
Windows 11 build 26100 with 6 CPU cores, 16 GB of RAM and no GPU. Commands
were typed through the QEMU monitor, and results were read from PowerShell
transcripts on the shared folder.

1. Recorded the VM state from an administrator PowerShell.
2. Created a local account, `pdtest`, in the Users group only. Opened
   Windows PowerShell as that user with `runas`.
3. As `pdtest`, ran the fixed `install.ps1` piped into `iex`, first under the
   default policy, then after the session-only policy command.
4. As `pdtest`, ran `pdomain-ocr` on the shared one-page test image,
   SHA256 `78ca7f98bcc65ca75f23d71b673ed180417d4f8e5046d21104b3835d2f716293`.
5. Read MSVC linker versions from every `.dll` and `.pyd` in the installed
   tool environment.
6. Ran the real runtime install step, `Install-VcRuntime`, as `pdtest` and
   again as the `docker` administrator account.

The first run used installer SHA256
`255a76eaf54dac6d5a02fc5cb1b130b2940b2eb8c78e609b7498ee5870a1cc83`. Review then
changed the uv bootstrap, the signature check and failure handling. A second
run used the final installer, SHA256
`6b8ecfd87e68caeef62b838b1b2eed3d206e74543eff15d66c9b757558f280b6`:

1. As `pdtest`, under the `Restricted` policy and without the policy command,
   ran the child-process uv bootstrap and then the full piped install.
2. As `docker`, ran the real runtime install step again, then printed the
   parsed signer organization and chain root, and tried to write and delete
   the installer while holding the same lock the installer uses.

The owner then approved turning UAC on and one Windows restart. Before it,
the `docker` account set `EnableLUA` to 1, `ConsentPromptBehaviorUser` to 3
(ask for credentials) and uninstalled the 14.52 runtime; the uninstall exited
0 and removed all three DLLs. The third run used installer SHA256 prefix
`e3c080cfe62f52f8`, which starts the elevated step with `Process.Start`:

1. As `pdtest`, with no runtime, ran the piped install and pressed Esc at the
   UAC credential prompt.
2. As `docker`, installed Microsoft's 14.44.35211 redistributable, approving
   the UAC consent prompt.
3. As `pdtest`, ran the piped install again, entered the `docker` password at
   the UAC credential prompt, and then ran OCR.

## Evidence

**VM state.** Windows PowerShell 5.1.26100.7920. UAC is off: `EnableLUA` is
0, so administrators always run elevated and no consent prompt can appear.
Every execution-policy scope was `Undefined`, which Windows 11 treats as
`Restricted`. The owner's earlier manual install left Visual C++ runtime
14.52.37029 in place.

**Execution policy.** In the first run, under `Restricted`, the installer
stopped before starting the uv installer and printed the session-only
command. The window stayed open, and `$?` was `False`. Review replaced that
check: the final installer runs the uv installer in a child PowerShell with
`-ExecutionPolicy Bypass`. In the second run, under `Restricted` with no
policy command, that bootstrap printed "everything's installed!". The
`Process` and `CurrentUser` scopes stayed `Undefined`, and the full install
then finished in 31 seconds with `Done!`. After
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force`, the
saved `CurrentUser` and `LocalMachine` policies were still `Undefined`.

**Standard-user install.** As `pdtest`, the installer bootstrapped uv 0.13.8
into `C:\Users\pdtest\.local\bin`. The pdomain index then returned HTTP 503
for `eventsourcing` twice. Each time, uv reported "Request failed after 3
retries", and the installer waited 15 seconds and then 45 seconds. The third
attempt installed 108 packages. The run took 209 seconds and ended with
`Done!`. No administrator rights were used.

**Runtime check.** The installer reported "Visual C++ runtime 14.52 found;
pdomain-ocr needs 14.51 or newer". The 14.51 floor came from Pillow, pandas,
matplotlib, pydantic-core, rapidfuzz, fontTools and other extensions. NumPy,
h5py, OpenCV and others were built with 14.44. Torch 2.15.0's `c10.dll` and
`torch_cpu.dll` were built with 14.42, the figure read from the torch wheel
on Linux.

**OCR as a standard user.** `pdomain-ocr --version` printed `pdomain-ocr
0.9.3`. OCR of the test page on the CPU exited 0 in 69 seconds. The output
began "18 THE DOCTRINE OF FILIAL DUTY / CHAPTER III / THE FILIAL DUTY OF
FEUDAL PRINCES". It was byte-identical to the owner's earlier administrator
run, which Notepad counted as 1,133 characters.

**Runtime install step.** Both accounts downloaded
`https://aka.ms/vc14/vc_redist.x64.exe`, product version 14.52.37029.0.
`Get-AuthenticodeSignature` reported `Valid`, signed by
`CN=Microsoft Corporation, O=Microsoft Corporation, L=Redmond, S=Washington,
C=US`. As `pdtest`, with UAC off, the start was not elevated and the
redistributable exited with code 5, access denied. The step reported a
failure. As `docker`, the redistributable succeeded over the existing 14.52
runtime, and the check then found 14.52 against the 14.51 floor.

**Final signature check.** In the second run, the parsed signer organization
was exactly `Microsoft Corporation`, and the chain root was
`8F43288AD272F3103B6FB1428485EA3014C0BCFE`, Microsoft Root Certificate
Authority 2011. The redistributable ran and succeeded while the installer's
read-only lock was held. With that lock held, opening the file for writing
and deleting it both failed.

**UAC on, missing runtime.** The installer reported all three DLLs missing,
downloaded and verified the redistributable, and Windows showed a credential
prompt: "Microsoft Visual C++ v14 Redistributable (x64) - 14.52.37029",
verified publisher Microsoft Corporation, asking for the `docker` password.
Pressing Esc cancelled it. The first attempt used `Start-Process`, and Windows
PowerShell 5.1 reported the cancel as an `InvalidOperationException` with no
Windows error code, so the installer's message said "could not be started".
After the switch to `Process.Start`, the same cancel read "the administrator
prompt was cancelled". Both times the install failed with the manual steps,
printed no `Done`, and left the DLLs missing. The pdomain index returned 503
once in this run too, and the retry recovered.

**UAC on, runtime too old.** With 14.44.35211 installed, the installer
reported "Visual C++ runtime 14.44 is older than 14.51", naming fontTools'
`cu2qu.cp313-win_amd64.pyd`. After the `docker` password was entered at the
prompt, the redistributable installed 14.52.37029 without asking for a
restart. The recheck passed and the run ended with `Done!` after 50 seconds.
OCR as `pdtest` then exited 0 in 81 seconds with byte-identical output.

## Conclusions

- With UAC on, a standard user gets a real credential prompt for the
  runtime step only. Cancelling it fails clearly, and approving it repairs a
  missing or old runtime without a restart.
- The final installer works under the default `Restricted` policy without
  the session-only command, so the README no longer asks for it. The
  installer published before this fix still needs it.
- Retrying uv's own network failures fixed a real install. The pdomain index
  on GitHub Pages returned 503 for several seconds at a time.
- A standard account can install and run `pdomain-ocr` once the Visual C++
  runtime is present.
- The runtime floor depends on which wheels uv picks, not just torch. On
  this day it was 14.51, so a fixed torch-derived floor of 14.42 would have
  been wrong. Reading it from the installed files keeps the check correct.

## Next steps

- The VM was left with UAC on. The owner asked for it to be turned off again,
  which needs another restart; that waits for the owner.
- Done after this note: `install.sh` now retries uv's network failures the
  same way and checks that the uv bootstrap actually installed uv.

## What this does NOT establish

- The redistributable never returned 3010 or 1641, so the restart-required
  path is covered only by tests that fake the Windows calls. Exit codes 1602
  and 1638 were also not seen.
- Only the credential prompt was tested for the runtime step. The consent
  prompt was seen only when `docker` installed 14.44 by hand.
- Only Windows PowerShell 5.1 ran; PowerShell 7 on Windows did not.
- This is a one-page CPU smoke test, not a check of OCR quality, GPU use or
  CUDA detection on Windows.
- OCR ran only after the first install. After the final install, only
  `pdomain-ocr --version` was checked.
- It used the published 0.9.3 wheel with the fixed installer, read from the
  shared folder. The `irm` download of the script from GitHub was not used,
  because the fix is not pushed.
