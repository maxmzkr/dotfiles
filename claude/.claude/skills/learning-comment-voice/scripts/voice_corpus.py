#!/usr/bin/env python3
"""The comment-voice corpus: one JSON file per comment Max wrote.

Flat and append-only, so concurrent sessions cannot conflict. One file per record
is what makes correcting a bad capture deleting a file -- that is the whole
correction mechanism, and it needs the records to be separately readable and
separately removable, which a single append-only log would not be.

The corpus is machine-local and untracked (see DEFAULT_CORPUS below). It holds
verbatim code from every repository Max works in, so committing it anywhere would
publish that code.

Vectors are deliberately absent. They are derived from these records, and a derived
value living in the authoritative file goes stale without anyone noticing.
"""

import dataclasses
import hashlib
import json
import os
from pathlib import Path

PLACEMENTS = ("doc", "block", "trailing")
KINDS = ("why", "warning", "contract", "domain", "pointer")

STATS_NAME = "_stats.jsonl"

# Machine-local, deliberately outside the repo: the corpus accumulates verbatim
# code from every repository Max works in, so it belongs to the machine rather
# than to a dotfiles package. The skill names the path; the data is not tracked.
_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
DEFAULT_CORPUS = _DATA_HOME / "claude" / "comment-voice" / "corpus"
DEFAULT_INDEX = _DATA_HOME / "claude" / "comment-voice" / "index"


@dataclasses.dataclass(frozen=True)
class Record:
    id: str
    comment: str
    placement: str
    language: str
    kind: str
    code: str
    description: str
    enclosing: str | None
    repo: str
    path: str
    commit: str
    captured: str


def record_id(comment: str, code: str) -> str:
    digest = hashlib.sha256()
    digest.update(comment.encode())
    digest.update(b"\x00")
    digest.update(code.encode())
    return digest.hexdigest()[:16]


def write_record(rec: Record, corpus_dir: Path) -> Path:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    path = corpus_dir / f"{rec.id}.json"
    path.write_text(json.dumps(dataclasses.asdict(rec), indent=2) + "\n")
    return path


def load_records(corpus_dir: Path) -> list[Record]:
    """Every readable record. A malformed file is skipped, never raised.

    Retrieval that returns fewer exemplars is a degraded result; retrieval that
    raises takes down the skill calling it.
    """
    if not corpus_dir.is_dir():
        return []
    out = []
    for path in sorted(corpus_dir.glob("*.json")):
        try:
            out.append(Record(**json.loads(path.read_text())))
        except (ValueError, TypeError):
            continue
    return out


def append_stats(
    corpus_dir: Path,
    *,
    repo: str,
    commit: str,
    added: int,
    rewritten: int,
    deleted: int,
    captured: str,
) -> None:
    """One line per capture run.

    Comment edits per commit-walk trending down is the only evidence this system
    does anything, so the count is recorded from the first run.
    """
    corpus_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "captured": captured,
        "repo": repo,
        "commit": commit,
        "added": added,
        "rewritten": rewritten,
        "deleted": deleted,
    }
    with (corpus_dir / STATS_NAME).open("a") as fh:
        fh.write(json.dumps(row) + "\n")
