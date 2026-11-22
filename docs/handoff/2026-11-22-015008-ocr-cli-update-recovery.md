---
kind: handoff
status: "active"
created: "2026-11-22"
created_at: "2026-11-22T01:50:08Z"
owner: agent:codex
branch: feat/ocr-cli-update
scope: ocr-cli-update-recovery
worktree: /mnt/work/projects/pdomain/.worktrees/ocr-cli-update
base_commit: "e564447b31d5683bf3f8aaf064df9848d8cf1da8"
supersedes: "2026-11-22-012950-ocr-cli-update-recovery.md"
handoff_reason: material_resume_change
host: codex
---

# Handoff: OCR CLI activation and rollback

## Goal

Finish update activation and offline rollback. Staging and the installed runtime probe
now pass. Activation still needs to coordinate with concurrent uv commands.

## Done

- CLI commit `e564447` fixes writable JSON staging and reuses decoded pixels for
  illustration crops. It adds an offline runtime import probe and points update
  notices to the cross-platform check command.
- Both installers can stage a verified wheel without calling `uv tool install`.
  They refuse an existing staging directory and publish the candidate record after
  copying the wheel. The Windows PowerShell 5.1 fixture verified a real wheel and
  confirmed that a bad digest leaves no stage.
- Linux CI passed with 693 tests and 16 slow-test skips. All 16 Linux real-model
  integration tests passed separately. Wheel smoke tests passed on Python 3.11,
  3.12, and 3.13.
  The original CI scratch directory on `/tmp` hit its quota. CI passed with
  `TMPDIR` on the uv cache filesystem under `/mnt/work`.
- Windows 11 build 26200 and Python 3.13.18 passed standalone JSON replacement,
  real OCR JSON, and illustration crops. The ASCII and Unicode crops matched byte
  for byte.
- Local pdomain-ops commit `8164fce` fixes Python 3.11 imports. With its local wheel,
  the CLI passed the runtime probe and real offline OCR on Windows Python 3.11.18.
  Local book-tools commit `7e7b37b` fixes Unicode contour paths. With its local
  wheel on Python 3.13.18, Unicode and ASCII paths returned four regions and identical text.
- The earlier disposable native Windows proof restored both launchers and the old
  environment offline. Test records remain in the Windows share.

Windows evidence is in the share under
/var/lib/omarchy/windows/mounts/users/1000/shared. The folders are
ocr-cli-fixes, ocr-cli-311, ocr-contour-fix, ocr-cli-prep, and ocr-recovery-native.
Each contains the corresponding proof logs and scripts. The VM was left running.
The Linux real-model test log is `ocr-cli-fixes/linux-integration.txt` in the same share.

## Not done and blockers

- The production updater still calls the original installer path. It needs to
  consume the staged candidate, verify the exact approved version, and restore the
  old install on failure. It also needs a durable record and standalone recovery.
- uv takes an exclusive lock on its tool directory before installing. With uv
  0.11.26 and disposable releases 1.0 and 2.0 on Linux, the candidate install waited
  while an external process held this lock. It installed after release of the lock.
  Holding the lock across a subprocess install therefore fails. Releasing it during
  activation lets another uv command install into the gap. A second disposable test
  installed 1.0 after the original environment and launchers were parked. The 2.0
  candidate then replaced that intervening install without `--force` or `--reinstall`.
- The dependency fixes are local. Published packages still need those fixes before
  the CLI can rely on them. Production interruption recovery, native PowerShell 7,
  CUDA, and long Windows model-cache paths remain unverified.

## Failed approaches and decisions

Keep candidate staging separate from live installation. Before activation consumes
a stage, validate its paths, recheck the digest, and flush the recovery record.
The installed probe uses `pdomain-ocr --check-runtime`. It imports the OCR runtime
without loading models or choosing a GPU. For Windows real-model checks, use a short
model-cache path. Set up isolated uv tool and bin directories for every test.

## Pointers

- `docs/plans/2026-11-21-cli-update-recovery.md`
- `docs/architecture/installation-and-updates.md`
- `pdomain_ocr_cli/_self_update.py`
- `install.sh`
- `install.ps1`
- `tests/test_cli_update.py`

## Resume steps

1. Resolve how the activation worker and external uv commands coordinate without
   allowing both to change the live installation. Prove the approach with the
   disposable packages before wiring it into the CLI.
2. Add durable activation and standalone recovery. Exercise interruption,
   candidate failure, and offline rollback on Linux and native Windows.
3. Activate a verified CLI wheel in an isolated install. Confirm the exact approved
   version and the runtime probe, then verify OCR with the supported dependency versions.
