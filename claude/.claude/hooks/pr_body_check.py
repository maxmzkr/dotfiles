#!/usr/bin/env python3
"""PreToolUse guard that keeps miserable PR bodies off GitHub.

Hard violations are objective facts about the text (a leftover template stub is
never correct) and deny every time. Soft violations are matters of taste; they
deny once, attach the rubric, then yield so a heuristic can never wedge a
legitimate PR.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

HARD = "hard"
SOFT = "soft"

SKILL_PATH = "/home/max/.claude/skills/writing-pr-descriptions/SKILL.md"


@dataclass(frozen=True)
class Violation:
    kind: str
    code: str
    detail: str


FENCE_RE = re.compile(r"^```.*?^```", re.S | re.M)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
HEADING_RE = re.compile(r"^##\s+.*$", re.M)
SECTION_RE = HEADING_RE
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$", re.M)
CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]", re.M)
CHECKBOX_BODY_RE = re.compile(r"^\[[ xX]\]")
SUMMARY_RE = re.compile(r"^##\s*Summary\b", re.M | re.I)
ROBOT_RE = re.compile(r"🤖 Generated with|Co-Authored-By:\s*Claude", re.I)
THIS_PR_RE = re.compile(r"^(This PR|This change|This commit)\b", re.I)

CHANGE_VERB_RE = re.compile(
    r"^(?:Add|Adds|Added|Rename|Renames|Renamed|Update|Updates|Updated"
    r"|Remove|Removes|Removed|Replace|Replaces|Replaced|Move|Moves|Moved"
    r"|Introduce|Introduces|Switch|Switches|Switched|Refactor|Refactors"
    r"|Bump|Bumps|Delete|Deletes|Deleted|Transfer|Transfers|Transferred"
    r"|Keep|Keeps|Wire|Wires|Expose|Exposes|Extract|Extracts)\b"
)
PATHY_RE = re.compile(
    r"`[^`]+`"
    # A letter is required on each side of the slash; \w alone made "3/4" and
    # "50/100" read as paths.
    r"|\b[\w.-]*[A-Za-z][\w.-]*/[\w./-]*[A-Za-z][\w./-]*\b"
    r"|\b\w+\.(?:go|py|ts|tsx|yaml|yml|json|proto|md|scala|sql|sh)\b"
)
REGISTER_WORDS = ("Notably", "Additionally", "comprehensive")

DIFF_RESTATEMENT_RATIO = 0.6
MIN_BULLETS_FOR_INVENTORY = 3
MIN_CHECKBOXES_FOR_TEST_PLAN = 2


def normalize(text: str) -> str:
    """GitHub hands back CRLF for many bodies; every ^/$ anchor below assumes LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_fences(text: str) -> str:
    return FENCE_RE.sub("", text)


def strip_comments(text: str) -> str:
    return COMMENT_RE.sub("", text)


def _leading_section_empty(text: str) -> bool:
    first = HEADING_RE.search(text)
    if not first:
        return False
    nxt = HEADING_RE.search(text, first.end())
    segment = text[first.end(): nxt.start() if nxt else len(text)]
    return not segment.strip()


def hard_violations(body: str) -> list[Violation]:
    body = normalize(body)
    found: list[Violation] = []
    # Fenced content is exempt: hard violations deny indefinitely with no yield, so
    # a body legitimately demonstrating HTML comment syntax must not be trapped.
    if "<!--" in strip_fences(body):
        found.append(Violation(
            HARD, "template_stub",
            "The body still contains <!-- --> template stubs. Delete every heading "
            "and comment you did not fill in — the template is a starting point, "
            "not a form.",
        ))
    text = strip_comments(body).strip()
    if not text:
        found.append(Violation(HARD, "empty_body", "The body is empty."))
        return found
    if _leading_section_empty(text):
        found.append(Violation(
            HARD, "empty_leading_section",
            "The first ## section is empty. Open with the problem — what was wrong, "
            "missing, or newly required — not an empty heading.",
        ))
    return found


