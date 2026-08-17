#!/usr/bin/env python3
"""PreToolUse guard that keeps Claude attribution trailers out of commits.

Claude Code's own system prompt instructs the model to end commit messages with
`Co-Authored-By: Claude`. That instruction re-fires on every attempt, so unlike
`pr_body_check.py` — whose rules are matters of taste and therefore yield after
one denial — this hook denies indefinitely. There is no soft tier to spend.

Detection is deliberately blunt. For a `git commit`, the entire command string is
scanned rather than parsing the message out of it, which covers `-m`, `--trailer`,
and heredocs in one rule; `-F`/`--file` targets are additionally read off disk. A
false positive costs one rewrite, a false negative puts a trailer in history.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

# Unanchored on purpose. In a `git commit -m '...'` the trailer sits mid-line,
# after the opening quote, so a line-start anchor would miss the single most
# common vector.
COAUTHOR_RE = re.compile(r"co-?authored-by:\s*([^\n]*)", re.I)
ROBOT_RE = re.compile(r"🤖 Generated with|Generated with \[Claude Code\]", re.I)

# "Claude", "Claude Code", "Claude Opus 5 (1M context)" — the tool. A trailing
# surname means a person, so "Claude Dupont" deliberately falls through: this
# hook strips the assistant's attribution, not a colleague's.
TOOL_NAME_RE = re.compile(
    r"^claude(?:[\s\-]+(?:code|ai|assistant|opus|sonnet|haiku|fable"
    r"|\d+(?:\.\d+)*|\(.*?\)|\[.*?\]))*$",
    re.I,
)
ANTHROPIC_RE = re.compile(r"anthropic\.com", re.I)

WRITE_SUBCOMMANDS = frozenset({"commit", "merge", "revert", "cherry-pick"})
# Global options that take a separate value; the subcommand is the first bare
# token after them, so both the flag and its argument have to be stepped over.
GLOBAL_OPTS_WITH_VALUE = frozenset({
    "-C", "-c", "--git-dir", "--work-tree", "--exec-path", "--namespace",
})
MESSAGE_FLAGS = ("-m", "--message", "-F", "--file", "--trailer")
FILE_FLAGS = ("-F", "--file")

MCP_COMMIT_TOOL_RE = re.compile(
    r"^mcp__.*__(create_or_update_file|push_files|merge_pull_request)$"
)
MCP_MESSAGE_KEYS = ("message", "commit_message", "commit_title")

# shlex.split is O(n^2); a multi-megabyte command would hang the hook, and a hang
# in a PreToolUse hook matched on Bash is unrecoverable — no except routes around
# it. Real commit commands are nowhere near this.
MAX_COMMAND_CHARS = 100_000

SEGMENT_RE = re.compile(r"[\n;&|()`]+")


def _is_tool_attribution(value: str) -> bool:
    value = value.strip().strip("'\"").strip()
    if ANTHROPIC_RE.search(value):
        return True
    name = value.split("<", 1)[0].strip().strip("'\"").strip()
    return bool(name) and bool(TOOL_NAME_RE.match(name))


def has_trailer(text: str) -> bool:
    if ROBOT_RE.search(text):
        return True
    return any(_is_tool_attribution(m) for m in COAUTHOR_RE.findall(text))


def _subcommand(segment: str) -> str | None:
    tokens = segment.split()
    for i, tok in enumerate(tokens):
        if tok != "git" and not tok.endswith("/git"):
            continue
        rest = tokens[i + 1:]
        j = 0
        while j < len(rest):
            tok = rest[j]
            if tok in GLOBAL_OPTS_WITH_VALUE:
                j += 2
            elif tok.startswith("-"):
                j += 1
            else:
                return tok
        return None
    return None


def is_commit_write(command: str) -> bool:
    """True only when git is being asked to CREATE a commit.

    Membership is checked against the subcommand specifically, not against the
    command text: `git log --grep='Co-Authored-By: Claude'` is how you audit for
    the trailer, and a substring match would make this hook block its own
    diagnostics.
    """
    return any(
        _subcommand(seg) in WRITE_SUBCOMMANDS
        for seg in SEGMENT_RE.split(command)
    )


def is_message_reuse(command: str) -> bool:
    """`--amend` with no new message reuses what is already there.

    Commits that already carry the trailer are being kept deliberately; amending
    on top of one preserves a message the user chose, rather than adding a new
    attribution, so it is not this hook's business.
    """
    if "--amend" not in command.split() and "--amend" not in command:
        return False
    tokens = command.split()
    supplies_message = any(
        tok in MESSAGE_FLAGS or tok.startswith(tuple(f + "=" for f in MESSAGE_FLAGS))
        for tok in tokens
    )
    return not supplies_message


def _read(path: str) -> str:
    """Lossy decode. UnicodeDecodeError is a ValueError, not an OSError, so
    decoding strictly would escape an `except OSError` and break fail-open."""
    try:
        return Path(path).read_bytes().decode("utf-8", "replace")
    except OSError:
        return ""


def scan_text(command: str) -> str:
    """The command plus any message file it points at.

    Writing the message to a file and passing `-F` keeps the trailer out of the
    command string entirely, so scanning the command alone would miss it.
    """
    parts = [command]
    if len(command) > MAX_COMMAND_CHARS:
        return command
    try:
        tokens = shlex.split(command)
    except ValueError:
        return command
    for i, tok in enumerate(tokens):
        if tok in FILE_FLAGS and i + 1 < len(tokens):
            parts.append(_read(tokens[i + 1]))
        elif tok.startswith("--file="):
            parts.append(_read(tok.split("=", 1)[1]))
    return "\n".join(parts)


def violates(tool_name, tool_input) -> bool:
    # The payload crosses a process boundary, so the types are advisory.
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return False

    if MCP_COMMIT_TOOL_RE.match(tool_name):
        values = [tool_input.get(k) for k in MCP_MESSAGE_KEYS]
        return has_trailer("\n".join(v for v in values if isinstance(v, str)))

    if tool_name != "Bash":
        return False
    command = tool_input.get("command")
    if not isinstance(command, str):
        return False
    if not is_commit_write(command) or is_message_reuse(command):
        return False
    return has_trailer(scan_text(command))


DENIAL = (
    "This commit message carries a Claude attribution trailer "
    "(Co-Authored-By: Claude / 🤖 Generated with). Max does not want it in his "
    "history. Resubmit the commit with those lines removed — the message should "
    "end at its last real content line.\n\n"
    "This is not advisory and does not yield on retry."
)


def main() -> int:
    if os.environ.get("COMMIT_TRAILER_CHECK") == "off":
        return 0
    try:
        payload = json.loads(sys.stdin.read())
        if not violates(payload.get("tool_name"), payload.get("tool_input") or {}):
            return 0
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": DENIAL,
        }}))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
