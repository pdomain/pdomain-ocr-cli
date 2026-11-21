"""Block unsafe tool calls and re-run the repo's typecheck recipe on stop.

The process that runs is ``git show master:agent_verify/check.py``. It reads
``agent-verify.toml`` and the justfile from ``master`` as well, so a worktree
edit of those files is not the judge.

The shell scan leaves these limits allowed: aliases, source, declare,
process substitution, and a shell script file.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

_BASE = "master"
_STATE_DIR_NAME = "pdomain-ocr-cli"
_HOST_MARGIN_SECONDS = 120
_READERS = frozenset({"cat", "head", "tail", "less", "rg", "grep", "ls", "wc", "stat"})
_GIT_READS = frozenset({"diff", "show", "log", "status", "blame", "rev-parse", "ls-files"})
_WRAPPERS = frozenset({"command", "exec", "nohup", "time", "nice", "env"})
_OPTION_ARGUMENT = {
    "exec": frozenset({"-a"}),
    "time": frozenset({"-f", "-o", "--format", "--output"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "env": frozenset({"-u", "-C", "-a", "-S", "--unset", "--chdir", "--argv0", "--split-string"}),
}
_ATTACHED_PREFIX = {
    "exec": ("-a",),
    "time": ("-f", "-o"),
    "nice": ("-n",),
    "env": ("-u", "-C", "-a", "-S"),
}
_SHELLS = frozenset({"bash", "sh", "dash"})
# Short options that do not take an argument. `-o` and `-O` do.
_BASH_NOARG = frozenset("ilrsDabefhkmnptuvxBCEHPT")
_BASH_ARG = frozenset({"o", "O"})
_BASH_LONG_ARG = frozenset({"--rcfile", "--init-file"})
_UNPARSED = "\0"
_OUTPUT_LIMIT = 4000


@dataclass(frozen=True)
class Profile:
    """Rules loaded from ``master:agent-verify.toml``."""

    mode: str
    timeout_seconds: int
    recipe: str
    paths: tuple[str, ...]
    outside_venv: bool
    hook_paths: tuple[str, ...]


class CheckError(Exception):
    """The profile or git base could not be used."""


@dataclass
class _VenvState:
    """The shell's UV_PROJECT_ENVIRONMENT, and whether a child would see it."""

    value: str
    exported: bool

    def child(self) -> str:
        """Return the value a child process inherits."""
        return self.value if self.exported else ""


def main() -> int:
    """Read one hook event from stdin and return the process exit code."""
    return handle(sys.stdin.read(), os.environ, Path.home())


def handle(raw: str, env: Mapping[str, str], home: Path) -> int:
    """Judge one hook event.

    Args:
        raw: The hook event JSON.
        env: The environment the hook inherited.
        home: Home directory used for the would-block log and the failure count.

    Returns:
        ``0`` to allow the tool or the stop. ``2`` to deny or block.
    """
    event = _parse_event(raw)
    if event is None:
        return _fail("The hook event was not a JSON object.")
    kind = _event_kind(event)
    if kind == "other":
        return 0
    root = _git_root(_cwd(event))
    if root is None:
        return _fail("The hook could not find the git root.")
    try:
        profile = _load_profile(root)
    except CheckError as exc:
        return _fail(str(exc))
    if kind == "pre":
        return _pre_tool(event, env, root, profile)
    return _stop(event, env, root, profile, home)


def _parse_event(raw: str) -> dict[str, object] | None:
    try:
        loaded = cast("object", json.loads(raw))
    except json.JSONDecodeError:
        return None
    return _as_object(loaded)


def _as_object(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    mapping = cast("dict[object, object]", value)
    return {key: item for key, item in mapping.items() if isinstance(key, str)}


def _text(event: Mapping[str, object], *keys: str) -> str:
    for key in keys:
        value = event.get(key)
        if isinstance(value, str):
            return value
    return ""


def _cwd(event: Mapping[str, object]) -> Path:
    raw = _text(event, "cwd")
    if raw:
        return Path(raw)
    return Path.cwd()


def _event_kind(event: Mapping[str, object]) -> str:
    raw = _text(event, "hook_event_name", "hookEventName")
    key = raw.replace("_", "").replace("-", "").lower()
    if key == "pretooluse":
        return "pre"
    if key in {"stop", "subagentstop", "subagentend"}:
        return "stop"
    return "other"


def _git_root(cwd: Path) -> Path | None:
    completed = _git(cwd if cwd.is_dir() else Path.cwd(), "rev-parse", "--show-toplevel")
    if completed is None or completed.returncode != 0:
        return None
    try:
        text = completed.stdout.decode().strip()
    except UnicodeDecodeError:
        return None
    if not text:
        return None
    return Path(text)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes] | None:
    git = shutil.which("git")
    if git is None:
        return None
    return subprocess.run(  # noqa: S603  # git is an absolute path from shutil.which
        [git, "-C", str(cwd), *args],
        check=False,
        capture_output=True,
    )


def _git_bytes(root: Path, spec: str) -> bytes:
    completed = _git(root, "show", f"{_BASE}:{spec}")
    if completed is None or completed.returncode != 0:
        message = ""
        if completed is not None:
            message = completed.stderr.decode(errors="replace")
        detail = message.strip() or f"git show {_BASE}:{spec} failed"
        raise CheckError(detail)
    return completed.stdout


def _load_profile(root: Path) -> Profile:
    try:
        text = _git_bytes(root, "agent-verify.toml").decode()
    except UnicodeDecodeError as exc:
        raise CheckError("agent-verify.toml on master is not text.") from exc
    parsed = _as_object(_toml_value(text))
    if parsed is None:
        raise CheckError("agent-verify.toml on master must be a table.")
    if parsed.get("base") != _BASE:
        raise CheckError("agent-verify.toml base must be master.")
    mode = parsed.get("mode")
    if not isinstance(mode, str) or mode not in {"observe", "enforce"}:
        raise CheckError("agent-verify.toml mode must be observe or enforce.")
    inner = _as_object(parsed.get("inner"))
    deny = _as_object(parsed.get("deny"))
    if inner is None or deny is None:
        raise CheckError("agent-verify.toml needs [inner] and [deny].")
    recipe = inner.get("python")
    timeout = inner.get("timeout_seconds")
    if not isinstance(recipe, str) or not _recipe_ok(recipe):
        raise CheckError("The inner recipe name is not a single just recipe.")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
        raise CheckError("timeout_seconds must be a positive integer.")
    outside = deny.get("outside_venv")
    if not isinstance(outside, bool):
        raise CheckError("outside_venv must be true or false.")
    return Profile(
        mode=mode,
        timeout_seconds=min(timeout, _HOST_MARGIN_SECONDS),
        recipe=recipe,
        paths=_string_tuple(inner.get("paths"), "paths"),
        outside_venv=outside,
        hook_paths=_string_tuple(deny.get("hook_paths"), "hook_paths"),
    )