def _first_sentence(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(">"):
            continue
        return re.split(r"(?<=[.!?])\s", stripped, maxsplit=1)[0]
    return ""


def _prose_bullets(text: str) -> list[str]:
    return [
        b.strip() for b in BULLET_RE.findall(text)
        if not CHECKBOX_BODY_RE.match(b.strip())
    ]


def _sections(text: str) -> list[str]:
    """A change inventory is a localized block, so score bullets per section.

    #25881's Technical Changes list is 6 of 7 verb-plus-path, but its How-to-Test
    commands, verification notes, and ticket ID dilute the whole-body ratio to
    6 of 18 — under any threshold worth having. Scoping to the section catches it
    without lowering the bar.
    """
    starts = [m.start() for m in SECTION_RE.finditer(text)]
    bounds = [0, *starts, len(text)]
    return [text[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]


def soft_violations(body: str) -> list[Violation]:
    body = normalize(body)
    text = strip_comments(strip_fences(body))
    found: list[Violation] = []

    if SUMMARY_RE.search(text):
        found.append(Violation(
            SOFT, "summary_heading",
            "A '## Summary' heading. That is the shape of a change log, not a "
            "problem statement.",
        ))

    if len(CHECKBOX_RE.findall(text)) >= MIN_CHECKBOXES_FOR_TEST_PLAN:
        found.append(Violation(
            SOFT, "checkbox_test_plan",
            "A checkbox test plan. Show the evidence that the change works, or say "
            "nothing — unchecked boxes tell a reviewer nothing.",
        ))

    if ROBOT_RE.search(body):
        found.append(Violation(
            SOFT, "robot_trailer",
            "A Claude attribution trailer. Remove it.",
        ))

    if THIS_PR_RE.match(_first_sentence(text)):
        found.append(Violation(
            SOFT, "this_pr_opener",
            "Opens with 'This PR…'. These get read in list views, so the first "
            "sentence has to state the problem and stand on its own out of context.",
        ))

    for section in _sections(text):
        bullets = _prose_bullets(section)
        if len(bullets) < MIN_BULLETS_FOR_INVENTORY:
            continue
        inventory = [
            b for b in bullets
            if CHANGE_VERB_RE.match(b) and PATHY_RE.search(b)
        ]
        if len(inventory) / len(bullets) >= DIFF_RESTATEMENT_RATIO:
            found.append(Violation(
                SOFT, "diff_restatement",
                f"{len(inventory)} of {len(bullets)} bullets in one section are a "
                "change inventory (a verb plus a path or identifier). That is the "
                "diff restated — the reviewer already has it. Say what problem this "
                "solves instead.",
            ))
            break

    hits = [w for w in REGISTER_WORDS if re.search(rf"\b{w}\b", text, re.I)]
    if hits:
        found.append(Violation(
            SOFT, "register_words",
            f"Design-doc register: {', '.join(hits)}. Would you say this out loud to "
            "a teammate?",
        ))

    return found


# --- Extraction -------------------------------------------------------------

import json
import shlex
from pathlib import Path

# Anchored at a command position, not anywhere in the string: a script that merely
# mentions a gh PR write in a comment or a docstring is not a PR write, and treating
# it as one lets the hook hard-deny ordinary shell work.
_CMD_START = r"(?:^|[\n;&|(]|\$\()\s*"
GH_PR_CREATE_RE = re.compile(_CMD_START + r"gh\s+pr\s+create\b", re.M)
GH_PR_EDIT_RE = re.compile(_CMD_START + r"gh\s+pr\s+edit\b", re.M)
GH_API_RE = re.compile(_CMD_START + r"gh\s+api\b", re.M)
PATCH_RE = re.compile(r"--method\s+PATCH\b")
MAX_COMMAND_CHARS = 100_000
# The heredoc must belong to the body flag itself. Matching any heredoc whenever
# "--body" appeared somewhere in the command captured the wrong text: a chained
# command handed an unrelated inline script to the validator as though it were the
# PR body, and a stray comment marker in that script then hard-denied the call.
# Unrecognized shapes fall through to shlex and then to None, which is fail-open.
HEREDOC_RE = re.compile(
    r"--body(?:\s|=)+[\"']?\$\(\s*cat\s*<<-?\s*'?(\w+)'?\r?\n(.*?)\r?\n\s*\1",
    re.S,
)
MCP_PR_TOOL_RE = re.compile(r"^mcp__.*__(create|update)_pull_request$")


def is_pr_write(command: str) -> bool:
    if GH_PR_CREATE_RE.search(command):
        return True
    if GH_PR_EDIT_RE.search(command) and "--body" in command:
        return True
    if (GH_API_RE.search(command) and PATCH_RE.search(command)
            and "/pulls/" in command):
        return True
    return False


def _read(path: str) -> str | None:
    """Lossy on purpose. Path.read_text() raises UnicodeDecodeError on non-UTF-8
    input, and UnicodeDecodeError is a ValueError — not an OSError — so an
    `except OSError` here would let it escape and break fail-open. Replacing bad
    bytes also beats returning None: a body pasted out of Word still gets judged
    instead of skipping the check entirely.
    """
    try:
        return Path(path).read_bytes().decode("utf-8", "replace")
    except OSError:
        return None


def body_from_command(command: str) -> str | None:
    """Best-effort body extraction. None means 'do not judge this call'."""
    heredoc = HEREDOC_RE.search(command)
    if heredoc:
        return heredoc.group(2)

    # Guard on the command string, not on body length: shlex.split is O(n^2) and
    # a multi-megabyte --body value takes tens of seconds. A hang is worse than a
    # crash here — no except can route around it. GitHub caps PR bodies at 65,536
    # characters, so this ceiling never fires on a real call.
    if len(command) > MAX_COMMAND_CHARS:
        return None

    try:
        tokens = shlex.split(command)
    except ValueError:
        return None

    for i, tok in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None

        # Checked before --body-file because `gh api` spells --field as -F, and
        # `gh api --method PATCH ... -F body=` is the documented way to edit a PR
        # body in this repo (gh pr edit is broken here). Treating -F as a file
        # path first left every body EDIT unchecked.
        if (tok in ("-f", "-F", "--field", "--raw-field")
                and nxt and nxt.startswith("body=")):
            value = nxt.split("=", 1)[1]
            return _read(value[1:]) if value.startswith("@") else value

        if tok in ("--body-file", "-F") and nxt:
            return _read(nxt)
        if tok.startswith("--body-file="):
            return _read(tok.split("=", 1)[1])

        if tok == "--input" and nxt:
            raw = _read(nxt)
            if raw is None:
                return None
            try:
                return json.loads(raw).get("body")
            except (ValueError, AttributeError):
                return None

        if tok in ("--body", "-b") and nxt:
            return nxt
        if tok.startswith("--body="):
            return tok.split("=", 1)[1]

    return None


def extract_body(tool_name: str, tool_input: dict) -> str | None:
    # The payload comes from outside this process; the type hints are not enforced.
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return None
    if MCP_PR_TOOL_RE.match(tool_name):
        body = tool_input.get("body")
        return body if isinstance(body, str) else None
    if tool_name != "Bash":
        return None
    command = tool_input.get("command", "")
    if not isinstance(command, str) or not is_pr_write(command):
        return None
    body = body_from_command(command)
    return body if isinstance(body, str) else None


# --- Decision ---------------------------------------------------------------

import os
import subprocess
import sys

RUBRIC_REMINDER = (
    "The body's job is to supply what the diff cannot: the problem, and only the "
    "context a reviewer needs to judge whether this is the right change. Cut any "
    "sentence recoverable from the diff. Link the ticket instead of restating it."
)


@dataclass(frozen=True)
class Decision:
    action: str  # "allow" | "deny" | "advise"
    message: str
    reset: bool
    soft_denied: bool


def format_message(hard: list[Violation], soft: list[Violation],
                   blocking: bool) -> str:
    lines = []
    if blocking:
        lines.append("PR body check — redraft before resubmitting.")
    else:
        lines.append("PR body check — advisory only, the call was allowed.")
    if hard:
        lines.append("")
        lines.append("BLOCKING:")
        lines += [f"  • {v.code}: {v.detail}" for v in hard]
    if soft:
        lines.append("")
        lines.append("ADVISORY:")
        lines += [f"  • {v.code}: {v.detail}" for v in soft]
    lines += ["", RUBRIC_REMINDER, "", f"Rubric and examples: {SKILL_PATH}"]
    return "\n".join(lines)


def decide(body: str, attempts: int) -> Decision:
    hard = hard_violations(body)
    soft = soft_violations(body)
    if not hard and not soft:
        return Decision("allow", "", reset=True, soft_denied=False)
    if hard:
        # A hard denial must not touch the soft counter. The soft tier owes every
        # draft exactly one deny; spending it on an unrelated hard failure would
        # let a diff-restatement body through the first time it is ever seen.
        return Decision("deny", format_message(hard, soft, blocking=True),
                        reset=False, soft_denied=False)
    if attempts >= 1:
        return Decision("advise", format_message(hard, soft, blocking=False),
                        reset=True, soft_denied=False)
    return Decision("deny", format_message(hard, soft, blocking=True),
                    reset=False, soft_denied=True)


# --- State ------------------------------------------------------------------

def _git(cwd: str, *args: str) -> str | None:
    try:
        out = subprocess.run(("git", *args), cwd=cwd, capture_output=True,
                             text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def state_path(cwd: str) -> Path | None:
    common = _git(cwd, "rev-parse", "--git-common-dir")
    if not common:
        return None
    base = Path(common)
    if not base.is_absolute():
        base = Path(cwd) / base
    return base / "pr-body-check-attempts"


def current_branch(cwd: str) -> str:
    return _git(cwd, "rev-parse", "--abbrev-ref", "HEAD") or "HEAD"


def read_attempts(path: Path | None, branch: str) -> int:
    if path is None:
        return 0
    try:
        data = json.loads(path.read_text())
        return int(data.get(branch, 0))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def write_attempts(path: Path | None, branch: str, count: int) -> None:
    if path is None:
        return
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    if count:
        data[branch] = count
    else:
        data.pop(branch, None)
    try:
        path.write_text(json.dumps(data))
    except OSError:
        pass


# --- Hook entry point -------------------------------------------------------

def main() -> int:
    if os.environ.get("PR_BODY_CHECK") == "off":
        return 0
    try:
        payload = json.loads(sys.stdin.read())
        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input") or {}
        cwd = payload.get("cwd") or os.getcwd()
        body = extract_body(tool_name, tool_input)
    except Exception:
        return 0
    if not body:
        return 0

    try:
        path = state_path(cwd)
        branch = current_branch(cwd)
        attempts = read_attempts(path, branch)
        decision = decide(body, attempts)
        if decision.reset:
            write_attempts(path, branch, 0)
        elif decision.soft_denied:
            write_attempts(path, branch, attempts + 1)

        if decision.action == "allow":
            return 0
        out = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
        if decision.action == "deny":
            out["hookSpecificOutput"]["permissionDecision"] = "deny"
            out["hookSpecificOutput"]["permissionDecisionReason"] = decision.message
        else:
            # No permissionDecision on the advisory path. "allow" BYPASSES the
            # normal approval prompt, and this user requires per-PR authorization
            # for `pr create` and `pr edit`. An advisory must add information,
            # never remove a gate.
            out["hookSpecificOutput"]["additionalContext"] = decision.message
            out["systemMessage"] = decision.message
        print(json.dumps(out))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
