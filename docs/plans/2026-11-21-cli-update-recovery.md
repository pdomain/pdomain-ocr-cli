---
Status: draft
Owner: CT
Created: 2026-11-21
Last verified: 2026-11-21
Kind: plan
---

# OCR CLI update recovery implementation plan

> **For agentic workers:** Use the Superpowers executing-plans or subagent-driven-development skill. Complete the checks in order.

## Goal

An update succeeds only after the installed launcher reports the approved version and loads the OCR runtime. A failed update restores the previous installation offline. A separate recovery command remains usable if the launcher is broken.

Keep the existing uv tool installation and the current confirmation, release integrity, platform, and model-cache behavior. Use the GUI as the reference for preflight, activation, health verification, and rollback. See [installation and updates](../architecture/installation-and-updates.md) for the current CLI flow.

## Architecture

The GUI stages a candidate and verifies the restarted app before accepting it. The current CLI calls a bundled installer and defers replacement on Windows until its launcher and Python process exit.

A disposable Linux uv install reported `99.9.1` before and after an intentional candidate-install failure. Restoring the old environment and launcher to their original paths worked offline. The uv receipt referred to an installer temporary wheel that no longer existed. An exact restore should use the old environment and launcher, since reinstalling the old wheel may require dependencies or network access. The proof covered a failure before a candidate was installed. It did not cover a partial install, interruption, or Windows locks.

Stage the verified wheel and preferably resolve its dependencies without touching the live paths. Run the destructive portion in a recovery worker outside the tool environment. On Windows, wait for both the initiating CLI process and its launcher. Keep the backup of each item on its original filesystem. Park it outside uv's tool discovery paths and restore it to the same absolute path. A venv or launcher can contain absolute paths, so the backup stays parked until restoration.

## Tech Stack

Python, uv, POSIX shell, Windows PowerShell, and pytest.

## Global Constraints

Make the phase record durable before each rename. Flush the record and its parent directory, then flush the affected directories after the rename. Use the platform equivalent on Windows. If durability cannot be established on a platform or filesystem, state that limit and refuse destructive activation there.

Keep the work directory private and validate recorded paths before acting on them. Lock the update and recovery together for the same tool installation. Refuse unsupported layouts before moving files. If another process or an external uv command may still be using the install, fail safely. Do not delete the last known-good backup until the replacement has passed verification and the success record is durable.

## Implementation tasks

1. **Prove filesystem and launcher behavior.**
   - [ ] Add a disposable package fixture with two versions and use real uv with isolated `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR`. Read the receipt and identify every launcher owned by this distribution. Confirm the environment and launchers can be parked, replaced, and restored without altering another tool.
   - [ ] Exercise the same sequence on native Windows. Include an active launcher, staged PowerShell worker, paths with spaces, and case-insensitive paths. Treat Linux PowerShell tests as partial evidence.
2. **Separate release preparation from replacement.**
   - [ ] Update `install.sh`, `install.ps1`, and their contract tests to let the updater prepare a verified local wheel before altering the current installation. Preserve standalone installer behavior, the approved tag guard, wheel verification, Python selection, and CUDA selection.
   - [ ] Hand off the selected wheel and install settings without doing a second mutable release lookup after parking the old install. A download, digest, or selection failure must leave the old launcher usable.
3. **Implement the transaction and recovery.**
   - [ ] Add a small recovery worker and a persistent phase record. Wire the launch and status reporting through `pdomain_ocr_cli/_self_update.py`. Ship the worker outside the replaceable environment before activation. It must remain runnable with the system shell or PowerShell if the CLI is missing.
   - [ ] Test failure after parking each item, partial candidate installation, process interruption, a second update, repeated recovery, and an unsuccessful restore. Verify interrupted phases recover without deleting unrelated files. Record the external recovery command and the backup location when intervention is required.
4. **Verify the candidate before accepting it.**
   - [ ] Invoke the installed launcher by absolute path. Check the exact approved version and exercise an offline OCR runtime import that does not load models or use a GPU. Treat timeout or wrong output as failure.
   - [ ] Restore the old environment and launchers on install or health-check failure. Verify the restored version before recording rollback. Persist the final state as `updated`, `rolled back`, or `recovery needed`. On Windows the initiating exit code still reports handoff, with the worker recording the final outcome.
5. **Prove the complete update flow.**
   - [ ] Cover successful update, bad candidate startup, rollback without network, interruption, and native Windows launcher replacement. Reuse `tests/test_cli_update.py` and installer tests. Add focused worker tests for state transitions and recovery safety.
   - [ ] Document how users see the result and recover a broken launcher. Put implementation details in architecture. Run `AI=1 just ci` and verify a built wheel in an isolated tool installation before committing.

No release or push is part of this plan.
