---
Status: active
Owner: CT
Created: 2026-08-08
Last verified: 2026-08-08
Kind: issue
Level: I1
---

# Weekly dep-refresh branches and pull requests accumulate instead of landing

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-08-08
- **Resolution:** Open
- **Severity:** Medium — no data loss, but stray branches/PRs pile up weekly and
  obscure real signal
- **Affected version:** `.github/workflows/dep-refresh.yml` @ master (dated-branch
  pattern), repo setting `delete_branch_on_merge: false`
- **Read when:** touching `dep-refresh.yml`, branch protection, or triaging why
  old `dep-refresh/*` branches/PRs exist
- **Search terms:** dep-refresh, dated branch, stray branch, PR accumulation,
  auto-merge, delete_branch_on_merge, pre-commit-update, required status check ci
- **Relates to:** [issues README](README.md)

## Summary

`dep-refresh.yml` names a fresh branch per run
(`dep-refresh/$(date +%Y-%m-%d)-$GITHUB_RUN_ID`) and the repo has
`delete_branch_on_merge: false`, so nothing ever reclaims or deletes a run's
branch. As of 2026-08-08 origin carries 7 stray `dep-refresh/*` branches and 3
open pull requests (#58, #59, #60). The three open PRs are genuinely **red**
on content (every matrix leg fails on the same `pre-commit-update` defect),
so branch protection is correctly refusing to merge them as-is. But a bigger,
independent finding surfaced during the investigation: master protection's
required context `ci` has not been produced by any check since `ci.yml` was
turned into a Python-version matrix on 2026-05-29 (`1c3993c`) — proven by a
fully green, non-conflicting docs PR (#57) that still could not merge and had
to be closed by hand. Even a green `dep-refresh` PR could not currently
auto-land through this gate.

## Impact

- Stray branches and PRs accumulate weekly with no cleanup path; 7 branches
  and 3 open PRs exist today (started 2026-07-19).
- Each new red week adds another branch/PR instead of updating the existing
  one, so the noise grows unbounded until a human batch-closes it (as
  happened once already: PRs #53–#56 were closed unmerged on 2026-07-12).
- Real dependency-bump breakage (see Evidence §3) is masked by the pile-up
  rather than surfaced as one actionable PR.
- **Separately, and more severely:** since 2026-05-29 no pull request — not
  just `dep-refresh` — can merge through the standard (non-admin) path,
  because the required `ci` context is never satisfied. No PR has merged
  since #52 (2026-05-23), which predates the matrix change. This silently
  defeats branch protection's purpose (every recent merge would need an
  admin bypass) and independently blocks any future auto-land fix for
  `dep-refresh` even after the accumulation defect below is fixed.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-cli
branch: master
workflow: .github/workflows/dep-refresh.yml (cron Sun 02:00 UTC + workflow_dispatch)
repo setting: delete_branch_on_merge=false, allow_auto_merge=true
branch protection (master): required_status_checks.contexts=["ci"], strict=true
```

## Evidence

### 1. Seven stray branches, three open PRs

```text
$ gh api repos/pdomain/pdomain-ocr-cli/branches?per_page=100 --jq '.[].name'
dep-refresh/2026-06-21-27896575345
dep-refresh/2026-06-28-28313746351
dep-refresh/2026-07-05-28731618963
dep-refresh/2026-07-12-29181353687
dep-refresh/2026-07-19-29674885978
dep-refresh/2026-07-26-30189679142
dep-refresh/2026-08-02-30734316215
master
wip/salvage-investigate-4733780-uvlock

$ gh pr list --repo pdomain/pdomain-ocr-cli --state open
#60  chore: weekly dep refresh  dep-refresh/2026-08-02-30734316215  2026-08-02
#59  chore: weekly dep refresh  dep-refresh/2026-07-26-30189679142  2026-07-26
#58  chore: weekly dep refresh  dep-refresh/2026-07-19-29674885978  2026-07-19
```

Each branch corresponds to one week's run; nothing has cleaned up the four
older branches whose PRs (#53–#56) were already closed, or reused a slot for
the three that remain open.

### 2. All three open PRs are red on every required leg, not merely unmerged

```text
$ gh pr view 60 --repo pdomain/pdomain-ocr-cli --json mergeStateStatus,statusCheckRollup
mergeStateStatus: DIRTY (mergeable: CONFLICTING)
ci / Python 3.11  FAILURE
ci / Python 3.12  FAILURE
ci / Python 3.13  FAILURE
```

Same pattern, same three FAILUREs, on #58 and #59. This rules out "green PR
stuck for an unrelated reason" — auto-merge is correctly declining to land
three failing PRs.

### 3. Root cause of the failure: `pre-commit-update` self-modifies during CI

```text
$ gh run view 30734345338 --repo pdomain/pdomain-ocr-cli --log-failed
pre-commit-update.............................................................Failed
- hook id: pre-commit-update
- files were modified by this hook

✘ ruff-pre-commit - v0.15.22 -> v0.16.1
✘ markdownlint-cli2 - v0.23.1 -> v0.23.2
Changes detected and applied

make[1]: *** [Makefile:119: pre-commit-check] Error 1
make: *** [Makefile:192: ci] Error 2
```

The `pre-commit-update` hook bumps `.pre-commit-config.yaml` pins in place
during `make ci`'s `pre-commit-check` step, which then fails because the
working tree changed mid-run. #58 (2026-07-19) and #59 (2026-07-26) fail with
the identical `pre-commit-update ... Failed` / `files were modified by this
hook` signature, confirming this is a stable, reproducible defect in the
refresh content itself, not flakiness.

### 4. Branches are also stale/conflicting, independent of the CI failure

`mergeStateStatus: DIRTY` / `mergeable: CONFLICTING` on all three PRs — each
branch was cut from the `master` of its run week and has not been rebased
since, so it now conflicts with current `master` as well as failing CI. A
single reusable branch, force-pushed from a fresh `master` each run (per the
spec below), removes this staleness by construction.

### 5. The required `ci` context is structurally never produced (proven on a green PR)

`ci.yml`'s job id is `ci`, but since commit `1c3993c` (2026-05-29, "ci:
harden release and wheel verification") the job carries an explicit
`name: ci / Python ${{ matrix.python-version }}` across a 3-way matrix.
GitHub reports checks under that literal name, so the produced checks are
`ci / Python 3.11`, `ci / Python 3.12`, `ci / Python 3.13` — never a check
named plain `ci`:

```text
$ gh api repos/pdomain/pdomain-ocr-cli/commits/2c68efe.../check-runs --jq '.check_runs[].name'
ci / Python 3.11
ci / Python 3.12
ci / Python 3.13
```

Master protection requires exactly `contexts: ["ci"]`. PR #52 (merged
2026-05-23, before the matrix change) shows the mechanism used to work — its
one check was literally named `ci` and the PR merged normally. Since the
matrix change, **no PR has merged**: #52 and #4 (2026-05-11) are the only
merged PRs in the repo's history, and both predate `1c3993c`.

Direct proof this now blocks green PRs, not just red ones: PR #57 ("docs:
migrate and simplify governed documentation", opened/closed 2026-07-15) had
all three matrix legs `pass` and `mergeable: MERGEABLE` (no conflicts), yet:

```text
$ gh pr view 57 --repo pdomain/pdomain-ocr-cli --json mergeStateStatus,mergeable,state
mergeStateStatus: BLOCKED
mergeable: MERGEABLE
state: CLOSED
```

A fully green, non-conflicting PR was `BLOCKED` and had to be closed by hand
without merging. This is the same class of defect as Bug 1 in the linked
`pdomain-ui` spec (a required context that no check produces), independently
discovered here rather than assumed from that spec.

## Root-cause hypotheses

1. **(Confirmed) Dated branch naming + `delete_branch_on_merge: false` +
   no reuse logic** — `BRANCH="dep-refresh/$(date +%Y-%m-%d)-$GITHUB_RUN_ID"`
   guarantees a new branch every run; nothing deletes or reuses an old one,
   merged or not. This is the accumulation defect this report is about.
2. **(Confirmed, separate defect) The refresh content is genuinely broken**
   — `pre-commit-update` rewrites `.pre-commit-config.yaml` mid-run and
   `pre-commit-check` then fails on the resulting diff. This is why the
   three open PRs are red; it is not evidence against auto-merge, it is the
   thing auto-merge is correctly blocking.
3. **(Confirmed, more severe, out of this report's primary scope) The
   required `ci` context has not existed since 2026-05-29** — `ci.yml`'s
   matrix rename means no check is ever named plain `ci`. Proven independent
   of dep-refresh by PR #57. Fixing defects 1–2 alone would still leave
   `dep-refresh` (and every other PR) unable to auto-merge without an admin
   bypass.

## Defects to fix

1. **(Primary)** `dep-refresh.yml` creates a new branch name every run and
   never deletes or reuses one, so failed weeks accumulate branches and PRs
   indefinitely instead of collapsing into one open PR.
2. `pre-commit-update`'s self-modifying hook run breaks `make ci` inside the
   refresh PR itself, which is why the current three PRs are red (tracked
   here as context; fixing the branch-reuse defect does not require fixing
   this, since a red PR is expected to stay open for review either way).
3. **(Related, separately severe)** No check in `ci.yml` is named plain
   `ci`, so master protection's required context is permanently unsatisfied
   for every PR, not only `dep-refresh`'s. This should likely be filed and
   fixed as its own issue — mirroring the linked spec's Bug 1 fix
   (aggregation job) — since it blocks normal merges independent of
   dep-refresh and is outside this report's branch-accumulation scope.

## Next steps

1. **(Most disambiguating — do first)** File and fix the required-`ci`-context
   gap (Evidence §5 / Defect 3) so `ci.yml` reports a check literally named
   `ci` again — e.g. rename the matrix job id and add an aggregation job
   named `ci` that needs all matrix legs, the same shape as Bug 1's fix in
   the linked spec. Until this lands, no PR can merge without an admin
   bypass, so any auto-land fix to `dep-refresh.yml` alone cannot be
   verified end-to-end.
2. Apply the design in the `pdomain-ui` repo's spec at
   `docs/specs/2026-07-16-dep-refresh-auto-land-design.md` (section 3.B–3.C,
   read-only reference — a different repo, not edited here) to this repo's
   `dep-refresh.yml`: replace the dated branch with one
   reusable `dep-refresh` branch force-pushed from a fresh `master` each run;
   open a PR only when no open one already exists for that branch (check
   state, not mere existence); re-arm `gh pr merge --auto --rebase`; and set
   `delete_branch_on_merge: true` on the repo so a green auto-merge deletes
   the branch and the next run recreates it clean.
3. Separately, decide whether to fix the `pre-commit-update` self-modification
   (defect 2) so a week's refresh can actually go green, or accept that
   pre-commit-hook bumps will keep failing and should be dropped from the
   refresh scope. Out of scope for this report.
4. Once the above land, manually close the three current stray PRs (#58–#60)
   and delete their branches (and the four already-closed dated branches,
   #53–#56) as a one-time cleanup — the new workflow will not do this
   retroactively.

## What is NOT broken (to scope the fix)

- The workflow runs on schedule and produces correct dependency-update diffs
  (Actions SHA pins, `make upgrade-deps`, npm/pnpm updates) — the refresh
  logic itself, aside from the `pre-commit-update` self-modification noted
  above, is sound.
- `allow_auto_merge` is enabled and `gh pr merge --auto --rebase` is already
  armed in the workflow; auto-merge itself is wired correctly on the
  `dep-refresh` side — it simply has never had a PR that could clear branch
  protection to act on (Evidence §5).
- The refresh does not corrupt lockfiles or produce spurious diffs; the
  `pre-commit-update` failure (Evidence §3) is the only content defect found.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
