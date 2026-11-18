"""Tests for the project verification hook.

``just test`` collects this file. It does not import ``pdomain_ocr_cli``,
so the package coverage floor is unchanged.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

from agent_verify import check
from agent_verify.check import handle

if TYPE_CHECKING:
    from collections.abc import Mapping

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}
_ENGINE_VENV = "/home/ntw/.local/share/series-engine-venv"


def _hook_command(repo_root: Path) -> str:
    settings = json.loads((repo_root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    command = hooks["Stop"][0]["hooks"][0]["command"]
    if not isinstance(command, str):
        message = "Stop hook command is missing"
        raise TypeError(message)
    return command


class CheckTests(unittest.TestCase):
    """Events against a temporary master branch."""

    def setUp(self) -> None:
        """Create a scratch home and a scratch repo root."""
        self.scratch = Path(tempfile.mkdtemp(prefix="agent-verify-"))
        (self.scratch / ".nobackup").touch()
        self.home = self.scratch / "home"
        self.home.mkdir()
        self.repo = self.scratch / "repo"
        self.repo.mkdir()

    def tearDown(self) -> None:
        """Remove the scratch directory."""
        shutil.rmtree(self.scratch, ignore_errors=True)

    def test_claude_denies_uv_when_the_venv_is_outside_the_repo(self) -> None:
        """A Claude Bash event with the engine venv exits 2 and names the variable."""
        self._commit_profile()
        code, out, err = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="uv run pytest tests/ -q",
            ),
            {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV},
        )
        assert code == 2
        assert "permissionDecision" in out
        assert "deny" in out
        assert "UV_PROJECT_ENVIRONMENT" in out
        assert "UV_PROJECT_ENVIRONMENT" in err
        assert "continue" not in out

    def test_grok_and_codex_shapes_deny_the_same_command(self) -> None:
        """Grok camelCase and Codex snake_case both deny the outside venv."""
        self._commit_profile()
        grok = {
            "hookEventName": "pre_tool_use",
            "hook_event_name": "PreToolUse",
            "sessionId": "grok-session",
            "cwd": str(self.repo),
            "toolName": "run_terminal_command",
            "toolInput": {"command": "uv run pytest tests/ -q"},
        }
        codex = {
            "hook_event_name": "PreToolUse",
            "session_id": "codex-session",
            "cwd": str(self.repo),
            "tool_name": "Bash",
            "tool_input": {"command": "uv run pytest tests/ -q"},
        }
        for event in (grok, codex):
            code, out, _err = self._run(event, {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV})
            assert code == 2
            assert "UV_PROJECT_ENVIRONMENT" in out

    def test_relative_venv_and_inside_venv_and_a_clean_command_are_allowed(self) -> None:
        """A relative venv, an in-repo venv, and git status are not denied."""
        self._commit_profile()
        relative = self._run(
            self._event("PreToolUse", tool_name="Bash", command="uv run pytest tests/ -q"),
            {"UV_PROJECT_ENVIRONMENT": ".venv-container"},
        )
        assert relative[0] == 0
        assert relative[1] == ""
        inside = str(self.repo / ".venv")
        allowed = self._run(
            self._event("PreToolUse", tool_name="Bash", command="just typecheck"),
            {"UV_PROJECT_ENVIRONMENT": inside},
        )
        assert allowed[0] == 0
        clean = self._run(
            self._event("PreToolUse", tool_name="Bash", command="git status"),
            {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV},
        )
        assert clean[0] == 0
        assert clean[1] == ""

    def test_a_relative_path_that_leaves_the_repo_is_denied(self) -> None:
        """A relative UV_PROJECT_ENVIRONMENT that resolves outside the repo is denied."""
        self._commit_profile()
        code, out, _err = self._run(
            self._event("PreToolUse", tool_name="Bash", command="uv run pytest tests/ -q"),
            {"UV_PROJECT_ENVIRONMENT": "../series-engine-venv"},
        )
        assert code == 2
        assert "UV_PROJECT_ENVIRONMENT" in out

    def test_a_later_assignment_and_a_command_prefix_still_see_uv(self) -> None:
        """A prefix or an assignment after env -u does not hide uv."""
        self._commit_profile()
        prefixed = self._run(
            self._event("PreToolUse", tool_name="Bash", command="command uv run pytest tests/ -q"),
            {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV},
        )
        assert prefixed[0] == 2
        later = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command=(
                    "env -u UV_PROJECT_ENVIRONMENT "
                    f"UV_PROJECT_ENVIRONMENT={_ENGINE_VENV} uv run pytest tests/ -q"
                ),
            )
        )
        assert later[0] == 2
        assert "UV_PROJECT_ENVIRONMENT" in later[1]

    def test_wrapper_flags_and_shell_expansion_still_see_uv(self) -> None:
        """Options, ``--``, and an unexpanded ``$`` do not hide uv or just."""
        self._commit_profile()
        commands = (
            "command -p uv run pytest tests/ -q",
            "time -p uv run pytest tests/ -q",
            "nice -n10 uv run pytest tests/ -q",
            "env -C /tmp uv run pytest tests/ -q",
            "nohup -- uv run pytest tests/ -q",
            "exec -a uvname uv run pytest tests/ -q",
            "UV_PROJECT_ENVIRONMENT=$UV_PROJECT_ENVIRONMENT uv run pytest tests/ -q",
            f"env -i UV_PROJECT_ENVIRONMENT={_ENGINE_VENV} uv run pytest tests/ -q",
        )
        for command in commands:
            code, out, _err = self._run(
                self._event("PreToolUse", tool_name="Bash", command=command),
                {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV},
            )
            assert code == 2, command
            assert "UV_PROJECT_ENVIRONMENT" in out

        cleared = self._run(
            self._event("PreToolUse", tool_name="Bash", command="env -i uv run pytest tests/ -q"),
            {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV},
        )
        assert cleared[0] == 0
        assert cleared[1] == ""

    def test_shell_forms_that_still_run_uv_are_denied(self) -> None:
        """Append, export, env -S, timeout, and bash -c do not hide uv."""
        self._commit_profile()
        denied = (
            "UV_PROJECT_ENVIRONMENT+= uv run pytest tests/ -q",
            f"export UV_PROJECT_ENVIRONMENT={_ENGINE_VENV}; uv run pytest tests/ -q",
            f"export UV_PROJECT_ENVIRONMENT={_ENGINE_VENV} && uv run pytest tests/ -q",
            "env -a name uv run pytest tests/ -q",
            "env -S 'uv run pytest tests/ -q'",
            "timeout 5 uv run pytest tests/ -q",
            "bash -c 'uv run pytest tests/ -q'",
            "echo $(uv run pytest tests/ -q)",
            f"UV_PROJECT_ENVIRONMENT={_ENGINE_VENV}+=x uv run pytest tests/ -q",
            f"export UV_PROJECT_ENVIRONMENT={_ENGINE_VENV}+=x; uv run pytest tests/ -q",
            "timeout -- 5 uv run pytest tests/ -q",
            "true & uv run pytest tests/ -q",
        )
        for command in denied:
            code, out, _err = self._run(
                self._event("PreToolUse", tool_name="Bash", command=command),
                {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV},
            )
            assert code == 2, command
            assert "UV_PROJECT_ENVIRONMENT" in out

        bare = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command=f"UV_PROJECT_ENVIRONMENT={_ENGINE_VENV}; uv run pytest tests/ -q",
            )
        )
        assert bare[0] == 0
        assert bare[1] == ""
        allowed = (
            "unset UV_PROJECT_ENVIRONMENT; uv run pytest tests/ -q",
            "env - uv run pytest tests/ -q",
            "env -iC/tmp uv run pytest tests/ -q",
            "env -i \\\nuv run pytest tests/ -q",
        )
        for command in allowed:
            code, out, _err = self._run(
                self._event("PreToolUse", tool_name="Bash", command=command),
                {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV},
            )
            assert code == 0, command
            assert out == ""

    def test_a_normalized_hook_path_is_denied(self) -> None:
        """A relative path with .. still matches the hook file."""
        self._commit_profile()
        code, out, _err = self._run(
            self._event(
                "PreToolUse",
                tool_name="Edit",
                file_path="pdomain_ocr_cli/../.claude/settings.json",
            )
        )
        assert code == 2
        assert "master" in out

    def test_a_failed_git_diff_does_not_skip_the_stop_check(self) -> None:
        """Stop blocks when git cannot list the changed files."""
        self._commit_profile()
        index = self.repo / ".git" / "index"
        index.chmod(0)
        try:
            code, _out, err = self._run(self._stop_event())
        finally:
            index.chmod(0o644)
        assert code == 2
        assert "git could not" in err

    def test_env_unset_before_uv_is_allowed(self) -> None:
        """A command that unsets the variable before uv is not the engine-venv case."""
        self._commit_profile()
        code, out, _err = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="env -u UV_PROJECT_ENVIRONMENT uv run pytest tests/ -q",
            ),
            {"UV_PROJECT_ENVIRONMENT": _ENGINE_VENV},
        )
        assert code == 0
        assert out == ""

    def test_hook_file_edits_are_denied_and_reads_are_allowed(self) -> None:
        """Edit and shell writes to the hook files are denied. git show is allowed."""
        self._commit_profile()
        edit = self._run(
            self._event(
                "PreToolUse",
                tool_name="Edit",
                file_path=".claude/settings.json",
            )
        )
        assert edit[0] == 2
        assert "master" in edit[1]
        remove = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="rm .claude/settings.json",
            )
        )
        assert remove[0] == 2
        show = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="git show master:.claude/settings.json",
            )
        )
        assert show[0] == 0
        redirected = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="cat /etc/hostname > .claude/settings.json",
            )
        )
        assert redirected[0] == 2
        glued = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="cat /etc/hostname >.claude/settings.json",
            )
        )
        assert glued[0] == 2
        compared = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="rg '>=' .claude/settings.json",
            )
        )
        assert compared[0] == 0
        assert compared[1] == ""
        duplicated = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="cat .claude/settings.json 2>&1",
            )
        )
        assert duplicated[0] == 0
        forced = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="cat x >|.claude/settings.json",
            )
        )
        assert forced[0] == 2
        assert "master" in forced[1]
        glued_word = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="cat /etc/hostname>.claude/settings.json",
            )
        )
        assert glued_word[0] == 2
        background = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="cat /etc/hostname>.claude/settings.json&",
            )
        )
        assert background[0] == 2
        quoted = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="rg '>.claude/settings.json' .",
            )
        )
        assert quoted[0] == 0
        assert quoted[1] == ""
        dd = self._run(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="dd of=.claude/settings.json",
            )
        )
        assert dd[0] == 2
        assert "master" in dd[1]

    def test_non_utf8_git_names_do_not_skip_the_stop_check(self) -> None:
        """Stop fails closed when git prints a name that is not UTF-8."""
        self._commit_profile()
        self._dirty_package()
        original = check._git

        def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
            if args and args[0] in {"diff", "ls-files"}:
                return subprocess.CompletedProcess(args, 0, stdout=b"\xff", stderr=b"")
            return original(cwd, *args)

        check._git = _git
        try:
            code, out, err = self._run(self._stop_event())
        finally:
            check._git = original
        assert code == 2
        assert out == ""
        assert "UTF-8" in err

    def test_observe_logs_a_failing_master_recipe_and_ignores_the_worktree_justfile(self) -> None:
        """Master's typecheck exits 1. A worktree recipe of true does not replace it."""
        self._commit_profile(recipe_body="exit 1")
        justfile = self.repo / "justfile"
        justfile.write_text(_justfile("exit 0"), encoding="utf-8")
        self._dirty_package()
        code, out, _err = self._run(self._stop_event())
        assert code == 0
        assert out == ""
        log = (self.home / ".local/state/agent-verify/pdomain-ocr-cli/would-block.log").read_text(
            encoding="utf-8"
        )
        assert "Would-block" in log

    def test_enforce_blocks_then_stops_on_the_third_failure(self) -> None:
        """The first two failures block. The third prints continue false."""
        self._commit_profile(mode="enforce", recipe_body="exit 1")
        self._dirty_package()
        event = self._stop_event()
        first = self._run(event)
        second = self._run(event)
        third = self._run(event)
        assert first[0] == 2
        assert '"decision": "block"' in first[1]
        assert second[0] == 2
        assert third[0] == 0
        assert '"continue": false' in third[1]
        assert "permissionDecision" not in third[1]

    def test_a_timeout_blocks_in_enforce(self) -> None:
        """The checker kills a recipe that exceeds the profile timeout."""
        self._commit_profile(mode="enforce", recipe_body="sleep 30", timeout_seconds=1)
        self._dirty_package()
        code, out, _err = self._run(self._stop_event())
        assert code == 2
        assert "timed out" in out

    def test_unchanged_tree_and_test_only_edits_skip_the_recipe(self) -> None:
        """Stop runs typecheck only when a package file changed."""
        self._commit_profile(mode="enforce", recipe_body="exit 1")
        skipped = self._run(self._stop_event())
        assert skipped[0] == 0
        assert skipped[1] == ""
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "foo.py").write_text("x = 1\n", encoding="utf-8")
        test_only = self._run(self._stop_event())
        assert test_only[0] == 0
        assert test_only[1] == ""

    def test_launcher_runs_master_check_py_not_the_worktree_copy(self) -> None:
        """The hook command executes check.py from master."""
        source_root = Path(__file__).resolve().parents[1]
        self._commit_profile()
        destination = self.repo / "agent_verify"
        destination.mkdir()
        shutil.copy(source_root / "agent_verify" / "check.py", destination / "check.py")
        self._git("add", "agent_verify/check.py")
        self._git("commit", "-m", "add checker")
        (destination / "check.py").write_text(
            "import sys\nsys.stdout.write('worktree\\n')\n",
            encoding="utf-8",
        )
        event = json.dumps(
            self._event(
                "PreToolUse",
                tool_name="Bash",
                command="uv run pytest tests/ -q",
            )
        )
        env = {
            **os.environ,
            "HOME": str(self.home),
            "UV_PROJECT_ENVIRONMENT": _ENGINE_VENV,
        }
        bash = shutil.which("bash")
        if bash is None:
            self.fail("bash is not on PATH")
        completed = subprocess.run(  # bash is an absolute path; the script is the hook command
            [bash, "-c", _hook_command(source_root)],
            check=False,
            cwd=self.repo,
            input=event,
            capture_output=True,
            text=True,
            env=env,
        )
        assert completed.returncode == 2, completed.stderr
        assert "UV_PROJECT_ENVIRONMENT" in completed.stdout
        assert "worktree" not in completed.stdout

    def _commit_profile(
        self,
        *,
        mode: str = "observe",
        recipe_body: str = "exit 0",
        timeout_seconds: int = 90,
    ) -> None:
        (self.repo / "agent-verify.toml").write_text(
            _profile(mode=mode, timeout_seconds=timeout_seconds),
            encoding="utf-8",
        )
        (self.repo / "justfile").write_text(_justfile(recipe_body), encoding="utf-8")
        self._git("init", "-b", "master")
        self._git("add", "agent-verify.toml", "justfile")
        self._git("commit", "-m", "profile")

    def _dirty_package(self) -> None:
        package = self.repo / "pdomain_ocr_cli"
        package.mkdir()
        (package / "changed.py").write_text("x = 1\n", encoding="utf-8")

    def _event(
        self,
        name: str,
        *,
        tool_name: str,
        command: str = "",
        file_path: str = "",
    ) -> dict[str, object]:
        tool_input: dict[str, object] = {}
        if command:
            tool_input["command"] = command
        if file_path:
            tool_input["file_path"] = file_path
        return {
            "hook_event_name": name,
            "session_id": "session-1",
            "cwd": str(self.repo),
            "tool_name": tool_name,
            "tool_input": tool_input,
        }

    def _stop_event(self) -> dict[str, object]:
        return {
            "hook_event_name": "Stop",
            "session_id": "session-1",
            "cwd": str(self.repo),
        }

    def _run(
        self,
        event: Mapping[str, object],
        env: Mapping[str, str] | None = None,
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        merged: dict[str, str] = {"PATH": os.environ.get("PATH", "")}
        if env is not None:
            merged.update(env)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = handle(json.dumps(event), merged, self.home)
        return code, stdout.getvalue(), stderr.getvalue()

    def _git(self, *args: str) -> None:
        git = shutil.which("git")
        if git is None:
            self.fail("git is not on PATH")
        completed = subprocess.run(  # git is an absolute path from shutil.which
            [git, "-C", str(self.repo), *args],
            check=False,
            env={**os.environ, **_GIT_ENV, "HOME": str(self.home)},
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr


def _profile(*, mode: str, timeout_seconds: int) -> str:
    return (
        'base = "master"\n'
        f'mode = "{mode}"\n'
        "\n"
        "[deny]\n"
        'hook_paths = [".claude/settings.json", ".codex/hooks.json", '
        '"agent_verify/", "agent-verify.toml"]\n'
        "outside_venv = true\n"
        "\n"
        "[inner]\n"
        f"timeout_seconds = {timeout_seconds}\n"
        'python = "typecheck"\n'
        'paths = ["pdomain_ocr_cli/"]\n'
    )


def _justfile(recipe_body: str) -> str:
    return (
        'set shell := ["bash", "-eu", "-o", "pipefail", "-c"]\n'
        "set positional-arguments\n"
        "\n"
        "typecheck:\n"
        "    #!/usr/bin/env bash\n"
        "    set -euo pipefail\n"
        f"    {recipe_body}\n"
    )


if __name__ == "__main__":
    unittest.main()
