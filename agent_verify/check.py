"""Block unsafe tool calls and re-run the repo's typecheck recipe on stop.

The process that runs is ``git show master:agent_verify/check.py``. It reads
``agent-verify.toml`` and the justfile from ``master`` as well, so a worktree
edit of those files is not the judge.
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
_UNPARSED = "\0"
_FALLBACK_JUST = Path("/home/ntw/.local/bin/just")
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
    root = _git_root(_cwd(event))
    if root is None:
        return _fail("The hook could not find the git root.")
    try:
        profile = _load_profile(root)
    except CheckError as exc:
        return _fail(str(exc))
    kind = _event_kind(event)
    if kind == "pre":
        return _pre_tool(event, env, root, profile)
    if kind == "stop":
        return _stop(event, env, root, profile, home)
    return 0


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


def _shell_hook_reason(command: str, root: Path, hook_paths: tuple[str, ...]) -> str | None:
    prepared = _join_continuations(command)
    for segment, _sep in _split_commands(prepared):
        tokens = _tokens(segment)
        if tokens is None:
            return "The command could not be parsed, so the hook denied it."
        if not tokens:
            continue
        for target in _redirect_targets(segment):
            if _matches_hook(target, root, hook_paths):
                return f"Writes to {target} are reserved for a commit on master."
        if _is_reader(tokens):
            continue
        for token in tokens:
            if _contains_hook(token, hook_paths):
                return f"Writes to {token} are reserved for a commit on master."
    return None


def _is_reader(tokens: list[str]) -> bool:
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


def _redirect_targets(segment: str) -> list[str]:
    """File targets of unquoted redirects. Quoted ``>`` is not an operator."""
    found: list[str] = []
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
        if char == "\\":
            index += 2
            continue
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
    if depth > 8:
        return state.child() or _UNPARSED
    shell = state
    pipeline: _VenvState | None = None
    found: str | None = None
    for segment, sep in _split_commands(_join_continuations(command)):
        base = pipeline if pipeline is not None else shell
        if not segment:
            pipeline = base if sep == "|" else None
            continue
        tokens = _tokens(segment)
        if tokens is None:
            return _UNPARSED
        if _substitution(segment) and base.child():
            return base.child()
        effective = _effective_venv(tokens, base, root, depth=depth)
        if effective == _UNPARSED:
            return _UNPARSED
        if effective is not None:
            found = effective
            if _shell_expands(effective) or _outside_root(effective, root):
                return effective
        if sep == "|":
            if pipeline is None:
                pipeline = shell
            continue
        if sep != "&" and pipeline is None:
            shell = _shell_after(tokens, shell)
        pipeline = None
    return found


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
    index = 0
    while index < len(tokens):
        parsed = _assignment_parts(tokens[index])
        if parsed is not None:
            key, value, append = parsed
            if key == "UV_PROJECT_ENVIRONMENT":
                current = _apply_assignment(current, value, append=append)
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


def _shell_after(tokens: list[str], state: _VenvState) -> _VenvState:
    """Shell state after a command. Prefix assignments do not persist."""
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
        name = Path(tokens[index]).name
        if name in {"export", "unset"}:
            value, exported, index = _export_or_unset(
                name, tokens, index + 1, value, exported=exported
            )
            continue
        return state
    return _VenvState(value, exported)


def _export_or_unset(
    name: str,
    tokens: list[str],
    index: int,
    value: str,
    *,
    exported: bool,
) -> tuple[str, bool, int]:
    if name == "unset":
        while index < len(tokens) and _assignment_parts(tokens[index]) is None:
            if tokens[index].startswith("-"):
                index += 1
                continue
            if tokens[index] == "UV_PROJECT_ENVIRONMENT":
                value, exported = "", False
            else:
                break
            index += 1
        return value, exported, index
    while index < len(tokens):
        word = tokens[index]
        if word.startswith("-"):
            index += 1
            continue
        parsed = _assignment_parts(word)
        if parsed is not None:
            key, raw, append = parsed
            if key == "UV_PROJECT_ENVIRONMENT":
                base = value if append else ""
                value = _apply_assignment(base, raw, append=append)
                exported = True
            index += 1
            continue
        if word == "UV_PROJECT_ENVIRONMENT":
            exported = True
            index += 1
            continue
        break
    return value, exported, index


def _shell_expands(value: str) -> bool:
    return "$" in value or "`" in value


def _substitution(segment: str) -> bool:
    quote = ""
    index = 0
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
        elif char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if segment.startswith("$(", index) or char == "`":
            return True
        index += 1
    return False


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
    """Return the script after ``bash -c``, or None when bash runs a file."""
    cursor = index + 1
    while cursor < len(tokens):
        word = tokens[cursor]
        if word == "--" or not word.startswith("-"):
            return None
        if word == "-c":
            if cursor + 1 >= len(tokens):
                return ""
            return tokens[cursor + 1]
        if not word.startswith("--") and "c" in word[1:]:
            rest = word.split("c", 1)[1]
            if rest:
                return rest
            if cursor + 1 >= len(tokens):
                return ""
            return tokens[cursor + 1]
        cursor += 1
    return None


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
    if not value:
        return False
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
    """Split on shell separators. The second item is the separator that followed."""
    parts: list[tuple[str, str]] = []
    buf: list[str] = []
    quote = ""
    index = 0
    while index < len(command):
        char = command[index]
        if quote:
            buf.append(char)
            if char == quote and command[index - 1] != "\\":
                quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            buf.append(char)
            index += 1
            continue
        sep = ""
        if command.startswith(("&&", "||"), index):
            sep = command[index : index + 2]
        elif char == "&" and not _redirect_ampersand(command, index):
            sep = "&"
        elif char in {";", "\n", "|"}:
            sep = char
        if sep:
            parts.append(("".join(buf).strip(), sep))
            buf = []
            index += len(sep)
            continue
        buf.append(char)
        index += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append((tail, ""))
    return parts


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
    code, output = _run_recipe(root, profile, env)
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


def _run_recipe(root: Path, profile: Profile, env: Mapping[str, str]) -> tuple[int, str]:
    just = shutil.which("just")
    if just is None and _FALLBACK_JUST.is_file():
        just = str(_FALLBACK_JUST)
    if just is None:
        return 127, "just is not on PATH and /home/ntw/.local/bin/just is missing."
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
