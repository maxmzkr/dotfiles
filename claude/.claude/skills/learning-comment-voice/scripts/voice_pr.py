#!/usr/bin/env python3
"""Turn a PR's description edit history into voice candidates.

GitHub attributes every edit to Max, including the ones Claude makes with
`gh pr edit`, so the editor field proves nothing. Line endings do: a body saved
from the browser comes back with CRLF, and one posted through `gh` with LF. A
CRLF version is therefore Max editing by hand, and what it adds over the version
before it is his.

Consecutive CRLF versions are one editing session, so each run of them is
compared as a whole against the last LF version before it -- the draft he was
reacting to. A run at the very start is a PR he opened in the browser, compared
against nothing.

Examples:
  voice_pr.py --repo owner/name 1234 --out /tmp/pr-candidates.json
"""

import argparse
import dataclasses
import json
import re
import subprocess
import sys

PLACEMENT = "pr-body"
LANGUAGE = "markdown"

# A paragraph that is only an uploaded screenshot carries no wording.
_IMAGE_ONLY = re.compile(r"^(<img\b[^>]*>|!\[[^\]]*\]\([^)]*\))$")


@dataclasses.dataclass(frozen=True)
class Version:
    edited_at: str
    body: str


@dataclasses.dataclass(frozen=True)
class Candidate:
    comment: str
    placement: str
    language: str
    code: str
    path: str


def _by_hand(body: str) -> bool:
    return "\r\n" in body


def paragraphs(body: str) -> list[str]:
    text = body.replace("\r\n", "\n")
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _runs(versions: list[Version]) -> list[tuple[Version | None, Version]]:
    """(base, final) for each run of hand-edited versions, oldest first."""
    ordered = sorted(versions, key=lambda v: v.edited_at)
    out = []
    base = None
    i = 0
    while i < len(ordered):
        if not _by_hand(ordered[i].body):
            base = ordered[i]
            i += 1
            continue
        while i + 1 < len(ordered) and _by_hand(ordered[i + 1].body):
            i += 1
        out.append((base, ordered[i]))
        base = ordered[i]
        i += 1
    return out


def extract(
    versions: list[Version], *, code: str, path: str
) -> tuple[list[Candidate], list[Candidate]]:
    """(voice, deleted): what Max wrote into the description, and what he cut.

    `code` is what the describing subagent sees in place of the body -- the PR
    title and changed files -- so it must not contain the description.
    """
    voice, deleted = [], []
    for base, final in _runs(versions):
        before = paragraphs(base.body) if base else []
        after = paragraphs(final.body)
        written = [p for p in after if p not in before and not _IMAGE_ONLY.match(p)]
        if written:
            voice.append(Candidate("\n\n".join(written), PLACEMENT, LANGUAGE, code, path))
        for p in before:
            if p not in after:
                deleted.append(Candidate(p, PLACEMENT, LANGUAGE, code, path))
    return voice, deleted


_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      title
      headRefOid
      files(first: 100) { nodes { path } }
      userContentEdits(first: 100) { nodes { editedAt diff } }
    }
  }
}
"""


def fetch(repo: str, number: int) -> dict:
    owner, name = repo.split("/", 1)
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={_QUERY}",
         "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)["data"]["repository"]["pullRequest"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--out", required=True, help="where to write the candidates JSON")
    ap.add_argument("number", type=int)
    args = ap.parse_args(argv)

    pr = fetch(args.repo, args.number)
    # The edit history holds the full body of each version, not a diff,
    # despite the field's name.
    versions = [Version(e["editedAt"], e["diff"] or "") for e in pr["userContentEdits"]["nodes"]]
    code = pr["title"] + "\n\n" + "\n".join(f["path"] for f in pr["files"]["nodes"])
    voice, deleted = extract(versions, code=code, path=f"#{args.number}")

    with open(args.out, "w") as fh:
        json.dump(
            {"commit": pr["headRefOid"],
             "voice": [dataclasses.asdict(c) for c in voice],
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
