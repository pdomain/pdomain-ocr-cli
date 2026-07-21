---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: spec
---

# Make every page output a recoverable transaction

A failed page write will restore every pre-existing artifact and remove every new artifact.

## Agent Index

- **Kind:** spec
- **Status:** active
- **Read when:** changing page artifact promotion or rollback
- **Search terms:** sidecar rollback, artifact transaction, former GH 22
- **Relates to:** [issue](../issues/2026-07-19-gh-22-sidecar-rollback-on-txt-failure.md)

**Implementation plan:** [output transaction plan](../plans/2026-07-21-output-transaction.md)

## Adopted design

The transaction stages all new bytes before touching destinations. Before promotion, it moves each existing destination to a unique backup in the same directory. It then promotes sidecars and text. On any failure, it removes promoted new files and restores backups in reverse order.

Backups remain on the same filesystem so rename stays atomic. Cleanup failure is reported alongside the original error. The transaction never silently deletes an older artifact.

## Acceptance criteria

- A successful write leaves all requested artifacts and no temporary files.
- A failed final text promotion removes new sidecars.
- A failed overwrite restores old sidecars and old text exactly.
- A rollback failure preserves the original exception and reports affected paths.
