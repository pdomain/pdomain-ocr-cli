---
Status: active
Owner: CT
Created: 2026-05-14
Last verified: 2026-11-07
Kind: process
---

# CLAUDE — pdomain-ocr-cli

This CLI tool turns scanned book pages into clean `.txt` files. It wraps
`pdomain-book-tools` OCR/layout primitives with auto-rotation, layout-aware
reading-order reconstruction, and a user-facing `pdomain-ocr` command.

## Commands

| recipe | does |
|---|---|
| `AI=1 just setup` | dev venv + pre-commit hooks (exact `pdomain-book-tools` pin from `pdomain-index-pip`) |
| `just local-setup` | clone any missing sibling pd-* repos into the workspace |
| `just local-dev` | switch to local-dev mode (editable `../pdomain-book-tools` + marker) |
| `just local-check` | print local-dev mode + per-sibling resolution |
| `just local-upgrade-deps` | upgrade deps then restore editable siblings (local-mode only) |
| `just local-install` / `just local-uninstall` | `uv tool install` with editable siblings / uninstall |
| `just local-run` | broken: `scripts/local-run.sh` calls `just run`, which the justfile lacks |
| `just local-test` | run fast test suite against editable local-dev siblings (local-mode only) |
| `just local-test-slow` | run full test suite incl. slow integration tests against editable local-dev siblings (local-mode only) |
| `just update-pdomain-deps` | bump `>=` pins of pd-* sibling deps to `pdomain-index-pip` latest; leaves diff for review |
| `AI=1 just test` | fast suite (`uv run pytest -n auto`; skips `@pytest.mark.slow`) |
| `AI=1 just test-slow` | full suite incl. real-model integration tests |
| `AI=1 just lint` / `AI=1 just format` | ruff |
| `AI=1 just build` | sdist + wheel into `dist/` |
| `AI=1 just ci` | setup → pre-commit → lint-check → typecheck → coverage → installer-test → build → wheel-smoke → docgraph strict |
| `just upgrade-pdomain-book-tools` | deprecated alias for `just update-pdomain-deps` |
| `just release-{patch,minor,major}` | run the `just ci-slow` preflight, create and push the tag, then build and create the GitHub Release locally |
| `just refresh-version` | re-derive `pdomain-ocr --version` after tag changes (hatch-vcs) |

`AI=1` captures full output to `.ci-ai.log` and prints one `PASS:` line.
On failure, it prints a `FAIL:` line and filtered failure sections. Omit
`AI=1` to see the full output directly.

