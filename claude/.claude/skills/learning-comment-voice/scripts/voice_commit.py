#!/usr/bin/env python3
"""Turn the commit messages Max reworded in a rebase into voice candidates.

Claude rewrites a message with `git commit --amend -F`, which the reflog logs as
`commit (amend)`. An interactive `reword` stop opens Max's editor and is logged
as `rebase (reword)`, so that entry is the provenance signal: what a reworded
message adds over the original commit's message is his.

Only the latest rebase session is read. Each reworded commit is paired with the
commit it rewrote by patch id, searched in the branch as it was before the
rebase started, since a reword whose parent changed has no other link back.

Examples:
  voice_commit.py --repo-dir . --out /tmp/commit-candidates.json
"""

import argparse
import dataclasses
import json
import re
import subprocess
import sys

PLACEMENT = "commit-message"
LANGUAGE = "text"

# How far back from the pre-rebase tip to look for the commit a reword rewrote.
_SEARCH_DEPTH = 500


@dataclasses.dataclass(frozen=True)
class Candidate:
    comment: str
    placement: str
    language: str
    code: str
    path: str
    commit: str


def paragraphs(message: str) -> list[str]:
    # Git drops comment lines from a message edited in the editor.
    text = "\n".join(line for line in message.splitlines() if not line.startswith("#"))
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def extract(
    before: str, after: str, *, code: str, path: str, commit: str
) -> tuple[list[Candidate], list[Candidate]]:
    """(voice, deleted): what Max wrote into the message, and what he cut.

    `code` is what the describing subagent sees in place of the message -- the
    commit's changed files -- so it must not contain the message.
    """
    old, new = paragraphs(before), paragraphs(after)
    written = [p for p in new if p not in old]
    voice = [Candidate("\n\n".join(written), PLACEMENT, LANGUAGE, code, path, commit)] if written else []
    deleted = [Candidate(p, PLACEMENT, LANGUAGE, code, path, commit) for p in old if p not in new]
    return voice, deleted


def _git(repo: str, *args: str, stdin: str | None = None) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], input=stdin, check=True, capture_output=True, text=True
    ).stdout


def _patch_ids(repo: str, rev_args: list[str]) -> dict[str, str]:
    """patch id -> commit for the commits rev_args selects."""
    patches = _git(repo, *rev_args)
    out = {}
    for line in _git(repo, "patch-id", "--stable", stdin=patches).splitlines():
        patch_id, sha = line.split()
        out.setdefault(patch_id, sha)
    return out


def rewords(repo: str) -> list[tuple[str, str]]:
    """(original, reworded) for each reword in the latest rebase, oldest first."""
    entries = [
        line.split("\x00", 1)
        for line in _git(repo, "reflog", "--format=%H%x00%gs", "HEAD").splitlines()
    ]
    reworded, before = [], None
    in_rebase = False
    for i, (sha, subject) in enumerate(entries):
        if not subject.startswith("rebase"):
            if in_rebase:
                break
            continue
        in_rebase = True
        if subject.startswith("rebase (reword)"):
            reworded.append(sha)
        if subject.startswith("rebase (start)"):
            before = entries[i + 1][0] if i + 1 < len(entries) else None
            break
    if not reworded or before is None:
        return []

    originals = _patch_ids(repo, ["log", "-p", "--format=commit %H", f"-n{_SEARCH_DEPTH}", before])
    pairs = []
    for sha in reversed(reworded):
        patch = _patch_ids(repo, ["show", "--format=commit %H", sha])
        for patch_id in patch:
            if patch_id in originals:
                pairs.append((originals[patch_id], sha))
    return pairs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-dir", default=".", help="the repository the rebase ran in")
    ap.add_argument("--out", required=True, help="where to write the candidates JSON")
    args = ap.parse_args(argv)

    voice, deleted = [], []
    for old, new in rewords(args.repo_dir):
        before = _git(args.repo_dir, "log", "-1", "--format=%B", old)
        after = _git(args.repo_dir, "log", "-1", "--format=%B", new)
        code = _git(args.repo_dir, "show", "--name-only", "--format=", new).strip()
        v, d = extract(before, after, code=code, path=new[:10], commit=new)
        voice += v
        deleted += d

    with open(args.out, "w") as fh:
        json.dump(
            {"voice": [dataclasses.asdict(c) for c in voice],
             "deleted": [dataclasses.asdict(c) for c in deleted]},
            fh, indent=2,
        )
    for label, group in (("voice", voice), ("deleted", deleted)):
        print(f"-- {label} ({len(group)}) --")
        for c in group:
            print(f"{c.path} {c.comment!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
