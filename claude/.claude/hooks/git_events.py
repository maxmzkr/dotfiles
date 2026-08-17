#!/usr/bin/env python3
"""Tell Claude Code about git commands run outside the session.

Registered on UserPromptSubmit (and SessionStart, to establish a baseline), this
reports repository-level operations -- commits, pulls, pushes, rebases,
cherry-picks, checkouts, resets -- that happened since the previous turn.

Everything is read from the reflog rather than from git hooks. git already
records the name of the operation that moved each ref, so there is nothing to
install per-repo and no global core.hooksPath to override. Pushes show up
because remote-tracking refs get reflogs too.

The hook is advisory: any failure exits 0 with no output rather than disturbing
the prompt.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# How far back to look for the previous turn's reflog position.
WINDOW = 200

# Reflog fields are joined by a byte that cannot appear in either of them.
SEP = "\x1f"

# Operations whose reflog text is the commit subject, and so worth quoting.
SUBJECT_OPS = {"commit", "cherry-pick", "revert"}

SUBJECT_LIMIT = 72


def _git(repo, *args):
    """Run git, returning stdout, or None if git failed or hung."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def repo_root(cwd):
    """The top level of the repo containing `cwd`, or None if there isn't one."""
    if not cwd or not os.path.isdir(cwd):
        return None
    out = _git(cwd, "rev-parse", "--show-toplevel")
    return out.strip() or None if out else None


def _reflog(repo, ref):
    """Reflog entries for `ref`, newest first, as (sha, subject) pairs."""
    out = _git(repo, "reflog", "show", ref,
               f"--max-count={WINDOW}", f"--format=%H{SEP}%gs")
    if not out:
        return []
    entries = []
    for line in out.splitlines():
        sha, _, subject = line.partition(SEP)
        if sha:
            entries.append((sha, subject))
    return entries


def _identity(entry):
    return entry[0] + SEP + entry[1]


def _split(subject):
    """Reflog subject -> (operation, base operation, detail).

    "rebase (finish): returning to refs/heads/x" -> ("rebase (finish)", "rebase", ...)
    "merge feature: Fast-forward"                -> ("merge feature", "merge", ...)
    """
    op, _, detail = subject.partition(": ")
    base = op.split(" (")[0].split(" ")[0]
    return op, base, detail


def _branch_move(entries):
    """"main -> feature" from a run of checkout entries, or None if unparseable."""
    def endpoints(detail):
        head, sep, tail = detail.partition(" to ")
        if not sep or not head.startswith("moving from "):
            return None
        return head[len("moving from "):], tail

    first = endpoints(_split(entries[0][1])[2])
    last = endpoints(_split(entries[-1][1])[2])
    if not first or not last:
        return None
    return f"{first[0]} -> {last[1]}"


def _describe(group, before):
    """One line for a run of same-operation reflog entries, oldest first."""
    op, base, _ = _split(group[0][1])
    label = op if len(group) == 1 else base
    after = group[-1][0]

    if base == "checkout":
        move = _branch_move(group)
        if move:
            return f"{label}: {move}"

    line = f"{label}: {before[:7]} -> {after[:7]}"
    if base in SUBJECT_OPS:
        detail = _split(group[-1][1])[2].strip()
        if detail:
            line += f' "{detail[:SUBJECT_LIMIT]}"'
    if len(group) > 1:
        line += f" ({len(group)} steps)"
    return line


def _head_lines(repo, marker, head):
    """Lines for HEAD movement since `marker`, plus the new anchor entry."""
    entries = _reflog(repo, "HEAD")
    anchor = marker.get("head_top") if marker else None
    top = _identity(entries[0]) if entries else None

    if marker is None:
        return [], top

    fresh = entries
    if anchor is not None:
        position = next(
            (i for i, e in enumerate(entries) if _identity(e) == anchor), None
        )
        if position is None:
            # The anchor fell out of the reflog: expired, or the entries it
            # pointed at were rewritten. Replaying the window would be a lie
            # about what just happened, so say only what is certain.
            if head and head != marker.get("head"):
                return [
                    f"history rewritten: HEAD is now {head[:7]} "
                    f"(previous position {str(marker.get('head'))[:7]} "
                    "is no longer in the reflog)"
                ], top
            return [], top
        fresh = entries[:position]

    if not fresh:
        return [], top

    # Oldest first, so the lines read in the order the operations happened. Each
    # entry's "before" sha is the entry preceding it, which is why the anchor
    # entry is kept out of `fresh` but its sha stays available as a predecessor.
    # Index, not sha: checkouts revisit shas, so shas are not unique keys.
    fresh = list(reversed(fresh))
    before = [marker.get("head", "")] + [e[0] for e in fresh[:-1]]

    lines, start = [], 0
    for i in range(1, len(fresh) + 1):
        ends = i == len(fresh) or (
            _split(fresh[i][1])[1] != _split(fresh[start][1])[1]
        )
        if ends:
            lines.append(_describe(fresh[start:i], before[start]))
            start = i
    return lines, top