See the workspace-level `docs/process/local-dev.md` for the canonical
local-dev pattern (spec #362).

Legacy recipes `dev-local`, `install-local`, `uninstall-local`,
`check-local-editable`, `run-local`, and `upgrade-deps-local` still work; the
repo keeps them as deprecation aliases.

Full recipe list: `just --list`. Full dev setup: [`DEVELOPMENT.md`](DEVELOPMENT.md).

## Rules

- Always run `AI=1 just ci` before committing.
- Use just recipes first; fall back to `uv run …` only when no recipe exists.
- Never `python -m pytest`. Always `uv run pytest -n auto` or `just test`. Bare `python`/`python3`/`.venv/bin/python` miss the venv.
- Never silently drop OCR words. Reorg, caption suppression, and all output paths must preserve every word — roles may change, words may not disappear.
- `--no-illustration-placeholders` suppresses the placeholder block, not caption text. Caption words must survive in the output.
- `pdomain-book-tools` is upstream for OCR/layout/image primitives. Coordinate with that agent before adding logic that belongs in the library.
- `pdomain-book-tools` is pinned exactly (`==`) in `pyproject.toml`, in both `dependencies` and the `gpu` extra. `just update-pdomain-deps` rewrites only `>=` pins, so bump this pin by hand, then run `uv lock`.
- `hatch-vcs` derives the version from git tags, so `pyproject.toml` carries no hardcoded version.

## Sibling repos

- `../pdomain-book-tools/` — upstream dependency. Side-by-side editing: `just local-setup` + `just local-dev`.

## Docs

- [`DEVELOPMENT.md`](DEVELOPMENT.md) — dev setup, just recipes, release steps.
- [`docs/roadmap.md`](docs/roadmap.md) — open priorities, now/next/later.
- [`docs/architecture/layout-aware-ocr.md`](docs/architecture/layout-aware-ocr.md) — layout-aware OCR behavior.
- [`docs/usage/cli-usage.md`](docs/usage/cli-usage.md) — end-user usage reference.

## Issues

Work is tracked as Markdown files in `docs/issues/`. The open list is
[`docs/issues/README.md`](docs/issues/README.md). Items that cut across several
`pdomain-*` repos are filed in
`/mnt/work/projects/pdomain/pdomain-book-tools/docs/issues/`. GitHub Issues is
still enabled on `pdomain/pdomain-ocr-cli`, but the remote tracker is kept
empty. `ConcaveTrillion/ocr-container-meta` was the tracker for the old
`/workspaces/ocr-container` workspace. Its last push was 2026-06-06, and it is
no longer used.

## docs/ folder

This repo follows the workspace docs/ template — see [`docs/README.md`](docs/README.md). Active
folders: `architecture/`, `context/`, `conventions/`, `decisions/`, `issues/`,
`plans/`, `process/`, `research/`, `runbooks/`, `specs/`, `templates/`, and
`usage/`.

**Superpowers redirect.** This repo has no `docs/superpowers/` subdirectory.
So when a superpowers skill (e.g. `brainstorming`, `writing-plans`) tells you
to save to `docs/superpowers/specs/<file>.md` or
`docs/superpowers/plans/<file>.md`, save instead to `docs/specs/<file>.md` or
`docs/plans/<file>.md`.

<!-- workspace-process:start -->

## Before coding

These steps are workspace defaults for any coding task. **User-level settings
override them** — a user's own `~/.claude/CLAUDE.md`, `settings.json`, or a
direct instruction in the conversation takes precedence and may waive or
change any step below.

### Working principles

- **Use skills.** Invoke the relevant superpowers skill before starting —
  process skills first (`brainstorming`, `systematic-debugging`,
  `writing-plans`, `test-driven-development`), then implementation skills.
  If a skill applies, using it is not optional.
- **Write clearly.** Route new reader-facing documents through
  `writing-docs:write-readably` and existing prose through
  `writing-docs:edit-for-readability`.
- **Delegate by default.** Dispatch subagents for non-trivial work: per-repo
  agents for repo changes, `Explore` for code searches. This keeps large tool
  output out of the parent context.
- **Parallelize.** Run independent tasks as concurrent subagents — multiple
  agent calls in a single message. Set `model: sonnet` on implementers and
  reviewers.

### Steps

1. **Check the working tree.** `git status --short`. Surface or resolve stray
   uncommitted work before starting — don't build on it.
2. **Read repo guidance.** This repo's `CLAUDE.md` and `CONVENTIONS.md` for
   repo-specific rules.
3. **Consult `docs/` for authoritative context** (whichever folders exist):
   `plans/` (the work plan), `specs/` (design specs — follow any `Spec:`
   pointer from the issue), `research/` (prior investigations), `decisions/`
   (ADRs / constraints), `architecture/` (shipped design).
4. **Check the issue's status.** Open its file under `docs/issues/`, or under
   `pdomain-book-tools/docs/issues/` for cross-repo work, and confirm it is
   still open.
5. **Check for in-flight work.** Open PRs and existing branches touching the
   same area, to avoid colliding with work-in-progress.
6. **Consult agent memory.** `.claude/agent-memory/<repo>/feedback_*.md` for
   corrections not yet promoted to `CONVENTIONS.md`.
7. **Locate code with `Explore` first.** Use an `Explore` subagent to find
   relevant files before broad `Read`/grep.
8. **Isolate in a worktree.** Never work directly in the interactive checkout
   at `/mnt/work/projects/pdomain/pdomain-ocr-cli/`; put worktrees under
   `/mnt/work/projects/pdomain/.worktrees/`. Use the `using-git-worktrees` skill
   to set up an isolated worktree. When delegating to a full-power
   implementation agent, pass `isolation: "worktree"` on the `Agent` call
   (skip for `-docs` agents and the `driver` agent). When an agent returns a
   worktree path + branch, use the `finishing-a-development-branch` skill to
   decide how to integrate.
9. **TDD.** Write the failing test first where the plan calls for it.
10. **Verify before committing.** Focused verification plus `just ci`.
11. **Commit locally; do not push** without explicit say-so.

<!-- workspace-process:end -->

<!-- >>> repo-setup:repo-facts sha256:ed76e7614a8ab4a4bfb95ff198150a61690491d8a7819d13e484da353427bf18 -->
## Repository facts

This Python 3.11-3.13 CLI turns scanned book pages into clean text. The
`pdomain-ocr` entry point calls `pdomain_ocr_cli.ocr_to_txt:main`. Application
code lives in `pdomain_ocr_cli/`; tests and fixtures live in `tests/`; project
and user documentation lives in `docs/`. The CLI builds on the pinned
`pdomain-book-tools` dependency for OCR, layout, and image primitives.
<!-- <<< repo-setup:repo-facts -->

<!-- >>> repo-setup:commands-and-gates sha256:dbc3cc6d8244e588879fefa67d31d3fc00e33cf2524f6f482279daf7476c7abe -->
## Commands and gates

Use the repository's `uv` environment for Python tools:

- `uv run pytest` runs tests.
- `uv run ruff check` runs lint checks.
- `uv run ruff format` formats Python.
- `uv run basedpyright` runs static type checks.
- `just test` runs the repository test recipe.
- `just lint` runs the repository lint recipe.
<!-- <<< repo-setup:commands-and-gates -->

<!-- >>> repo-setup:writing-and-review sha256:611871197ede37b1dba3159b2b1c005c88bbe7c69debc375d9381cc9d99ce399 -->
## Writing and review

Route new durable reader-facing documents through the
`writing-docs:write-readably` skill. Route prose edits through
`writing-docs:edit-for-readability`. Follow the consuming plugin's policy when
using `adversarial-review:adversarial-review`. For Python changes, follow the
`writing-python:writing-python` skill and its mandatory gate.
<!-- <<< repo-setup:writing-and-review -->