def _toml_value(text: str) -> object:
    try:
        loaded = cast("object", tomllib.loads(text))
    except tomllib.TOMLDecodeError as exc:
        raise CheckError("agent-verify.toml on master is not valid TOML.") from exc
    return loaded


def _recipe_ok(recipe: str) -> bool:
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
    return bool(recipe) and all(char in allowed for char in recipe)


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise CheckError(f"{label} must be a list of strings.")
    items: list[str] = []
    for item in cast("list[object]", value):
        if not isinstance(item, str):
            raise CheckError(f"{label} must be a list of strings.")
        items.append(item)
    return tuple(items)


def _pre_tool(
    event: Mapping[str, object],
    env: Mapping[str, str],
    root: Path,
    profile: Profile,
) -> int:
    if event.get("toolInputTruncated") is True or event.get("tool_input_truncated") is True:
        return _deny("The tool input was truncated, so the hook cannot see the whole command.")
    tool_input = _as_object(event.get("tool_input")) or _as_object(event.get("toolInput")) or {}
    reason = _deny_reason(event, tool_input, env, root, profile)
    if reason is None:
        return 0
    return _deny(reason)


def _deny_reason(
    event: Mapping[str, object],
    tool_input: Mapping[str, object],
    env: Mapping[str, str],
    root: Path,
    profile: Profile,
) -> str | None:
    path_reason = _hook_path_reason(event, tool_input, root, profile.hook_paths)
    if path_reason is not None:
        return path_reason
    if not profile.outside_venv:
        return None
    command = tool_input.get("command")
    if not isinstance(command, str):
        return None
    return _venv_reason(command, env.get("UV_PROJECT_ENVIRONMENT"), root)


def _hook_path_reason(
    event: Mapping[str, object],
    tool_input: Mapping[str, object],
    root: Path,
    hook_paths: tuple[str, ...],
) -> str | None:
    tool = _text(event, "tool_name", "toolName").lower()
    file_path = _edited_path(tool_input)
    if file_path and _matches_hook(file_path, root, hook_paths):
        return f"Writes to {file_path} are reserved for a commit on master."
    command = tool_input.get("command")
    if (
        tool in {"apply_patch", "edit", "write", "search_replace"}
        and isinstance(command, str)
        and _command_mentions_hook(command, root, hook_paths)
    ):
        return "That edit touches a hook file. Those change only on master."
    if not isinstance(command, str) or tool in {"apply_patch"}:
        return None
    return _shell_hook_reason(command, root, hook_paths)


