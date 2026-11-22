---
kind: handoff
status: "active"
created: "2026-11-22"
created_at: "2026-11-22T01:29:50Z"
owner: agent:codex
branch: feat/ocr-cli-update
scope: ocr-cli-update-recovery
worktree: /mnt/work/projects/pdomain/.worktrees/ocr-cli-update
base_commit: "57c396d5f8ef876ada6e6a57e1f7efc3a8857840"
supersedes: "2026-11-22-001114-ocr-cli-update-recovery.md"
handoff_reason: user_requested
host: codex
---

# Handoff: OCR CLI update recovery and Windows testing

## Goal

Verify the installed CLI candidate before reporting an update as successful.
Restore the old CLI offline if the candidate fails. Use the local Windows VM
to reproduce CLI gaps and verify fixes against the branch wheel.

## Done

- The local feature branch has explicit CLI updates, opt-in background checks,
  and model prefetch. Production recovery remains at the plan stage.
- Disposable Linux and native Windows uv tests installed a second version and
  restored the old environment and both launchers offline. On Windows a staged
  PowerShell worker waited for the active launcher and its Python process.
  Spaces, mixed case, and an unrelated tool were covered.
- On Windows 11 build 26200 with Windows PowerShell 5.1, the real candidate
  wheel passed plain OCR on Python 3.12 and 3.13. The 3.13 launcher passed a
  recursive Unicode text batch, layout reports, collision rejection, partial
  batch with a corrupt PNG, and locked-output preservation with no leftovers.
- The real installer, using a fixture release, honored model skip, saved opt-in
  under APPDATA, and rejected the wrong release tag and digest. Explicit
  update check and background-check suppression passed with fixture responses.
- Native fast tests returned 503 passes, 165 failures, 16 skips, and one
  collection error. Of the failures, 148 were missing Git, sh or PowerShell 7,
  or POSIX-only fixtures. The real-model suite returned 12 passes and four
  JSON failures. Three subagents audited OCR, install, and update coverage.

## Not done and blockers

- JSON staging reopens files read-only before flushing. Both paths in
  _artifacts.py fail on Windows. Native fsync on a writable handle passed.
- On Python 3.11 the installed wheel starts help and version, but OCR
  fails because pdomain-ops 0.12.6 imports typing.override in its GPU
  dispatcher. The CLI misattributes the import failure to book-tools.
  The locked 3.11 launcher also failed. One test separately imports
  typing.override during collection.
- OpenCV filename reads break Unicode contour input and illustration rereads.
  The crop command returned success with zero crops versus one on ASCII input.
  Byte-buffer decoding worked in the Windows probe.
- The automatic update notice prints a Unix installer command on Windows.
  Prefetch failed at a 260-character cache path and passed online and offline
  with a shorter cache path.
- Production replacement, candidate startup failure, interruption recovery,
  PowerShell 7, and CUDA remain unverified. Existing Windows CI installs the
  latest published wheel and exercises one CPU image.

## Failed approaches and decisions

Keep uv backups on the original filesystem but outside discovery paths. Use
distinct paths for the environment and launchers to avoid a basename collision.
The installer deletes the wheel named in the old uv receipt. Keep original
absolute restore paths. The initial prefetch harness treated a partially
populated cache as success. Trust command exit status and offline validation.

## Pointers

- `docs/plans/2026-11-21-cli-update-recovery.md`
- `docs/architecture/installation-and-updates.md`
- `pdomain_ocr_cli/_artifacts.py`
- `pdomain_ocr_cli/_self_update.py`
- `pdomain_ocr_cli/_update_check.py`
- `install.ps1`
- `tests/test_cli_update.py`
- `.github/workflows/windows-install.yml`

Windows scripts, suite XML, runtime traceback, and case logs are in the local
VM share at /var/lib/omarchy/windows/mounts/users/1000/shared/ocr-cli-native.
The disposable update proof is in the sibling ocr-recovery-native directory.
The VM was left running. Tests used isolated installs and did not change the
repository. The branch remains local.

## Resume steps

1. Read the recovery plan and the Windows CLI progress and traceback logs.
2. Prioritize JSON staging and Python 3.11 runtime startup. Coordinate the
   dependency and Unicode contour fixes with their upstream projects.
3. Exercise the branch wheel on the VM as changes land, especially JSON,
   Unicode crops and contour, and offline model prefetch.
4. Follow the recovery plan with failure injection after staging, activation
   and interruption. Verify the installed candidate before reporting success.
5. Keep POSIX contract tests on POSIX. Prepare a native Windows branch-wheel
   acceptance run. Report which recovery and platform checks actually run.
