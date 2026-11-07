---
Status: implemented
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-07
Kind: spec
---

# Make every page output a recoverable transaction

A failed page write will restore every pre-existing artifact and remove every new artifact.

## Agent Index

- **Kind:** spec
- **Status:** implemented
- **Read when:** changing page artifact promotion or rollback
- **Search terms:** sidecar rollback, artifact transaction, former GH 22
- **Relates to:** shipped in commit `7af73fc` (v0.9.1); current behavior is [cli-orchestration.md](../architecture/cli-orchestration.md)

**Implementation plan:** retired after it shipped; see the 2026-11-07 tombstone in [decisions](../context/decisions.md).

## Adopted design

The transaction stages all new bytes before touching destinations. Before promotion, it moves each existing destination to a unique backup in the same directory. It then promotes sidecars and text. On any failure, it removes promoted new files and restores backups in reverse order.

Backups remain on the same filesystem so rename stays atomic. Cleanup failure is reported alongside the original error. The transaction never silently deletes an older artifact.

## Acceptance criteria

- A successful write leaves all requested artifacts and no temporary files.
- A failed final text promotion removes new sidecars.
- A failed overwrite restores old sidecars and old text exactly.
- A rollback failure preserves the original exception and reports affected paths.

## Adversarial Review

Reviewed on 2026-11-07 by one independent, read-only reviewer (Claude Sonnet)
against master `3297650`. The reviewer checked the design and its acceptance
criteria against the code and tests.

**Verdict:** Implemented with deviations. All four acceptance criteria hold for failures inside the running process.

- Medium: a crash, `SIGKILL` or power loss mid-commit leaves hidden `.bak` and `.stage` files, and the next run neither detects nor restores them. Documented in `cli-orchestration.md`. Follow-up.
- Medium: a failed backup rename leaves an empty reserved `.bak`, and an interrupt between the rename and the bookkeeping loses the old artifact to rollback. This breaks "never silently deletes an older artifact". Follow-up.
- Medium: `_discard_backups` swallows unlink errors, so a stale backup can remain unreported. Follow-up.
- Medium: rollback overwrites whatever is at the destination; concurrent runs on one output directory are not locked. Documented. Follow-up.
- Low: a second Ctrl-C aborts rollback; a dangling symlink destination is not backed up; replaced files lose their mode; stale sidecars from earlier runs survive. Follow-up.