def _edited_path(tool_input: Mapping[str, object]) -> str:
    for key in ("file_path", "filePath", "path", "target_notebook"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _matches_hook(path: str, root: Path, hook_paths: tuple[str, ...]) -> bool:
    relative = _relative_to_root(path, root)
    for hook in hook_paths:
        normalized = hook.strip("/")
        if not normalized:
            continue
        if hook.endswith("/"):
            if relative == normalized or relative.startswith(normalized + "/"):
                return True
        elif relative == normalized:
            return True
    return False


def _relative_to_root(path: str, root: Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return candidate.as_posix()


def _command_mentions_hook(command: str, root: Path, hook_paths: tuple[str, ...]) -> bool:
    for token in command.replace("\\", "/").split():
        cleaned = token.strip("\"'`:,")
        if cleaned and _matches_hook(cleaned, root, hook_paths):
            return True
    return False


def _shell_hook_reason(
    command: str,
    root: Path,
    hook_paths: tuple[str, ...],
    *,
    depth: int = 0,
) -> str | None:
    """Deny a write to a hook path.

    Quoted ``echo`` may mention a hook path. A quoted path passed to another
    command, and a path that resolves with ``.`` or ``..``, still write it.
    """
    if depth > 8:
        return "The command could not be parsed, so the hook denied it."
    prepared = _join_continuations(command)
    for segment, _sep in _split_commands(prepared):
        tokens = _tokens(_strip_redirects(segment))
        if tokens is None:
            return "The command could not be parsed, so the hook denied it."
        if not tokens:
            continue
        for target in _redirect_targets(segment):
            if _word_hits_hook(target, root, hook_paths):
                return f"Writes to {target} are reserved for a commit on master."
        for body in _substitution_bodies(segment):
            reason = _shell_hook_reason(body, root, hook_paths, depth=depth + 1)
            if reason is not None:
                return reason
        for _kind, body in _command_groups(segment):
            reason = _shell_hook_reason(body, root, hook_paths, depth=depth + 1)
            if reason is not None:
                return reason
        script = _hook_script(tokens)
        if script is not None:
            body, skip = script
            reason = _shell_hook_reason(body, root, hook_paths, depth=depth + 1)
            if reason is not None:
                return reason
            for cursor, token in enumerate(tokens):
                if cursor in skip:
                    continue
                if _word_hits_hook(token, root, hook_paths):
                    return f"Writes to {token} are reserved for a commit on master."
            continue
        subject = _subject(tokens)
        if _is_reader(subject):
            continue
        for word in _unquoted_words(segment):
            if _word_hits_hook(word, root, hook_paths):
                return f"Writes to {word} are reserved for a commit on master."
        if _is_echo(subject):
            continue
        for token in subject:
            if _word_hits_hook(token, root, hook_paths):
                return f"Writes to {token} are reserved for a commit on master."
    return None


_SUBJECT_WRAPPERS = frozenset({"command", "exec", "nohup", "time", "nice", "env"})


def _subject(tokens: list[str]) -> list[str]:
    """Return the program a wrapper runs, including its arguments."""
    index = 0
    while index < len(tokens):
        if _assignment_parts(tokens[index]) is not None:
            index += 1
            continue
        name = Path(tokens[index]).name
        if name == "timeout":
            index = _skip_timeout(tokens, index + 1)
            continue
        if name not in _SUBJECT_WRAPPERS:
            return tokens[index:]
        index, _ignored, script = _skip_wrapper_options(name, tokens, index + 1, "")
        if script is not None:
            return []
    return []


def _is_echo(tokens: list[str]) -> bool:
    return bool(tokens) and Path(tokens[0]).name == "echo"


def _word_hits_hook(word: str, root: Path, hook_paths: tuple[str, ...]) -> bool:
    """True when a word, or the value after ``=``, is a hook path."""
    if _contains_hook(word, hook_paths) or _matches_hook(word, root, hook_paths):
        return True
    if "=" not in word:
        return False
    value = word.split("=", 1)[1]
    return _contains_hook(value, hook_paths) or _matches_hook(value, root, hook_paths)


def _hook_script(tokens: list[str]) -> tuple[str, frozenset[int]] | None:
    """Return a ``-c``, ``eval``, or ``env -S`` script and the token indexes to skip.

    The skipped indexes are the script text. Other arguments are still checked.
    """
    index = 0
    while index < len(tokens):
        if _assignment_parts(tokens[index]) is not None:
            index += 1
            continue
        name = Path(tokens[index]).name
        if name == "timeout":
            index = _skip_timeout(tokens, index + 1)
            continue
        if name in _WRAPPERS:
            start = index
            index, _ignored, script = _skip_wrapper_options(name, tokens, index + 1, "")
            if script is not None:
                return script, _matching_indexes(tokens, script, start)
            continue
        if name in _SHELLS:
            script = _c_script(tokens, index)
            if script is None:
                return None
            return script, _matching_indexes(tokens, script, index + 1)
        if name == "eval":
            return " ".join(tokens[index + 1 :]), frozenset(range(index + 1, len(tokens)))
        return None
    return None


def _matching_indexes(tokens: list[str], text: str, start: int) -> frozenset[int]:
    """Return the first token index at or after ``start`` whose text is ``text``."""
    for cursor in range(start, len(tokens)):
        if tokens[cursor] == text:
            return frozenset({cursor})
    return frozenset()


def _is_reader(tokens: list[str]) -> bool:
    if not tokens:
        return False
    name = Path(tokens[0]).name
    if name in _READERS:
        return True
    return name == "git" and len(tokens) > 1 and tokens[1] in _GIT_READS


def _contains_hook(token: str, hook_paths: tuple[str, ...]) -> bool:
    text = token.replace("\\", "/")
    for hook in hook_paths:
        if hook.endswith("/"):
            bare = hook.strip("/")
            if bare and (f"{bare}/" in text or text.rstrip("/") == bare):
                return True
        elif hook and hook in text:
            return True
    return False


def _unquoted_words(segment: str) -> list[str]:
    """Words outside quotes. A ``#`` that starts a word ends the segment."""
    words: list[str] = []
    buf: list[str] = []
    quote = ""
    index = 0
    while index < len(segment):
        char = segment[index]
        if quote:
            if char == "\\" and quote == '"' and index + 1 < len(segment):
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if char == "\\" and index + 1 < len(segment):
            buf.append(segment[index + 1])
            index += 2
            continue
        if char in {" ", "\t", "\n"}:
            if buf:
                words.append("".join(buf))
                buf = []
            index += 1
            continue
        if char == "#" and not buf:
            break
        buf.append(char)
        index += 1
    if buf:
        words.append("".join(buf))
    return words


def _redirect_targets(segment: str) -> list[str]:
    """File targets of unquoted redirects. Quoted ``>`` is not an operator."""
    found: list[str] = []
    quote = ""
    index = 0
    at_word_start = True
    while index < len(segment):
        char = segment[index]
        if quote:
            if char == "\\" and quote == '"' and index + 1 < len(segment):
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            at_word_start = False
            index += 1
            continue
        if char == "\\":
            at_word_start = False
            index += 2
            continue
        if char in {" ", "\t", "\n"}:
            at_word_start = True
            index += 1
            continue
        if char == "#" and at_word_start:
            break
        at_word_start = False
        operator = _redirect_operator(segment, index)
        if operator is None:
            index += 1
            continue
        op, op_len = operator
        target, index = _redirect_target(segment, index + op_len)
        if op == ">&" and target.isdigit():
            continue
        if target.startswith("|"):
            target = target[1:]
        if target:
            found.append(target)
    return found


def _strip_redirects(segment: str) -> str:
    """Remove unquoted redirect operators and targets, leaving the command."""
    kept: list[str] = []
    quote = ""
    index = 0
    at_word_start = True
    while index < len(segment):
        char = segment[index]
        if quote == "'":
            kept.append(char)
            if char == "'":
                quote = ""
            index += 1
            continue
        if quote == '"':
            if char == "\\" and index + 1 < len(segment):
                kept.append(segment[index : index + 2])
                index += 2
                continue
            kept.append(char)
            if char == '"':
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            kept.append(char)
            at_word_start = False
            index += 1
            continue
        if char == "\\" and index + 1 < len(segment):
            kept.append(segment[index : index + 2])
            index += 2
            at_word_start = False
            continue
        if char in {" ", "\t", "\n"}:
            kept.append(char)
            at_word_start = True
            index += 1
            continue
        if char == "#" and at_word_start:
            break
        operator = _redirect_operator(segment, index)
        if operator is not None:
            _drop_fd_number(kept)
            _op, op_len = operator
            _target, index = _redirect_target(segment, index + op_len)
            at_word_start = True
            continue
        kept.append(char)
        at_word_start = False
        index += 1
    return "".join(kept)


def _drop_fd_number(kept: list[str]) -> None:
    """Drop a file-descriptor number glued to the redirect operator."""
    text = "".join(kept)
    start = len(text)
    while start > 0 and text[start - 1].isdigit():
        start -= 1
    if start == len(text):
        return
    if start > 0 and text[start - 1] not in {" ", "\t", "\n"}:
        return
    kept.clear()
    prefix = text[:start]
    if prefix:
        kept.append(prefix)


def _redirect_operator(segment: str, index: int) -> tuple[str, int] | None:
    for op in ("&>>", "&>", ">>", ">|", ">&", "<>", ">"):
        if segment.startswith(op, index):
            return op, len(op)
    return None


def _redirect_target(segment: str, index: int) -> tuple[str, int]:
    while index < len(segment) and segment[index] in {" ", "\t"}:
        index += 1
    if index >= len(segment):
        return "", index
    if segment[index] in {"'", '"'}:
        quote = segment[index]
        index += 1
        buf: list[str] = []
        while index < len(segment) and segment[index] != quote:
            buf.append(segment[index])
            index += 1
        if index < len(segment):
            index += 1
        return "".join(buf), index
    buf = []
    while index < len(segment) and segment[index] not in {" ", "\t", "\n", "|", ";", "&"}:
        buf.append(segment[index])
        index += 1
    return "".join(buf), index


def _venv_reason(command: str, inherited: str | None, root: Path) -> str | None:
    found = _scan(command, _state_from(inherited), root, depth=0)
    if found == _UNPARSED:
        return "The command could not be parsed, so the hook denied it."
    if found is None:
        return None
    if _shell_expands(found) or _outside_root(found, root):
        return (
            "UV_PROJECT_ENVIRONMENT points outside the repo "
            f"({found}). uv and just are denied until it is unset "
            "or points inside the checkout."
        )
    return None


def _state_from(inherited: str | None) -> _VenvState:
    if inherited is None:
        return _VenvState(value="", exported=False)
    return _VenvState(value=inherited, exported=True)


def _join_continuations(command: str) -> str:
    return command.replace("\\\r\n", "").replace("\\\n", "")


def _scan(command: str, state: _VenvState, root: Path, *, depth: int) -> str | None:
    """Return the venv a nested script would give uv, or ``_UNPARSED``."""
    found, _end = _scan_with_state(command, state, root, depth=depth)
    return found


def _scan_with_state(
    command: str,
    state: _VenvState,
    root: Path,
    *,
    depth: int,
) -> tuple[str | None, _VenvState]:
    """Return the venv uv would see, and the shell state after the command."""
    if depth > 8:
        return state.child() or _UNPARSED, state
    shell = state
    pipeline: _VenvState | None = None
    found: str | None = None
    for segment, sep in _split_commands(_join_continuations(command)):
        base = pipeline if pipeline is not None else shell
        if not segment:
            pipeline = base if _is_pipe(sep) else None
            continue
        tokens = _tokens(_strip_redirects(segment))
        if tokens is None:
            return _UNPARSED, shell
        nested = _scan_substitutions(segment, base, root, depth=depth)
        if _venv_blocks(nested, root):
            return nested, shell
        if nested is not None:
            found = nested
        grouped, brace_state = _scan_groups(segment, base, root, depth=depth)
        if _venv_blocks(grouped, root):
            return grouped, shell
        if grouped is not None:
            found = grouped
        effective = _effective_venv(tokens, base, root, depth=depth)
        if _venv_blocks(effective, root):
            return effective, shell
        if effective is not None:
            found = effective
        if _is_pipe(sep):
            if pipeline is None:
                pipeline = shell
            continue
        if sep != "&" and pipeline is None:
            if brace_state is not None:
                shell = brace_state
            else:
                shell = _shell_after(tokens, shell, root, depth=depth)
        pipeline = None
    return found, shell


def _is_pipe(sep: str) -> bool:
    """True for ``|`` and ``|&``. Neither updates the parent shell."""
    return sep in {"|", "|&"}


def _venv_blocks(found: str | None, root: Path) -> bool:
    """True when a venv result must stop the scan."""
    if found == _UNPARSED:
        return True
    return found is not None and (_shell_expands(found) or _outside_root(found, root))


def _scan_groups(
    segment: str,
    state: _VenvState,
    root: Path,
    *,
    depth: int,
) -> tuple[str | None, _VenvState | None]:
    """Scan ``(...)`` and ``{ ...; }``. Only a brace group updates the shell."""
    found: str | None = None
    brace_state: _VenvState | None = None
    for kind, body in _command_groups(segment):
        nested, end = _scan_with_state(body, state, root, depth=depth + 1)
        if _venv_blocks(nested, root):
            return nested, brace_state
        if nested is not None:
            found = nested
        if kind == "brace":
            brace_state = end
    return found, brace_state


def _effective_venv(
    tokens: list[str],
    state: _VenvState,
    root: Path,
    *,
    depth: int,
) -> str | None:
    """Return the venv a uv or just command would use.

    ``None`` means this word list does not run uv or just. A prefix
    assignment applies only to that command. ``+=`` appends.
    """
    current = state.child()
    # ``+=`` appends to the shell value even when that value is not exported.
    assigned = state.value
    index = 0
    while index < len(tokens):
        parsed = _assignment_parts(tokens[index])
        if parsed is not None:
            key, value, append = parsed
            if key == "UV_PROJECT_ENVIRONMENT":
                assigned = _apply_assignment(assigned, value, append=append)
                current = assigned
            index += 1
            continue
        name = Path(tokens[index]).name
        if name in _WRAPPERS:
            index += 1
            index, current, script = _skip_wrapper_options(name, tokens, index, current)
            if script is not None:
                return _scan(script, _VenvState(current, True), root, depth=depth + 1)
            continue
        if name == "timeout":
            index = _skip_timeout(tokens, index + 1)
            continue
        if name in _SHELLS:
            script = _c_script(tokens, index)
            if script is None:
                return None
            return _scan(script, _VenvState(current, True), root, depth=depth + 1)
        if name == "eval":
            script = " ".join(tokens[index + 1 :])
            return _scan(script, _VenvState(current, True), root, depth=depth + 1)
        if name in {"uv", "just"}:
            return current
        return None
    return None


def _apply_assignment(current: str, value: str, *, append: bool) -> str:
    if append:
        return f"{current}{value}"
    return value


def _shell_after(
    tokens: list[str],
    state: _VenvState,
    root: Path,
    *,
    depth: int,
) -> _VenvState:
    """Shell state after a command. Prefix assignments do not persist.

    ``export`` and ``unset`` apply every name operand, including names that
    follow the variable. ``command export`` and ``eval`` update this shell.
    """
    value = state.value
    exported = state.exported
    index = 0
    while index < len(tokens):
        parsed = _assignment_parts(tokens[index])
        if parsed is not None:
            key, raw, append = parsed
            if key == "UV_PROJECT_ENVIRONMENT":
                base = value if append else ""
                value = _apply_assignment(base, raw, append=append)
            index += 1
            continue
        # A prefix applies only to the command. export and unset start
        # from the shell state that was already in effect.
        return _command_shell(tokens, index, state, root, depth=depth)
    return _VenvState(value, exported)


def _command_shell(
    tokens: list[str],
    index: int,
    state: _VenvState,
    root: Path,
    *,
    depth: int,
) -> _VenvState:
    """Shell state after a real command. A redirect does not cancel export."""
    value = state.value
    exported = state.exported
    while index < len(tokens):
        name = Path(tokens[index]).name
        if name == "command":
            index = _skip_leading_flags(tokens, index + 1)
            continue
        if name == "eval":
            script = " ".join(tokens[index + 1 :])
            _found, end = _scan_with_state(
                script,
                _VenvState(value, exported),
                root,
                depth=depth + 1,
            )
            return end
        if name in {"export", "unset"}:
            value, exported, _index = _export_or_unset(
                name, tokens, index + 1, value, exported=exported
            )
            return _VenvState(value, exported)
        return state
    return _VenvState(value, exported)


def _skip_leading_flags(tokens: list[str], index: int) -> int:
    while index < len(tokens) and tokens[index].startswith("-"):
        index += 1
    return index


def _export_or_unset(
    name: str,
    tokens: list[str],
    index: int,
    value: str,
    *,
    exported: bool,
) -> tuple[str, bool, int]:
    """Apply ``export`` or ``unset`` operands. A later name is still an operand.

    ``unset -f`` removes a function, not the variable. ``export -n`` clears
    the export flag. ``-f`` and ``-v`` together do nothing, as bash refuses
    that unset.
    """
    if name == "unset":
        # ``-f`` unsets a function. With ``-v`` as well, bash refuses both.
        functions = False
        while index < len(tokens):
            word = tokens[index]
            if word == "--":
                index += 1
                break
            flags = _short_flags(word)
            if flags is not None:
                functions = functions or "f" in flags
                index += 1
                continue
            if not _is_shell_name(word):
                break
            if word == "UV_PROJECT_ENVIRONMENT" and not functions:
                value, exported = "", False
            index += 1
        return value, exported, index
    unexport = False
    while index < len(tokens):
        word = tokens[index]
        if word == "--":
            index += 1
            break
        flags = _short_flags(word)
        if flags is not None or (word.startswith("--") and _assignment_parts(word) is None):
            if flags is not None and "n" in flags:
                unexport = True
            index += 1
            continue
        parsed = _assignment_parts(word)
        if parsed is not None:
            key, raw, append = parsed
            if key == "UV_PROJECT_ENVIRONMENT":
                base = value if append else ""
                value = _apply_assignment(base, raw, append=append)
                exported = not unexport
            index += 1
            continue
        if not _is_shell_name(word):
            break
        if word == "UV_PROJECT_ENVIRONMENT":
            exported = not unexport
        index += 1
    return value, exported, index


def _short_flags(word: str) -> str | None:
    """Return the letters of a short option such as ``-n`` or ``-fv``."""
    if len(word) < 2 or not word.startswith("-") or word.startswith("--"):
        return None
    return word[1:]


def _is_shell_name(word: str) -> bool:
    if not word or not (word[0].isalpha() or word[0] == "_"):
        return False
    return all(char.isalnum() or char == "_" for char in word[1:])


def _shell_expands(value: str) -> bool:
    return "$" in value or "`" in value


def _scan_substitutions(
    segment: str,
    state: _VenvState,
    root: Path,
    *,
    depth: int,
) -> str | None:
    """Scan ``$(...)`` and backticks with the exported child environment."""
    found: str | None = None
    child = _VenvState(state.child(), True)
    for body in _substitution_bodies(segment):
        nested = _scan(body, child, root, depth=depth + 1)
        if nested == _UNPARSED or (nested is not None and _outside_root(nested, root)):
            return nested
        if nested is not None:
            found = nested
    return found


def _substitution_bodies(text: str) -> list[str]:
    """Return command-substitution bodies the shell would run.

    Single quotes hide a substitution. A ``#`` that starts an unquoted
    word ends the text, because the rest is a comment.
    """
    found: list[str] = []
    index = 0
    quote = ""
    at_word_start = True
    while index < len(text):
        char = text[index]
        if quote == "'":
            if char == "'":
                quote = ""
            index += 1
            continue
        if char in {" ", "\t", "\n"} and not quote:
            at_word_start = True
            index += 1
            continue
        if char == "#" and at_word_start and not quote:
            break
        if not quote and char in {"'", '"'}:
            quote = char
            at_word_start = False
            index += 1
            continue
        if quote == '"' and char == '"':
            quote = ""
            index += 1
            continue
        if char == "\\" and index + 1 < len(text) and quote != "'":
            at_word_start = False
            index += 2
            continue
        at_word_start = False
        if text.startswith("$(", index):
            body, index = _paren_body(text, index + 2)
            found.append(body)
            continue
        if char == "`":
            body, index = _backtick_body(text, index + 1)
            found.append(body)
            continue
        index += 1
    return found


def _paren_body(text: str, start: int) -> tuple[str, int]:
    """Return the inside of ``$(...)`` and the index after its closing paren."""
    depth = 1
    index = start
    quote = ""
    buf: list[str] = []
    while index < len(text) and depth:
        char = text[index]
        if quote == "'":
            buf.append(char)
            if char == "'":
                quote = ""
            index += 1
            continue
        if quote == '"':
            buf.append(char)
            if char == "\\" and index + 1 < len(text):
                buf.append(text[index + 1])
                index += 2
                continue
            if char == '"':
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            buf.append(char)
            index += 1
            continue
        if text.startswith("$(", index):
            depth += 1
            buf.append("$(")
            index += 2
            continue
        if char == "(":
            depth += 1
            buf.append(char)
            index += 1
            continue
        if char == ")":
            depth -= 1
            if depth == 0:
                return "".join(buf), index + 1
            buf.append(char)
            index += 1
            continue
        buf.append(char)
        index += 1
    return "".join(buf), index


def _backtick_body(text: str, start: int) -> tuple[str, int]:
    """Return the inside of a backtick substitution and the index after it."""
    buf: list[str] = []
    index = start
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text) and text[index + 1] in {"`", "$", "\\"}:
            buf.append(text[index + 1])
            index += 2
            continue
        if char == "`":
            return "".join(buf), index + 1
        buf.append(char)
        index += 1
    return "".join(buf), index


def _skip_wrapper_options(
    wrapper: str,
    tokens: list[str],
    index: int,
    current: str,
) -> tuple[int, str, str | None]:
    """Skip flags after a wrapper. The third value is an ``env -S`` script."""
    while index < len(tokens):
        word = tokens[index]
        if word == "--":
            return index + 1, current, None
        if _assignment_parts(word) is not None or not word.startswith("-"):
            return index, current, None
        if wrapper == "env" and word == "-":
            current = ""
            index += 1
            continue
        if wrapper == "env" and word.startswith("-") and not word.startswith("--"):
            index, current, script = _env_shorts(word, tokens, index, current)
            if script is not None:
                return index, current, script
            continue
        if wrapper == "env" and word in {"-i", "--ignore-environment"}:
            current = ""
            index += 1
            continue
        if wrapper == "exec" and word == "-c":
            current = ""
            index += 1
            continue
        option, attached = _split_option(wrapper, word)
        if wrapper == "env" and option in {"-S", "--split-string"} and attached is not None:
            return index + 1, current, attached
        if option in _OPTION_ARGUMENT.get(wrapper, frozenset()) and attached is None:
            if _unsets_project_env(wrapper, option, tokens, index + 1):
                current = ""
            if wrapper == "env" and option in {"-S", "--split-string"}:
                script = tokens[index + 1] if index + 1 < len(tokens) else ""
                return index + 2, current, script
            index += 2 if index + 1 < len(tokens) else 1
            continue
        if _unsets_attached(wrapper, option, attached):
            current = ""
        index += 1
    return index, current, None


def _env_shorts(
    word: str,
    tokens: list[str],
    index: int,
    current: str,
) -> tuple[int, str, str | None]:
    """Read a clustered ``env`` short option such as ``-iC/tmp`` or ``-a``."""
    body = word[1:]
    pos = 0
    script: str | None = None
    next_index = index + 1
    while pos < len(body):
        flag = body[pos]
        rest = body[pos + 1 :]
        if flag == "i":
            current = ""
            pos += 1
            continue
        if flag in {"0", "v"}:
            pos += 1
            continue
        if flag in {"u", "C", "a", "S"}:
            if rest:
                arg = rest
                pos = len(body)
            elif next_index < len(tokens):
                arg = tokens[next_index]
                next_index += 1
                pos = len(body)
            else:
                arg = ""
                pos = len(body)
            if flag == "u" and arg == "UV_PROJECT_ENVIRONMENT":
                current = ""
            if flag == "S":
                script = arg
            continue
        pos += 1
    return next_index, current, script


def _split_option(wrapper: str, word: str) -> tuple[str, str | None]:
    if word.startswith("--") and "=" in word:
        option, value = word.split("=", 1)
        return option, value
    for prefix in _ATTACHED_PREFIX.get(wrapper, ()):
        if word.startswith(prefix) and len(word) > len(prefix):
            return prefix, word[len(prefix) :]
    return word, None


def _unsets_project_env(wrapper: str, option: str, tokens: list[str], arg_index: int) -> bool:
    if wrapper != "env" or option not in {"-u", "--unset"}:
        return False
    return arg_index < len(tokens) and tokens[arg_index] == "UV_PROJECT_ENVIRONMENT"


def _unsets_attached(wrapper: str, option: str, attached: str | None) -> bool:
    return wrapper == "env" and option in {"-u", "--unset"} and attached == "UV_PROJECT_ENVIRONMENT"


def _assignment_parts(token: str) -> tuple[str, str, bool] | None:
    """Return key, value, and whether the operator is ``+=``.

    The operator is the one that follows the name. ``+=`` inside the value
    stays part of the value.
    """
    if not token or not (token[0].isalpha() or token[0] == "_"):
        return None
    index = 1
    while index < len(token) and (token[index].isalnum() or token[index] == "_"):
        index += 1
    if token.startswith("+=", index):
        return token[:index], token[index + 2 :], True
    if token.startswith("=", index):
        return token[:index], token[index + 1 :], False
    return None


def _c_script(tokens: list[str], index: int) -> str | None:
    """Return the script after ``bash -c``, or None when bash runs a file.

    ``-o`` and ``-O`` take the next word. A clustered ``-c`` whose other
    letters are flags, such as ``-cl``, uses the next word as the script.
    """
    cursor = index + 1
    while cursor < len(tokens):
        word = tokens[cursor]
        if word in {"--", "-"} or not word.startswith("-"):
            return None
        if word.startswith("--"):
            option, sep, _value = word.partition("=")
            if option in _BASH_LONG_ARG and sep != "=":
                cursor += 2
                continue
            cursor += 1
            continue
        script, cursor = _bash_short_cluster(word[1:], tokens, cursor)
        if script is not None:
            return script
    return None


def _bash_short_cluster(
    body: str,
    tokens: list[str],
    cursor: int,
) -> tuple[str | None, int]:
    """Walk one short-option cluster. The string is the ``-c`` script."""
    pos = 0
    next_index = cursor + 1
    while pos < len(body):
        flag = body[pos]
        rest = body[pos + 1 :]
        if flag == "c":
            if rest and all(char in _BASH_NOARG for char in rest):
                script = tokens[next_index] if next_index < len(tokens) else ""
                return script, next_index
            if rest:
                return rest, next_index
            script = tokens[next_index] if next_index < len(tokens) else ""
            return script, next_index
        if flag in _BASH_ARG:
            if rest:
                return None, next_index
            if next_index >= len(tokens):
                return None, next_index
            return None, next_index + 1
        pos += 1
    return None, next_index


def _skip_timeout(tokens: list[str], index: int) -> int:
    """Skip timeout flags and the duration, leaving the command."""
    while index < len(tokens):
        word = tokens[index]
        if word == "--":
            return index + 2 if index + 1 < len(tokens) else index + 1
        if not word.startswith("-"):
            return index + 1
        option = word.split("=", 1)[0]
        if option in {"-k", "--kill-after", "-s", "--signal"} and "=" not in word:
            index += 2
            continue
        index += 1
    return index


def _outside_root(value: str, root: Path) -> bool:
    """Return whether a venv value is outside the repo.

    Empty is inside. A relative path is joined to the git root first.
    A value that contains ``$`` or a backtick is outside.
    """
    if not value:
        return False
    if _shell_expands(value):
        return True
    expanded = Path(value).expanduser()
    if not expanded.is_absolute():
        expanded = root / expanded
    try:
        return not expanded.resolve().is_relative_to(root.resolve())
    except OSError:
        return True


def _redirect_ampersand(command: str, index: int) -> bool:
    """True when this ``&`` is part of ``>&``, ``&>``, or ``&>>``."""
    if index > 0 and command[index - 1] == ">":
        return True
    return index + 1 < len(command) and command[index + 1] == ">"


def _split_commands(command: str) -> list[tuple[str, str]]:
    """Split on separators outside quotes, substitutions, and groups.

    The second item is the separator that followed. ``$(...)``, backticks,
    process substitution, ``(...)``, and ``{ ...; }`` stay one piece.
    """
    parts: list[tuple[str, str]] = []
    buf: list[str] = []
    quote = ""
    index = 0
    at_word_start = True
    while index < len(command):
        char = command[index]
        if quote == "'":
            buf.append(char)
            if char == "'":
                quote = ""
            index += 1
            continue
        if quote == '"':
            if char == "\\" and index + 1 < len(command):
                buf.append(command[index : index + 2])
                index += 2
                continue
            buf.append(char)
            if char == '"':
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            buf.append(char)
            at_word_start = False
            index += 1
            continue
        if char == "\\" and index + 1 < len(command):
            buf.append(command[index : index + 2])
            index += 2
            at_word_start = False
            continue
        if char in {" ", "\t"}:
            buf.append(char)
            at_word_start = True
            index += 1
            continue
        if char == "#" and at_word_start:
            newline = command.find("\n", index)
            if newline == -1:
                break
            index = newline
            continue
        hidden = _hidden_end(command, index, at_word_start=at_word_start)
        if hidden is not None:
            buf.append(command[index:hidden])
            index = hidden
            at_word_start = False
            continue
        sep = ""
        if command.startswith("|&", index):
            sep = "|&"
        elif command.startswith(("&&", "||"), index):
            sep = command[index : index + 2]
        elif char == "&" and not _redirect_ampersand(command, index):
            sep = "&"
        elif char == "|" and _closes_force_redirect(command, index):
            buf.append(char)
            at_word_start = False
            index += 1
            continue
        elif char in {";", "\n", "|"}:
            sep = char
        if sep:
            parts.append(("".join(buf).strip(), sep))
            buf = []
            index += len(sep)
            at_word_start = True
            continue
        buf.append(char)
        at_word_start = False
        index += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append((tail, ""))
    return parts


def _closes_force_redirect(command: str, index: int) -> bool:
    """True when this ``|`` finishes an unescaped ``>|`` redirect."""
    if index == 0 or command[index - 1] != ">":
        return False
    slashes = 0
    cursor = index - 2
    while cursor >= 0 and command[cursor] == "\\":
        slashes += 1
        cursor -= 1
    return slashes % 2 == 0


def _hidden_end(command: str, index: int, *, at_word_start: bool) -> int | None:
    """Return the index after a substitution or group, or None."""
    if command.startswith("$(", index):
        return _paren_body(command, index + 2)[1]
    if command[index] == "`":
        return _backtick_body(command, index + 1)[1]
    if command.startswith("<(", index) or command.startswith(">(", index):
        return _paren_body(command, index + 2)[1]
    if at_word_start and command[index] == "(":
        return _paren_body(command, index + 1)[1]
    if at_word_start and _is_brace_word(command, index):
        return _brace_body(command, index + 1)[1]
    return None


def _command_groups(segment: str) -> list[tuple[str, str]]:
    """Return subshell and brace bodies. Process substitution stays out."""
    found: list[tuple[str, str]] = []
    index = 0
    quote = ""
    at_word_start = True
    while index < len(segment):
        char = segment[index]
        if quote == "'":
            if char == "'":
                quote = ""
            index += 1
            continue
        if quote == '"':
            if char == "\\" and index + 1 < len(segment):
                index += 2
                continue
            if char == '"':
                quote = ""
            index += 1
            continue
        if char in {" ", "\t", "\n"}:
            at_word_start = True
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            at_word_start = False
            index += 1
            continue
        if char == "\\" and index + 1 < len(segment):
            at_word_start = False
            index += 2
            continue
        if char == "#" and at_word_start:
            break
        if segment.startswith("$(", index):
            index = _paren_body(segment, index + 2)[1]
            at_word_start = False
            continue
        if char == "`":
            index = _backtick_body(segment, index + 1)[1]
            at_word_start = False
            continue
        if segment.startswith("<(", index) or segment.startswith(">(", index):
            index = _paren_body(segment, index + 2)[1]
            at_word_start = False
            continue
        if at_word_start and char == "(":
            body, index = _paren_body(segment, index + 1)
            found.append(("subshell", body))
            at_word_start = False
            continue
        if at_word_start and _is_brace_word(segment, index):
            body, index = _brace_body(segment, index + 1)
            found.append(("brace", body))
            at_word_start = False
            continue
        at_word_start = False
        index += 1
    return found


def _is_brace_word(text: str, index: int) -> bool:
    """True when ``{`` is its own word."""
    if index >= len(text) or text[index] != "{":
        return False
    nxt = index + 1
    return nxt >= len(text) or text[nxt] in " \t\n}"


def _brace_body(text: str, start: int) -> tuple[str, int]:
    """Return the inside of a ``{ ... }`` group and the index after ``}``."""
    depth = 1
    index = start
    quote = ""
    at_word_start = True
    buf: list[str] = []
    while index < len(text) and depth:
        char = text[index]
        if quote == "'":
            buf.append(char)
            if char == "'":
                quote = ""
            index += 1
            continue
        if quote == '"':
            buf.append(char)
            if char == "\\" and index + 1 < len(text):
                buf.append(text[index + 1])
                index += 2
                continue
            if char == '"':
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            buf.append(char)
            at_word_start = False
            index += 1
            continue
        if char in {" ", "\t", "\n"}:
            buf.append(char)
            at_word_start = True
            index += 1
            continue
        if char == "\\" and index + 1 < len(text):
            buf.append(char)
            buf.append(text[index + 1])
            at_word_start = False
            index += 2
            continue
        if (
            text.startswith("$(", index)
            or text.startswith("<(", index)
            or text.startswith(">(", index)
        ):
            _body, end = _paren_body(text, index + 2)
            buf.append(text[index:end])
            index = end
            at_word_start = False
            continue
        if at_word_start and char == "(":
            _body, end = _paren_body(text, index + 1)
            buf.append(text[index:end])
            index = end
            at_word_start = False
            continue
        if char == "`":
            _body, end = _backtick_body(text, index + 1)
            buf.append(text[index:end])
            index = end
            at_word_start = False
            continue
        if at_word_start and _is_brace_word(text, index):
            depth += 1
            buf.append(char)
            at_word_start = False
            index += 1
            continue
        if at_word_start and char == "}" and _closes_word(text, index):
            depth -= 1
            if depth == 0:
                return "".join(buf), index + 1
            buf.append(char)
            at_word_start = False
            index += 1
            continue
        buf.append(char)
        at_word_start = False
        index += 1
    return "".join(buf), index


def _closes_word(text: str, index: int) -> bool:
    """True when the character after ``}`` ends that word."""
    nxt = index + 1
    return nxt >= len(text) or text[nxt] in " \t\n;&|)}"


def _tokens(segment: str) -> list[str] | None:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return None


def _stop(
    event: Mapping[str, object],
    env: Mapping[str, str],
    root: Path,
    profile: Profile,
    home: Path,
) -> int:
    try:
        changed = _paths_changed(root, profile.paths)
    except CheckError as exc:
        return _fail(f"git could not list changed files, so typecheck was not skipped. {exc}")
    if not changed:
        return 0
    if profile.outside_venv and _outside_root(env.get("UV_PROJECT_ENVIRONMENT", ""), root):
        reason = (
            "UV_PROJECT_ENVIRONMENT points outside the repo, so typecheck was not run. "
            "Unset it or point it inside the checkout."
        )
        return _finish(event, profile, home, reason)
    code, output = _run_recipe(root, profile, env, home)
    if code == 0:
        return 0
    reason = f"just {profile.recipe} failed (exit {code}).\n{output}"
    return _finish(event, profile, home, reason)


def _paths_changed(root: Path, prefixes: tuple[str, ...]) -> bool:
    changed = _name_list(root, "diff", "--name-only", "HEAD")
    changed.extend(_name_list(root, "ls-files", "--others", "--exclude-standard"))
    for name in changed:
        posix = name.replace("\\", "/")
        for prefix in prefixes:
            bare = prefix.strip("/")
            if posix == bare or posix.startswith(bare + "/"):
                return True
    return False


def _name_list(root: Path, *args: str) -> list[str]:
    completed = _git(root, *args)
    if completed is None or completed.returncode != 0:
        detail = (
            "git is not on PATH"
            if completed is None
            else completed.stderr.decode(errors="replace").strip()
        )
        raise CheckError(detail or "git could not list changed files")
    try:
        text = completed.stdout.decode()
    except UnicodeDecodeError as exc:
        message = "git output was not UTF-8, so typecheck was not skipped."
        raise CheckError(message) from exc
    return [line for line in text.splitlines() if line]


def _just_program(env: Mapping[str, str], home: Path) -> str | None:
    """Return ``just`` from ``PATH``, then ``~/.local/bin/just`` under ``home``."""
    found = shutil.which("just", path=env.get("PATH"))
    if found is not None:
        return found
    fallback = home / ".local" / "bin" / "just"
    if fallback.is_file() and os.access(fallback, os.X_OK):
        return str(fallback)
    return None


def _run_recipe(
    root: Path,
    profile: Profile,
    env: Mapping[str, str],
    home: Path,
) -> tuple[int, str]:
    just = _just_program(env, home)
    if just is None:
        return 127, "just is not on PATH and ~/.local/bin/just is missing."
    try:
        justfile = _git_bytes(root, "justfile")
    except CheckError as exc:
        return 1, str(exc)
    child_env = dict(env)
    _ = child_env.pop("AI", None)
    proc = subprocess.Popen(  # noqa: S603  # just is an absolute path; the recipe name is one token
        [just, "--justfile", "-", "--working-directory", str(root), profile.recipe],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=root,
        env=child_env,
        start_new_session=True,
    )
    try:
        output, _ = proc.communicate(justfile, timeout=profile.timeout_seconds)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        output, _ = proc.communicate()
        text = _clip(output.decode(errors="replace"))
        return 124, f"just {profile.recipe} timed out after {profile.timeout_seconds}s.\n{text}"
    text = _clip(output.decode(errors="replace"))
    return proc.returncode if proc.returncode is not None else 1, text


def _kill_group(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _clip(text: str) -> str:
    if len(text) <= _OUTPUT_LIMIT:
        return text
    return text[-_OUTPUT_LIMIT:]


def _finish(
    event: Mapping[str, object],
    profile: Profile,
    home: Path,
    reason: str,
) -> int:
    state = home / ".local" / "state" / "agent-verify" / _STATE_DIR_NAME
    if profile.mode == "observe":
        _append_log(state, reason)
        return 0
    count = _bump_failures(state, _text(event, "session_id", "sessionId") or "unknown")
    if count >= 3:
        _emit({"continue": False, "stopReason": reason})
        return 0
    return _block(reason)


def _append_log(state: Path, reason: str) -> None:
    state.mkdir(parents=True, exist_ok=True)
    marker = state / ".nobackup"
    if not marker.exists():
        marker.touch()
    log = state / "would-block.log"
    first = reason.splitlines()[0] if reason else "failed"
    with log.open("a", encoding="utf-8") as handle:
        _ = handle.write(f"Would-block {first}\n")


def _bump_failures(state: Path, session_id: str) -> int:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in session_id)
    path = state / "sessions" / (safe or "unknown")
    path.parent.mkdir(parents=True, exist_ok=True)
    marker = state / ".nobackup"
    if not marker.exists():
        marker.touch()
    current = 0
    if path.is_file():
        try:
            current = int(path.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            current = 0
    count = current + 1
    _ = path.write_text(f"{count}\n", encoding="utf-8")
    return count


def _deny(reason: str) -> int:
    _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )
    _ = sys.stderr.write(reason + "\n")
    return 2


def _block(reason: str) -> int:
    _emit({"decision": "block", "reason": reason})
    _ = sys.stderr.write(reason + "\n")
    return 2


def _fail(reason: str) -> int:
    # No stdout. Exit 2 is a deny on PreToolUse and a block on Stop for all
    # three hosts. A JSON object one of them rejects would let the turn through.
    _ = sys.stderr.write(reason + "\n")
    return 2


def _emit(payload: Mapping[str, object]) -> None:
    _ = sys.stdout.write(json.dumps(payload) + "\n")


if __name__ == "__main__":
    sys.exit(main())
