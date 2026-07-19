---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-19
Kind: architecture
Supersedes:
  - docs/specs/2026-05-28-test-suite-reorganization-design.md
  - docs/plans/2026-05-28-test-suite-reorganization.md
---

# Test-suite architecture

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing tests, coverage policy, OCR test doubles, installer tests, PowerShell setup, or fast and slow CI gates.
- **Search terms:** test suite, pytest, coverage, FakePage, shared fixtures, slow integration, real OCR, pwsh, installer contract, word preservation.

## Suite structure

The test suite separates fast, deterministic checks from slow, model-backed
integration tests. The fast suite covers CLI behavior, policy, output planning,
artifact safety, warnings, model resolution, installers, and workflow contracts.
It uses controlled fakes in place of heavy OCR and layout dependencies. It still
exercises real CLI orchestration and output-writing paths.

Tests marked `slow` use real OCR and layout models, download pinned model assets
when necessary, and validate recognized text and default-layout behavior. The
fast suite does not claim to validate model inference.

Shared scaffolding lives in `tests/_fakes.py` and `tests/conftest.py`. Slow
integration tests retain a local invocation helper because their real-model
lifecycle differs from the mocked fast path.

## Shared fixtures and fakes

`tests/conftest.py` provides the common CLI harness, dependency replacements,
and repeatable image inputs. `tests/_fakes.py` provides shared document, page,
word, snapshot, array, and argument stand-ins.

`FakePage` records `reorganize_page` calls. It deterministically recomposes output
from seeded body text, layout words, illustration placeholders, and captions.
Fast tests therefore assert written text instead of relying only on mock call
arguments. These fakes validate CLI wiring and output contracts. They do not
replace slow tests of production OCR and reorganization.

## Fast and slow gates

The fast gate runs the default pytest suite without tests marked `slow`. The
slow gate adds model-backed integration tests for real OCR and default layout.

Both paths use branch coverage, with `fail_under=100` for production code.
Reachable behavior receives a test. Coverage exclusions are limited to
genuinely unexecutable code and require a short reason.

## PowerShell and installer coverage

PowerShell is a required test dependency. `scripts/ensure-pwsh.sh` provisions
it through repository setup; missing `pwsh` is a setup failure, not a reason to
skip installer tests.

`tests/test_install_ps1_cuda.py` invokes the real CUDA-detection helpers.
`tests/test_install_ps1.py` exercises the top-level `install.ps1` contract,
including piped invocation and package-index behavior.

## Word preservation

Tests enforce the no-silent-word-drop invariant for CLI wiring paths. Caption
handling, illustration-placeholder suppression, and reorganization with
controlled fakes preserve OCR words. A word may move or receive a role label,
but it must not disappear silently. `--no-illustration-placeholders` suppresses
only the placeholder; caption text remains.

**Coverage gap (roadmap former GH #41):** fast word-preservation cases often
force `--layout-model none` or use `FakePage`. Slow default-layout tests prove
the path runs, but do not yet assert a multiset “every OCR word preserved”
oracle under default layout reorganization.

## Implementation deviations

The implementation took five different directions from the original design:

- Commit `cf36030` expanded scope into production code by reporting corrupt
  inputs per image instead of aborting a batch.
- Commit `d887fc0` centralized PowerShell provisioning in
  `scripts/ensure-pwsh.sh` through `make setup`, instead of separate CI and
  devcontainer changes.
- The fast content oracle uses deterministic `FakePage` recomposition. Real
  recognized text remains the slow suite's responsibility.
- Splitting `test_main_mocked.py` improved behavioral grouping but left two
  large successor modules, so the file-size goal was only partly achieved.
- The slow integration suite retained its local invocation helper because its
  real-model lifecycle differs from the mocked fixture.

## Evidence

Verified against the repository on 2026-07-13.

- Code and configuration: `tests/_fakes.py`, `tests/conftest.py`, `Makefile`,
  and `pyproject.toml`.
- Fast behavior: `tests/test_main_flag_wiring.py` and
  `tests/test_main_happy.py`.
- Slow behavior: `tests/test_pipeline_integration.py`.
- Installer contracts: `tests/test_install_ps1_cuda.py` and
  `tests/test_install_ps1.py`.
- History: commits `24c889f`, `8f4b7e8`, `6823f1e`, `47e8653`, `cf36030`,
  and `d887fc0`.