def _remote_tips(repo):
    out = _git(repo, "for-each-ref", "--format=%(refname)%09%(objectname)",
               "refs/remotes")
    if not out:
        return {}
    tips = {}
    for line in out.splitlines():
        ref, _, sha = line.partition("\t")
        if ref and sha:
            tips[ref] = sha
    return tips


def _remote_verb(repo, ref):
    """Whether the newest update to a remote-tracking ref was a push or a fetch."""
    entries = _reflog(repo, ref)
    subject = entries[0][1] if entries else ""
    if "push" in subject:
        return "push"
    if "fetch" in subject or "pull" in subject:
        return "fetch"
    return "update"


def _remote_lines(repo, marker, tips):
    if marker is None:
        return []
    was = marker.get("remotes") or {}
    lines = []
    for ref, sha in sorted(tips.items()):
        short = ref[len("refs/remotes/"):]
        if ref not in was:
            lines.append(f"{_remote_verb(repo, ref)}: {short} -> {sha[:7]} (new)")
        elif was[ref] != sha:
            lines.append(
                f"{_remote_verb(repo, ref)}: {short} "
                f"{was[ref][:7]} -> {sha[:7]}"
            )
    for ref in sorted(set(was) - set(tips)):
        lines.append(f"deleted: {ref[len('refs/remotes/'):]}")
    return lines


def collect(repo, marker):
    """Events since `marker`, and the marker to store for next time.

    A `marker` of None means this is the first look at the repo in this session:
    record the current position and report nothing, so a fresh session does not
    open with a dump of yesterday's work. Returns ([], None) if `repo` is not a
    git repository.
    """
    root = repo_root(repo)
    if root is None:
        return [], None

    head = (_git(root, "rev-parse", "HEAD") or "").strip()
    branch = (_git(root, "symbolic-ref", "--quiet", "--short", "HEAD") or "").strip()
    tips = _remote_tips(root)

    lines, top = _head_lines(root, marker, head)
    lines += _remote_lines(root, marker, tips)

    return lines, {
        "repo": root,
        "head": head,
        "branch": branch or "(detached)",
        "head_top": top,
        "remotes": tips,
    }


def format_block(repo, lines, marker):
    if not lines:
        return ""
    branch = (marker or {}).get("branch", "")
    body = "\n".join(lines)
    return (
        f'<git-activity repo="{repo}" branch="{branch}">\n'
        f"{body}\n"
        "</git-activity>"
    )


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "claude" / "git-events"


def marker_path(base, session_id, repo):
    digest = hashlib.sha1(str(repo).encode()).hexdigest()[:16]
    return Path(base) / str(session_id) / f"{digest}.json"


def load_marker(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def save_marker(path, marker):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(marker))
    tmp.replace(path)


def main():
    payload = json.loads(sys.stdin.read() or "{}")
    cwd = payload.get("cwd") or os.getcwd()
    event = payload.get("hook_event_name") or "UserPromptSubmit"
    session = payload.get("session_id") or "default"

    root = repo_root(cwd)
    if root is None:
        return

    path = marker_path(cache_dir(), session, root)
    lines, marker = collect(root, load_marker(path))
    if marker is None:
        return
    save_marker(path, marker)

    block = format_block(root, lines, marker)
    if block:
        json.dump({"hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": block,
        }}, sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # A hook that breaks the prompt is worse than a hook that says nothing.
        pass
    sys.exit(0)
