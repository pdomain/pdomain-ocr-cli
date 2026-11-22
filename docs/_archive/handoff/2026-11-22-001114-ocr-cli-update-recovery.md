---
kind: archive
status: retired
created_at: "2026-11-22T00:11:14Z"
owner: "agent:codex"
branch: "feat/ocr-cli-update"
scope: "ocr-cli-update-recovery"
worktree: "/mnt/work/projects/pdomain/.worktrees/ocr-cli-update"
base_commit: "083f68e16f529767c09449845eb1fd0dbc709d70"
handoff_reason: "user_requested"
host: "codex"
created: "2026-11-22"
last_verified: "2026-11-22"
---

# Handoff: OCR CLI update recovery

> **Retired — superseded by `docs/handoff/2026-11-22-012950-ocr-cli-update-recovery.md`.**

## Goal

Bring CLI update recovery in line with the Simple GUI. Verify the installed candidate before reporting success. Restore the old CLI offline if the candidate fails.

## Done

- The feature branch already has explicit CLI updates, optional automatic checks, installer model prefetch and skip flags, and revised user and architecture docs.
- Compared the GUI's staging, restart verification, and rollback with the CLI's installer handoff.
- Proved offline restoration of a disposable Linux uv installation after a missing candidate failed. The receipt pointed to a temporary wheel, so a rollback must preserve the live installation.
- Wrote the recovery implementation plan. No production recovery code was changed.

## Not done

Candidate startup failure after installation, partial activation, interruption recovery, and native Windows launcher replacement remain untested. The feature branch is local.

## Failed approaches and decisions

Do not assume the previous wheel remains at the path recorded by uv. The bootstrap installer deletes its temporary download. A parked backup also appeared as a malformed tool when stored directly under uv's tool directory. The proof backup was restored and removed from that directory. Park production backups on the same filesystem outside uv's discovery path. Restore the original absolute paths.

## Pointers

- `docs/plans/2026-11-21-cli-update-recovery.md`
- `docs/architecture/installation-and-updates.md`
- `pdomain_ocr_cli/_self_update.py`
- `install.sh`
- `install.ps1`
- `tests/test_cli_update.py`

## Resume steps

1. Open the feature worktree above, check its Git state, and read the plan.
2. Start with the real uv fixture and native Windows acceptance path. Prove parking and restoring the launcher at the original location before modifying the live updater.
3. Implement and test the plan in order. Keep the recovery worker usable without the CLI. Run full CI and report which Windows checks actually ran.
