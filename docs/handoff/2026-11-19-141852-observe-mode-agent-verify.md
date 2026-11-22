---
kind: handoff
status: "active"
created: "2026-11-19"
created_at: "2026-11-19T14:18:52Z"
owner: agent:grok
branch: master
scope: agent-verify
worktree: /mnt/work/projects/pdomain/pdomain-ocr-cli
base_commit: "02258a04596ec09311b49fd6a5fe408e8dcdd91f"
supersedes: ""
handoff_reason: agent_switch
host: grok
---

# Handoff: observe-mode agent verify

## Goal

Keep the project hook on local `master` in observe mode, and make the tree match the agent-verify skills. Codex picks this up in the existing checkout. Enforce mode waits until the owner has read a would-block line.

## Done

- The skills are on disk, outside this repo. Claude loads the same directories through links in `/home/ntw/.claude/skills/`.
  - `/home/ntw/.agents/skills/installing-agent-verify/SKILL.md`
  - `/home/ntw/.agents/skills/authoring-agent-verify-profile/SKILL.md`
  - `/home/ntw/.agents/skills/writing-agent-verify-checker/SKILL.md`
  - `/home/ntw/.agents/skills/writing-agent-verify-checker/references/shell.md`
  - `/home/ntw/.agents/skills/registering-agent-verify-hooks/SKILL.md`
  - `/home/ntw/.agents/skills/proving-agent-verify/SKILL.md`
- `a17fec5` adds the observe-mode hook. `02258a0` teaches the checker the shell rules for `uv` and hook-path writes. Both are on `origin/master`.
- The same push fast-forwarded `7bd9aef` to `02258a0` and included `52e4da9` and `3058950`. The gx-yolo session `01a1eff9` pushed after the owner sent `a` in that session.
- `agent-verify.toml` has `mode = "observe"`, `base = "master"`, inner recipe `typecheck`, paths `pdomain_ocr_cli/`, and outer recipe `ci`. Stop does not run `ci`.
- The checker reads `agent_verify/check.py`, `agent-verify.toml`, and the justfile with `git show master:`. The justfile in the worktree was not rewritten.
- Claude and Grok share `.claude/settings.json`. Codex uses `.codex/hooks.json`. There is no project `.grok/hooks` copy.
- `/home/ntw/.local/state/agent-verify/pdomain-ocr-cli` does not exist. No would-block line has been written.
- A search of `/home/ntw/.codex/config.toml` and `/home/ntw/.codex/hooks.json` did not find `pdomain-ocr-cli`. The project hook hash is not recorded there.

## Not yet done

1. The owner proof in `proving-agent-verify` has not been run. Do not start it unless the owner asks in the pickup session. The steps are folder trust for a new Claude or Grok session, `/hooks` trust for `.codex/hooks.json`, one outside-`UV_PROJECT_ENVIRONMENT` deny per host, one worktree type error that appends a `Would-block` line, and the owner reading that log.
2. `mode` stays `observe` until that read. Do not commit `enforce`.
3. `references/shell.md` leaves these allowed: aliases, `source`, `declare`, process substitution, and a shell script file. Leave them allowed unless the owner asks to change that file first.
4. Stop stays on `typecheck` for `pdomain_ocr_cli/` only. A different inner recipe is a profile change the owner asks for. `ci`, `coverage`, `lint`, and `format` are the wrong Stop recipes.
5. The skills were not run through a pressure-test lab.

## Failed approaches

- `git show master:agent_verify/check.py | python3 -` drops the hook event. The hook command execs the source and keeps stdin.
- Unsetting `UV_PROJECT_ENVIRONMENT` for every command blocks the in-repo `.venv-container` path. Deny only an absolute path outside the git root, or a relative path that resolves outside it.
- A blanket `.claude/` gitignore drops `.claude/settings.json`. The ignore is `.claude/*` plus `!.claude/settings.json`.

## Key decisions

- The files on `master` decide. A worktree edit of the checker, the profile, or the justfile does not.
- `failClosed` is only on PreToolUse. Stop and SubagentStop have no matcher. The PreToolUse matcher is `Bash|Edit|Write|write|search_replace|apply_patch`.
- Test edits stay allowed. The inner path prefix does not include `tests/`.
- The checker stays out of the wheel. Its tests live in `tests/test_agent_verify_hook.py`.
- This gate is committed on the interactive checkout's `master`. Feature work still uses `/mnt/work/projects/pdomain/.worktrees/`.

## Current state

HEAD and `origin/master` are `02258a04596ec09311b49fd6a5fe408e8dcdd91f`. The branch was clean when this handoff was written. Re-check `git status -sb` before editing. A live Codex session is already in this checkout: Herdr workspace `w9J`, tab `w9J:t1`, pane `w9J:p1`, title `Resume Grok's work`. Do not start a second session. Do not close that pane.

The skills are the contract. This file does not restate them.

## Pointers

- `agent-verify.toml`
- `agent_verify/check.py`
- `tests/test_agent_verify_hook.py`
- `.claude/settings.json`
- `.codex/hooks.json`
- `/home/ntw/.agents/skills/installing-agent-verify/SKILL.md`
- `/home/ntw/.agents/skills/authoring-agent-verify-profile/SKILL.md`
- `/home/ntw/.agents/skills/writing-agent-verify-checker/SKILL.md`
- `/home/ntw/.agents/skills/writing-agent-verify-checker/references/shell.md`
- `/home/ntw/.agents/skills/registering-agent-verify-hooks/SKILL.md`
- `/home/ntw/.agents/skills/proving-agent-verify/SKILL.md`

## Resume steps

1. Read this file, then the six skill paths above. `references/shell.md` is the only home for the shell rules.
2. Confirm HEAD is `02258a04596ec09311b49fd6a5fe408e8dcdd91f` and read `git status -sb`. If the live pane has already edited files, inspect that diff before changing anything.
3. Compare `agent-verify.toml`, `agent_verify/check.py`, `tests/test_agent_verify_hook.py`, `.claude/settings.json`, and `.codex/hooks.json` with the skills. Change a file only where it disagrees.
4. If you change code, run `AI=1 just ci` from this repo. Commit on local `master` only after that passes. Do not push unless the owner asks. Do not amend `02258a0` or the commits under it.
5. Leave `mode` at `observe`. Leave the justfile unchanged. Leave the named shell limits allowed. Do not run the owner proof.
6. Report whether the tree matches, and any commit you made.
