---
kind: handoff
status: "active"
created: "2026-11-11"
created_at: "2026-11-11T03:22:38Z"
owner: "CT"
branch: "fix/spec-review-followups"
scope: "spec-review-followups"
worktree: "/mnt/work/projects/pdomain/.worktrees/ocr-cli-spec-review-followups"
base_commit: "edd59bd56eb197be10b79b0d039e8c95be487167"
supersedes: ""
handoff_reason: "user_requested"
host: "claude-code"
---

# Spec review follow-ups ready for review

## Goal

Do the fixes from the 2026-11-07 spec reviews, highest value first.

## Done

- Eight of nine follow-ups are done and a ninth is partly done, in ten commits.
- The default model is pinned to commit `8b7f9b31…`, the commit behind v0.7, and branch names now warn.
- The dependency bounds test parses requirements. Output transactions record backups before each rename and later runs clean up what a killed run left.
- Update-check failures report under `PD_OCR_DEBUG`, `install.sh` falls back to the REST API for digests, and `install.ps1` enables TLS 1.2.
- Rotated crops are tested on real pixels, a slow real-model word-preservation test was added, and decoded pixels per chunk are capped.
- `make ci AI=1` passed with 521 fast tests and `make ci-slow` with 537 tests at 100% coverage, on CPU with the GPU hidden.

## Not done

- On 2026-11-11 the batch rotation angle was blocked, because `pdomain-book-tools` 0.30.1 picked an angle and discarded it. As of 2026-11-13, version 0.31.0 returns one clockwise degree per page, `pdomain-ops` 0.12.2 stores it on the page, and this CLI reads `page.ocr_rotation_degrees`. The upright-buffer test remains. The CLI still must not infer the angle.
- `--normalize-output` stays deferred.
- The TLS 1.2 line ran only on PowerShell 7.6, not on a real Windows PowerShell 5.1 host.
- The readability editor did not run, because it rewrites whole files. Changed passages were written to the standard by hand.

## Failed approaches

- `make ci` failed at baseline with `Disk quota exceeded` on `/tmp`. It passed with `TMPDIR` on the work drive.

## Decisions

- The chunk limit is 400 million pixels, which is what the default `--batch-pages 4` could already hold at the per-image limit.
- Version-shaped names such as `v0.7` count as pinned, because tags and branches cannot be told apart offline.
- Cleanup removes superseded leftovers with a warning for each, and restores a backup only if the destination is missing.
- Open for the owner: the mode name, retiring the six specs, and where the suppression record lives.

## State

Worktree clean. Commit `4237dd4` went in after a CI run stopped at the end-of-file hook; the hook's fix is in that commit and the next full run passed. The owner paused this work on 2026-11-10 and the session's herdr tab is closed. Nothing was pushed, merged, tagged, released or deployed. All work ran on CPU with the GPU hidden. The session's last terminal output is saved in `/mnt/work/projects/pdomain/.artifacts/handoff-20261110/session-output/`. `/tmp` is a shared tmpfs that ran out of quota several times on 2026-11-10 while ten sessions ran gates. If a gate fails with a quota error, point `TMPDIR` at the work drive and rerun before suspecting the code.

## Pointers

- `docs/roadmap.md`
- `docs/context/intent-map.md`
- `docs/context/current-state.md`

## Resume steps

1. Review `git log master..HEAD`.
2. Check the 400 million pixel limit and the cleanup behaviour.
3. Merge when the owner asks.
