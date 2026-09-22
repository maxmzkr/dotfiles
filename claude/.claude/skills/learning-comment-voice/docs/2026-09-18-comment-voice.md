# Comment Voice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture the comments Max writes by hand during an interactive commit walk into a machine-local corpus, and serve relevant exemplars back to Claude before it writes or rewrites a comment.

**Architecture:** A work-private skill extracts comment hunks from the diff of Max's hand edits and writes one JSON record per comment. A query CLI filters those records by mechanical facets and returns exemplars, using a full-corpus backend while the corpus is small and swapping to vector similarity once it outgrows the context window. Capture and query never call each other; they meet at the corpus directory on disk.

**Tech Stack:** Python 3.12, standard library only for the core path. `numpy` and `sentence-transformers` are optional and gated behind an availability check — neither is installed on this machine today, and the core must work without them. Tests use stdlib `unittest`.

**Spec:** `claude/.claude/skills/learning-comment-voice/docs/2026-09-18-comment-voice-design.md`

## Global Constraints

- All new files live under `claude/.claude/skills/learning-comment-voice/`, which is **public**. Nothing in this feature is work-private.
- **The corpus is not in the repository.** It lives at `~/.local/share/claude/comment-voice/`, untracked, because it accumulates verbatim code from every repo Max works in. The skill names the path; the data at that path belongs to the machine. Never add a corpus directory, a `.gitkeep`, or a sample record to the repo.
- Exactly one work-private file is touched, in Task 9: `claudework/.claude/skills/review-comments/SKILL.md`. Every other changed path is public.
- The core path (`voice_corpus.py`, `voice_extract.py`, `voice_query.py`) is **standard library only**. `numpy` and `sentence-transformers` may be imported only inside `voice_vectors.py` and `voice_index.py`, and only lazily.
- Every consumer path degrades to today's behavior on failure: missing corpus, missing index, absent dependency, and empty result all return nothing rather than raising.
- Claude's original comment text is **never** stored in a record.
- Vectors are **never** stored in a record. They are derived, and live only in the index.
- Tests use stdlib `unittest`, no pytest. Each test builds the data its own assertions depend on; there is deliberately no shared corpus fixture, so a check's input reads next to the assertion about it.
- Run tests with `python3 -m unittest discover` from the `scripts/` directory.
- Commit messages must not carry a Claude attribution trailer (`~/.claude/CLAUDE.md`; `commit_trailer_check.py` enforces it as a hard deny).

---

## File Structure

```
claude/.claude/skills/learning-comment-voice/     (in the repo, public)
  SKILL.md                      capture procedure + query trigger
  docs/                         the spec and this plan
  scripts/
    voice_corpus.py             record schema, read/write, stats     (stdlib)
    voice_extract.py            unified diff -> comment candidates   (stdlib)
    voice_query.py              CLI: facets + backend dispatch       (stdlib)
    voice_vectors.py            embedding + cosine ranking           (optional deps)
    voice_index.py              index builder CLI                    (optional deps)
    test_voice_corpus.py
    test_voice_extract.py
    test_voice_query.py
    test_voice_vectors.py

~/.local/share/claude/comment-voice/               (untracked, machine-local)
  corpus/*.json                 one record per comment
  corpus/_stats.jsonl           one line per capture run
  index/vectors.npz             derived, rebuildable
```

Responsibilities are split so the two files carrying optional dependencies are the only ones that can fail to import. `voice_extract.py` holds all the diff-parsing logic and is the largest pure-function surface, so it is tested hardest.

---

### Task 1: Record schema and corpus store

**Files:**
- Create: `claude/.claude/skills/learning-comment-voice/scripts/voice_corpus.py`
- Create: `claude/.claude/skills/learning-comment-voice/scripts/test_voice_corpus.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Record` dataclass with fields `id, comment, placement, language, kind, code, description, enclosing, repo, path, commit, captured` (all `str`, `enclosing` is `str | None`)
  - `record_id(comment: str, code: str) -> str`
  - `write_record(rec: Record, corpus_dir: Path) -> Path`
  - `load_records(corpus_dir: Path) -> list[Record]`
  - `append_stats(corpus_dir: Path, *, repo: str, commit: str, added: int, rewritten: int, deleted: int, captured: str) -> None`
  - `PLACEMENTS = ("doc", "block", "trailing")`, `KINDS = ("why", "warning", "contract", "domain", "pointer")`
  - `DEFAULT_CORPUS: Path` and `DEFAULT_INDEX: Path` under `$XDG_DATA_HOME/claude/comment-voice/`, defined here once and imported by `voice_query` and `voice_index` rather than restated in each

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for voice_corpus."""

import json
import tempfile
import unittest
from pathlib import Path

import voice_corpus as vc


def a_record(**over) -> vc.Record:
    """A complete record; each test overrides only what it asserts on."""
    fields = dict(
        comment="// The Failed condition is set only once backoffLimit is spent.",
        placement="block",
        language="go",
        kind="why",
        code="if cond.Type == batchv1.JobFailed {",
        description="a job-watch loop branching on a terminal condition",
        enclosing="watchJob",
        repo="widgets",
        path="services/foo/watch.go",
        commit="30c403aabd",
        captured="2026-09-18",
    )
    fields.update(over)
    fields["id"] = vc.record_id(fields["comment"], fields["code"])
    return vc.Record(**fields)


class TestRecordID(unittest.TestCase):
    def test_id_is_stable_for_same_comment_and_code(self):
        self.assertEqual(vc.record_id("// a", "x := 1"), vc.record_id("// a", "x := 1"))

    def test_id_differs_when_code_differs(self):
        self.assertNotEqual(vc.record_id("// a", "x := 1"), vc.record_id("// a", "y := 2"))


class TestRoundTrip(unittest.TestCase):
    def test_written_record_loads_back_identical(self):
        rec = a_record()
        with tempfile.TemporaryDirectory() as d:
            vc.write_record(rec, Path(d))
            self.assertEqual([rec], vc.load_records(Path(d)))

    def test_file_is_named_for_the_record_id(self):
        rec = a_record()
        with tempfile.TemporaryDirectory() as d:
            path = vc.write_record(rec, Path(d))
            self.assertEqual(rec.id + ".json", path.name)

    def test_no_vector_field_is_persisted(self):
        rec = a_record()
        with tempfile.TemporaryDirectory() as d:
            path = vc.write_record(rec, Path(d))
            stored = json.loads(path.read_text())
        self.assertNotIn("vector", stored)
        self.assertNotIn("desc_vector", stored)


class TestLoadIsForgiving(unittest.TestCase):
    def test_missing_corpus_dir_loads_as_empty(self):
        self.assertEqual([], vc.load_records(Path("/nonexistent/corpus")))

    def test_unparseable_file_is_skipped_not_raised(self):
        good = a_record()
        with tempfile.TemporaryDirectory() as d:
            vc.write_record(good, Path(d))
            (Path(d) / "broken.json").write_text("{not json")
            self.assertEqual([good], vc.load_records(Path(d)))

    def test_stats_file_is_not_loaded_as_a_record(self):
        with tempfile.TemporaryDirectory() as d:
            vc.append_stats(
                Path(d), repo="widgets", commit="abc", added=1,
                rewritten=2, deleted=3, captured="2026-09-18",
            )
            self.assertEqual([], vc.load_records(Path(d)))


class TestStats(unittest.TestCase):
    def test_runs_append_rather_than_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            for n in (1, 2):
                vc.append_stats(
                    Path(d), repo="widgets", commit=f"sha{n}", added=n,
                    rewritten=0, deleted=0, captured="2026-09-18",
                )
            lines = (Path(d) / "_stats.jsonl").read_text().strip().split("\n")
        self.assertEqual(["sha1", "sha2"], [json.loads(l)["commit"] for l in lines])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_corpus -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice_corpus'`

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_corpus -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add claude/.claude/skills/learning-comment-voice/
git commit -m "Add the comment-voice corpus store

One JSON file per comment, flat and append-only. Vectors are derived and
live in the index, never in the record."
```

---

### Task 2: Extract comment candidates from a diff

**Files:**
- Create: `claude/.claude/skills/learning-comment-voice/scripts/voice_extract.py`
- Create: `claude/.claude/skills/learning-comment-voice/scripts/test_voice_extract.py`

**Interfaces:**
- Consumes: `PLACEMENTS` from `voice_corpus`.
- Produces:
  - `Candidate` dataclass: `comment: str`, `placement: str`, `language: str`, `code: str`, `path: str`
  - `language_for(path: str) -> str | None`
  - `extract(diff_text: str) -> tuple[list[Candidate], list[Candidate]]` returning `(voice, deleted)`

The split is the spec's rule 2: comments Max **added or rewrote** are voice, comments he **deleted** are evidence for `rules.md`. A rewritten comment appears as both a `-` and a `+` line in the same hunk; the `+` side wins and the `-` side is dropped, so a rewrite is counted once, as voice.

`code` is the hunk's post-image (context and `+` lines) with every comment line removed. That stripping is what makes the comment-blind description in Task 6 possible.

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for voice_extract.

Each test writes the diff its assertions depend on. Diffs are built by a helper
that supplies only the headers, because the headers are noise in every assertion
here and the hunk body is the subject of all of them.
"""

import unittest

import voice_extract as ve


def diff(path: str, body: str) -> str:
    """A one-file, one-hunk unified diff. `body` lines carry their own +/-/space."""
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1,3 +1,4 @@\n"
        f"{body}\n"
    )


def comments(cands) -> list[str]:
    return [c.comment for c in cands]


class TestLanguage(unittest.TestCase):
    def test_go_file(self):
        self.assertEqual("go", ve.language_for("services/foo/watch.go"))

    def test_python_file(self):
        self.assertEqual("python", ve.language_for("scripts/run.py"))

    def test_unknown_extension_has_no_language(self):
        self.assertIsNone(ve.language_for("README.unknownext"))


class TestAddedComments(unittest.TestCase):
    def test_an_added_comment_is_voice(self):
        voice, deleted = ve.extract(diff("a.go", "+// backoff cap tracks the upstream timeout\n x := 1"))
        self.assertEqual(["// backoff cap tracks the upstream timeout"], comments(voice))
        self.assertEqual([], deleted)

    def test_a_deleted_comment_is_not_voice(self):
        voice, deleted = ve.extract(diff("a.go", "-// increment the counter\n x := 1"))
        self.assertEqual([], voice)
        self.assertEqual(["// increment the counter"], comments(deleted))

    def test_a_rewrite_counts_once_as_voice(self):
        voice, deleted = ve.extract(
            diff("a.go", "-// old text\n+// new text\n x := 1")
        )
        self.assertEqual(["// new text"], comments(voice))
        self.assertEqual([], deleted, "the replaced comment is not separate evidence")


class TestPlacement(unittest.TestCase):
    def test_comment_after_code_on_the_same_line_is_trailing(self):
        voice, _ = ve.extract(diff("a.go", "+x := 1 // seconds, not millis"))
        self.assertEqual("trailing", voice[0].placement)
        self.assertEqual("// seconds, not millis", voice[0].comment)

    def test_comment_above_a_declaration_is_doc(self):
        voice, _ = ve.extract(diff("a.go", "+// Watch blocks until the job settles.\n+func Watch() error {"))
        self.assertEqual("doc", voice[0].placement)

    def test_comment_above_a_statement_is_block(self):
        voice, _ = ve.extract(diff("a.go", "+// the API replays these in sequence\n+order = append(order, id)"))
        self.assertEqual("block", voice[0].placement)


class TestCodeContext(unittest.TestCase):
    def test_code_excludes_the_comment_itself(self):
        voice, _ = ve.extract(diff("a.go", "+// why this is here\n+x := compute()\n y := 2"))
        self.assertNotIn("why this is here", voice[0].code)

    def test_code_includes_context_lines_not_just_added_ones(self):
        voice, _ = ve.extract(diff("a.go", "+// why this is here\n+x := compute()\n y := 2"))
        self.assertIn("y := 2", voice[0].code)

    def test_code_excludes_removed_lines(self):
        voice, _ = ve.extract(diff("a.go", "+// why this is here\n-x := old()\n+x := compute()"))
        self.assertNotIn("old()", voice[0].code)


class TestMultipleLanguages(unittest.TestCase):
    def test_python_hash_comment_is_found(self):
        voice, _ = ve.extract(diff("run.py", "+# the vendor returns 200 on failure\n+check(resp)"))
        self.assertEqual(["# the vendor returns 200 on failure"], comments(voice))

    def test_a_hash_inside_a_string_is_not_a_comment(self):
        voice, _ = ve.extract(diff("run.py", '+colour = "#ff0000"'))
        self.assertEqual([], voice)

    def test_a_url_in_go_code_is_not_a_comment(self):
        voice, _ = ve.extract(diff("a.go", '+u := "https://example.com/x"'))
        self.assertEqual([], voice)


class TestFilesWithoutLanguage(unittest.TestCase):
    def test_unknown_extension_yields_nothing(self):
        voice, deleted = ve.extract(diff("notes.unknownext", "+// looks like a comment"))
        self.assertEqual([], voice)
        self.assertEqual([], deleted)


class TestMultipleFiles(unittest.TestCase):
    def test_each_file_keeps_its_own_path_and_language(self):
        text = diff("a.go", "+// go comment\n x := 1") + diff("run.py", "+# py comment\n y = 2")
        voice, _ = ve.extract(text)
        self.assertEqual(
            [("a.go", "go"), ("run.py", "python")],
            sorted((c.path, c.language) for c in voice),
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_extract -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice_extract'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Turn a unified diff of Max's hand edits into comment candidates.

The diff produced at an interactive-rebase stop, after Max says he is done, is by
construction his own work. That is the entire provenance argument -- there is no
journal of what Claude wrote and no line-number anchoring, because the hunks are
the evidence.

Two outputs, because they feed different places: comments added or rewritten are
voice, comments deleted are evidence for the review-comments rulebook. A comment
he removed says nothing about how he writes.
"""

import dataclasses
import re

LINE_COMMENT = {
    "go": "//",
    "python": "#",
    "rust": "//",
    "javascript": "//",
    "typescript": "//",
    "c": "//",
    "cpp": "//",
    "java": "//",
    "lua": "--",
    "sql": "--",
    "sh": "#",
    "yaml": "#",
    "ruby": "#",
    "terraform": "#",
}

EXTENSIONS = {
    ".go": "go",
    ".py": "python",
    ".rs": "rust",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".java": "java",
    ".lua": "lua",
    ".sql": "sql",
    ".sh": "sh",
    ".bash": "sh",
    ".zsh": "sh",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".rb": "ruby",
    ".tf": "terraform",
}

# A declaration is what makes a preceding comment a doc comment rather than an
# aside. Deliberately shallow: the cost of a wrong guess is a mislabelled facet,
# and facets only filter.
DECLARATION = re.compile(
    r"^\s*("
    r"func\b|type\b|var\b|const\b"            # go
    r"|def\b|class\b|async\s+def\b"           # python
    r"|fn\b|struct\b|enum\b|trait\b|impl\b"   # rust
    r"|export\b|function\b|interface\b"       # js/ts
    r"|public\b|private\b|protected\b"        # java
    r"|local\s+function\b"                    # lua
    r")"
)


@dataclasses.dataclass(frozen=True)
class Candidate:
    comment: str
    placement: str
    language: str
    code: str
    path: str


def language_for(path: str) -> str | None:
    for ext, lang in EXTENSIONS.items():
        if path.endswith(ext):
            return lang
    return None


def _split_comment(line: str, marker: str) -> tuple[str, str] | None:
    """(code_before, comment) for `line`, or None when it holds no comment.

    Scans character by character tracking quote state, because the cheap test --
    does the marker appear -- fires on `"#ff0000"` and on every URL in Go source.
    """
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'`":
            quote = ch
        elif line.startswith(marker, i):
            return line[:i], line[i:].rstrip()
        i += 1
    return None


def _placement(code_before: str, following: list[str]) -> str:
    if code_before.strip():
        return "trailing"
    for line in following:
        if not line.strip():
            continue
        return "doc" if DECLARATION.match(line) else "block"
    return "block"


def _file_chunks(diff_text: str) -> list[tuple[str, list[str]]]:
    """(path, body lines) per file. Hunk headers are dropped; only +/-/space remain."""
    chunks: list[tuple[str, list[str]]] = []
    path: str | None = None
    body: list[str] = []
    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            if path is not None:
                chunks.append((path, body))
            path, body = line[len("+++ b/"):], []
        elif line.startswith(("diff --git", "--- a/", "index ", "@@", "new file", "deleted file", "similarity", "rename ")):
            continue
        elif path is not None and line[:1] in ("+", "-", " "):
            body.append(line)
    if path is not None:
        chunks.append((path, body))
    return chunks


def extract(diff_text: str) -> tuple[list[Candidate], list[Candidate]]:
    voice: list[Candidate] = []
    deleted: list[Candidate] = []

    for path, body in _file_chunks(diff_text):
        language = language_for(path)
        if language is None:
            continue
        marker = LINE_COMMENT[language]

        post = [ln[1:] for ln in body if ln[:1] in ("+", " ")]
        code = "\n".join(
            ln for ln in post
            if _split_comment(ln, marker) is None or _split_comment(ln, marker)[0].strip()
        )

        added, removed = [], []
        for idx, raw in enumerate(body):
            found = _split_comment(raw[1:], marker)
            if found is None:
                continue
            before, comment = found
            if raw[0] == "+":
                following = [ln[1:] for ln in body[idx + 1:] if ln[:1] in ("+", " ")]
                added.append(Candidate(comment, _placement(before, following), language, code, path))
            elif raw[0] == "-":
                removed.append(Candidate(comment, "block", language, code, path))

        voice.extend(added)
        # A rewrite shows up as a matched -/+ pair. The + side is already recorded
        # as voice; counting the - side too would report one edit as two.
        if not added:
            deleted.extend(removed)

    return voice, deleted
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_extract -v`
Expected: PASS, 16 tests

- [ ] **Step 5: Commit**

```bash
git add claude/.claude/skills/learning-comment-voice/scripts/
git commit -m "Extract comment candidates from a diff

Added and rewritten comments are voice; deleted ones are rulebook evidence.
Quote-aware scanning, so a URL in Go source is not read as a comment."
```

---

### Task 3: Query CLI with the full-corpus backend

**Files:**
- Create: `claude/.claude/skills/learning-comment-voice/scripts/voice_query.py`
- Create: `claude/.claude/skills/learning-comment-voice/scripts/test_voice_query.py`

**Interfaces:**
- Consumes: `Record`, `load_records` from `voice_corpus`.
- Produces:
  - `facet_filter(records: list[Record], *, language: str | None, placement: str | None, kind: str | None) -> list[Record]`
  - `render(records: list[Record]) -> str`
  - `main(argv: list[str]) -> int`

Only `language` and `placement` are meant to be filtered in normal use; `kind` is metadata exposed as an optional flag. The spec's reasoning: `kind` is a judgment call applied unevenly, and an uneven hard filter starves retrieval invisibly.

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for voice_query."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import voice_corpus as vc
import voice_query as vq


def stored(corpus: Path, **over) -> vc.Record:
    fields = dict(
        comment="// the API replays these in sequence",
        placement="block",
        language="go",
        kind="why",
        code="order = append(order, id)",
        description="an append that preserves arrival order",
        enclosing="replay",
        repo="widgets",
        path="services/foo/replay.go",
        commit="abc123",
        captured="2026-09-18",
    )
    fields.update(over)
    fields["id"] = vc.record_id(fields["comment"], fields["code"])
    rec = vc.Record(**fields)
    vc.write_record(rec, corpus)
    return rec


class TestFacetFilter(unittest.TestCase):
    def test_language_narrows(self):
        recs = [
            vc.Record(id="1", comment="// a", placement="block", language="go", kind="why",
                      code="x", description="d", enclosing=None, repo="r", path="p", commit="c", captured="2026-09-18"),
            vc.Record(id="2", comment="# b", placement="block", language="python", kind="why",
                      code="x", description="d", enclosing=None, repo="r", path="p", commit="c", captured="2026-09-18"),
        ]
        got = vq.facet_filter(recs, language="go", placement=None, kind=None)
        self.assertEqual(["1"], [r.id for r in got])

    def test_placement_narrows(self):
        recs = [
            vc.Record(id="1", comment="// a", placement="doc", language="go", kind="why",
                      code="x", description="d", enclosing=None, repo="r", path="p", commit="c", captured="2026-09-18"),
            vc.Record(id="2", comment="// b", placement="trailing", language="go", kind="why",
                      code="x", description="d", enclosing=None, repo="r", path="p", commit="c", captured="2026-09-18"),
        ]
        got = vq.facet_filter(recs, language=None, placement="doc", kind=None)
        self.assertEqual(["1"], [r.id for r in got])

    def test_no_facets_keeps_everything(self):
        recs = [
            vc.Record(id="1", comment="// a", placement="doc", language="go", kind="why",
                      code="x", description="d", enclosing=None, repo="r", path="p", commit="c", captured="2026-09-18"),
        ]
        self.assertEqual(recs, vq.facet_filter(recs, language=None, placement=None, kind=None))


class TestCLI(unittest.TestCase):
    def test_matching_record_is_printed_verbatim(self):
        with tempfile.TemporaryDirectory() as d:
            stored(Path(d))
            out = io.StringIO()
            with redirect_stdout(out):
                rc = vq.main(["--corpus", d, "--language", "go", "--situation", "ordering"])
        self.assertEqual(0, rc)
        self.assertIn("// the API replays these in sequence", out.getvalue())

    def test_non_matching_language_prints_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            stored(Path(d))
            out = io.StringIO()
            with redirect_stdout(out):
                rc = vq.main(["--corpus", d, "--language", "rust", "--situation", "ordering"])
        self.assertEqual(0, rc)
        self.assertEqual("", out.getvalue().strip())

    def test_missing_corpus_exits_zero_with_no_output(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = vq.main(["--corpus", "/nonexistent", "--situation", "anything"])
        self.assertEqual(0, rc, "a missing corpus degrades to today's behavior")
        self.assertEqual("", out.getvalue().strip())

    def test_k_caps_the_number_of_exemplars(self):
        with tempfile.TemporaryDirectory() as d:
            for n in range(5):
                stored(Path(d), comment=f"// comment {n}", code=f"x{n}")
            out = io.StringIO()
            with redirect_stdout(out):
                vq.main(["--corpus", d, "--situation", "x", "-k", "2"])
        self.assertEqual(2, out.getvalue().count("// comment"))

    def test_all_backend_returns_everything_when_k_is_absent(self):
        with tempfile.TemporaryDirectory() as d:
            for n in range(5):
                stored(Path(d), comment=f"// comment {n}", code=f"x{n}")
            out = io.StringIO()
            with redirect_stdout(out):
                vq.main(["--corpus", d, "--situation", "x"])
        self.assertEqual(5, out.getvalue().count("// comment"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_query -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice_query'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Serve comment exemplars for a situation Claude is about to comment on.

The only interface consumers use. Which backend ran is never visible to the
caller, so swapping the full-corpus backend for vector similarity changes no
caller and needs no re-capture.

Examples:
  voice_query.py --language go --placement doc \\
      --situation "retry loop whose backoff cap tracks an upstream timeout"

  voice_query.py --language python --kind warning -k 3 --situation "..."
"""

import argparse
import sys
from pathlib import Path

import voice_corpus as vc

DEFAULT_CORPUS = vc.DEFAULT_CORPUS


def facet_filter(records, *, language, placement, kind):
    out = records
    if language:
        out = [r for r in out if r.language == language]
    if placement:
        out = [r for r in out if r.placement == placement]
    if kind:
        out = [r for r in out if r.kind == kind]
    return out


def render(records) -> str:
    blocks = []
    for r in records:
        head = f"--- {r.language}/{r.placement} · {r.repo}:{r.path}"
        code = "\n".join("    " + ln for ln in r.code.split("\n")[:4])
        blocks.append(f"{head}\n{r.comment}\n{code}")
    return "\n\n".join(blocks)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--situation", required=True, help="what the code presents, in one line")
    ap.add_argument("--language")
    ap.add_argument("--placement", choices=vc.PLACEMENTS)
    ap.add_argument("--kind", choices=vc.KINDS)
    ap.add_argument("-k", type=int, default=None, help="cap on exemplars returned")
    args = ap.parse_args(argv)

    records = facet_filter(
        vc.load_records(args.corpus),
        language=args.language,
        placement=args.placement,
        kind=args.kind,
    )
    if args.k is not None:
        records = records[: args.k]
    if records:
        print(render(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_query -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add claude/.claude/skills/learning-comment-voice/scripts/
git commit -m "Add the voice query CLI with the full-corpus backend

Filters on language and placement only. Kind stays an optional flag: it is a
judgment call, and an uneven hard filter starves retrieval invisibly."
```

---

### Task 4: Vector backends and index builder

**Files:**
- Create: `claude/.claude/skills/learning-comment-voice/scripts/voice_vectors.py`
- Create: `claude/.claude/skills/learning-comment-voice/scripts/voice_index.py`
- Create: `claude/.claude/skills/learning-comment-voice/scripts/test_voice_vectors.py`

**Interfaces:**
- Consumes: `Record`, `load_records` from `voice_corpus`.
- Produces:
  - `voice_vectors.available() -> bool`
  - `voice_vectors.embed(texts: list[str]) -> "numpy.ndarray"` (L2-normalised rows)
  - `voice_vectors.rank(query, matrix, ids: list[str], k: int) -> list[str]` — ids, best first
  - `voice_index.build(corpus_dir: Path, index_dir: Path) -> int` — records indexed
  - `voice_index.load(index_dir: Path) -> dict | None` — `{"ids": [...], "desc": ndarray, "code": ndarray}`, `None` when absent or unreadable

Both the `desc` and `code` vectors are computed. The spec is explicit that which one retrieves better cannot be known before a corpus exists, so the choice is deferred to measurement and both are stored.

`numpy` and `sentence-transformers` are not installed on this machine. Every test in this task that needs them must skip, and the core path must stay green without them — that is the deliverable being verified, not an inconvenience.

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for voice_vectors and voice_index.

The dependency-free assertions are the important ones: they pin the behavior this
machine actually has today, where neither numpy nor sentence-transformers is
installed. The embedding tests skip rather than fail.
"""

import tempfile
import unittest
from pathlib import Path

import voice_corpus as vc
import voice_index as vi
import voice_vectors as vv


def stored(corpus: Path, comment: str, code: str) -> vc.Record:
    rec = vc.Record(
        id=vc.record_id(comment, code), comment=comment, placement="block",
        language="go", kind="why", code=code, description="d", enclosing=None, repo="r",
        path="p.go", commit="c", captured="2026-09-18",
    )
    vc.write_record(rec, corpus)
    return rec


class TestDegradesWithoutDependencies(unittest.TestCase):
    def test_available_answers_without_raising(self):
        self.assertIn(vv.available(), (True, False))

    def test_missing_index_loads_as_none(self):
        self.assertIsNone(vi.load(Path("/nonexistent/index")))

    def test_unreadable_index_loads_as_none(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "vectors.npz").write_text("not an npz")
            self.assertIsNone(vi.load(Path(d)))

    def test_build_without_dependencies_indexes_nothing(self):
        if vv.available():
            self.skipTest("dependencies present; this asserts the degraded path")
        with tempfile.TemporaryDirectory() as d:
            corpus, index = Path(d) / "corpus", Path(d) / "index"
            stored(corpus, "// a", "x := 1")
            self.assertEqual(0, vi.build(corpus, index))


class TestEmbedding(unittest.TestCase):
    def setUp(self):
        if not vv.available():
            self.skipTest("numpy/sentence-transformers not installed")

    def test_rows_are_unit_length(self):
        import numpy as np
        m = vv.embed(["a retry loop", "a parser"])
        self.assertTrue(np.allclose(np.linalg.norm(m, axis=1), 1.0))

    def test_rank_puts_the_nearest_id_first(self):
        m = vv.embed(["a retry loop with backoff", "an HTML template renderer"])
        q = vv.embed(["retrying with exponential backoff"])[0]
        self.assertEqual("retry", vv.rank(q, m, ["retry", "html"], k=2)[0])

    def test_rank_respects_k(self):
        m = vv.embed(["a", "b", "c"])
        q = vv.embed(["a"])[0]
        self.assertEqual(2, len(vv.rank(q, m, ["1", "2", "3"], k=2)))


class TestIndexBuild(unittest.TestCase):
    def setUp(self):
        if not vv.available():
            self.skipTest("numpy/sentence-transformers not installed")

    def test_both_vector_sets_are_written(self):
        with tempfile.TemporaryDirectory() as d:
            corpus, index = Path(d) / "corpus", Path(d) / "index"
            rec = stored(corpus, "// why", "x := compute()")
            self.assertEqual(1, vi.build(corpus, index))
            loaded = vi.load(index)
        self.assertEqual([rec.id], list(loaded["ids"]))
        self.assertEqual(1, loaded["desc"].shape[0])
        self.assertEqual(1, loaded["code"].shape[0])

    def test_rebuild_reflects_a_deleted_record(self):
        with tempfile.TemporaryDirectory() as d:
            corpus, index = Path(d) / "corpus", Path(d) / "index"
            keep = stored(corpus, "// keep", "x := 1")
            drop = stored(corpus, "// drop", "y := 2")
            vi.build(corpus, index)
            (corpus / f"{drop.id}.json").unlink()
            self.assertEqual(1, vi.build(corpus, index))
            self.assertEqual([keep.id], list(vi.load(index)["ids"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_vectors -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice_index'`

- [ ] **Step 3: Write `voice_vectors.py`**

```python
#!/usr/bin/env python3
"""Embedding and cosine ranking, behind an availability check.

Neither numpy nor sentence-transformers is installed on this machine, and neither
is required. Everything here is optional: `available()` answers honestly and every
caller treats False as "return nothing", never as an error.

A few thousand 384-dimensional vectors is microseconds of brute-force cosine in
numpy, so there is no index structure and no vector database -- rows are
L2-normalised at embed time, which makes the dot product the cosine.
"""

MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def available() -> bool:
    try:
        import numpy  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts: list[str]):
    import numpy as np

    raw = _load_model().encode(list(texts))
    matrix = np.asarray(raw, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def rank(query, matrix, ids: list[str], k: int) -> list[str]:
    """The k ids whose rows are nearest `query`, best first."""
    import numpy as np

    if len(ids) == 0:
        return []
    scores = matrix @ query
    order = np.argsort(-scores)[:k]
    return [ids[i] for i in order]
```

- [ ] **Step 4: Write `voice_index.py`**

```python
#!/usr/bin/env python3
"""Build the vector index from the corpus.

A pure function of the corpus: it can be rebuilt at any time and is never
authoritative. A stale or missing index costs recall, never correctness, which is
why nothing reads it without a fallback.

Both vector sets are written. Whether a code-derived description retrieves better
than the code itself is an empirical question that cannot be answered before a
corpus exists, so the decision is deferred to measurement rather than guessed.

Usage:
  voice_index.py                 # rebuild in place
  voice_index.py --corpus DIR --index DIR
"""

import argparse
import sys
from pathlib import Path

import voice_corpus as vc
import voice_vectors as vv

DEFAULT_CORPUS = vc.DEFAULT_CORPUS
DEFAULT_INDEX = vc.DEFAULT_INDEX

def build(corpus_dir: Path, index_dir: Path) -> int:
    """Rebuild the index. Returns the number of records indexed."""
    if not vv.available():
        return 0
    records = vc.load_records(corpus_dir)
    if not records:
        return 0

    import numpy as np

    ids = [r.id for r in records]
    desc = vv.embed([_description(r) for r in records])
    code = vv.embed([r.code for r in records])

    index_dir.mkdir(parents=True, exist_ok=True)
    np.savez(index_dir / "vectors.npz", ids=np.array(ids), desc=desc, code=code)
    return len(ids)


def _description(rec) -> str:
    """The comment-blind situation description, falling back to the code.

    A capture run whose describing subagent failed still belongs in the index --
    degraded on the desc side, intact on code.
    """
    return rec.description or rec.code


def load(index_dir: Path):
    if not vv.available():
        return None
    try:
        import numpy as np

        data = np.load(index_dir / "vectors.npz", allow_pickle=False)
        return {"ids": [str(i) for i in data["ids"]], "desc": data["desc"], "code": data["code"]}
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    args = ap.parse_args(argv)
    count = build(args.corpus, args.index)
    print(f"indexed {count} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_vectors -v`
Expected: PASS with the embedding and index-build tests reported as skipped (`numpy/sentence-transformers not installed`), and the four degradation tests passing.

- [ ] **Step 6: Run the whole suite**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest discover -v`
Expected: PASS. Redirect to a file and print only on failure — a pipe hands the pipeline's status to its last stage, which is how a green tree gets reported as a failure.

- [ ] **Step 7: Commit**

```bash
git add claude/.claude/skills/learning-comment-voice/scripts/
git commit -m "Add vector backends and the index builder

Both the description and code vectors are computed; which retrieves better is
an empirical question that needs a corpus to answer. Dependencies are optional
and absent here, so the degraded path is what the tests pin."
```

---

### Task 5: Backend auto-selection

**Files:**
- Modify: `claude/.claude/skills/learning-comment-voice/scripts/voice_query.py`
- Modify: `claude/.claude/skills/learning-comment-voice/scripts/test_voice_query.py`

**Interfaces:**
- Consumes: `voice_index.load`, `voice_vectors.available`, `voice_vectors.embed`, `voice_vectors.rank`.
- Produces: `choose_backend(records: list[Record], index) -> str` returning `"all"`, `"desc"`, or `"code"`.

Thresholds: `VECTOR_MIN_ENTRIES = 150`, `VECTOR_MIN_CHARS = 20000`. Below either, `all` is correct and better than similarity search — returning the whole corpus beats ranking twenty items. Above both, and only when an index exists, ranking takes over.

- [ ] **Step 1: Write the failing tests**

Append to `test_voice_query.py`:

```python
class TestBackendSelection(unittest.TestCase):
    def _records(self, n, comment_len=10):
        return [
            vc.Record(id=str(i), comment="/" * comment_len, placement="block",
                      language="go", kind="why", code="x", description="d",
                      enclosing=None, repo="r", path="p", commit="c", captured="2026-09-18")
            for i in range(n)
        ]

    def test_small_corpus_uses_the_all_backend(self):
        self.assertEqual("all", vq.choose_backend(self._records(10), index={"ids": []}))

    def test_large_corpus_without_an_index_still_uses_all(self):
        big = self._records(200, comment_len=200)
        self.assertEqual("all", vq.choose_backend(big, index=None))

    def test_large_corpus_with_an_index_uses_desc(self):
        big = self._records(200, comment_len=200)
        self.assertEqual("desc", vq.choose_backend(big, index={"ids": ["0"]}))

    def test_many_entries_but_little_text_stays_on_all(self):
        many_tiny = self._records(200, comment_len=2)
        self.assertEqual("all", vq.choose_backend(many_tiny, index={"ids": ["0"]}))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_voice_query.TestBackendSelection -v`
Expected: FAIL with `AttributeError: module 'voice_query' has no attribute 'choose_backend'`

- [ ] **Step 3: Implement selection**

Add to `voice_query.py`:

```python
import voice_index as vi
import voice_vectors as vv

VECTOR_MIN_ENTRIES = 150
VECTOR_MIN_CHARS = 20000


def choose_backend(records, index) -> str:
    """Which backend to run when --backend was not given.

    Below either threshold the whole corpus fits in context, and returning all of
    it beats ranking twenty items. Without an index there is nothing to rank with,
    so size is irrelevant.
    """
    if index is None or not index.get("ids"):
        return "all"
    if len(records) < VECTOR_MIN_ENTRIES:
        return "all"
    if sum(len(r.comment) for r in records) < VECTOR_MIN_CHARS:
        return "all"
    return "desc"
```

Then wire it into `main`, replacing the body after the facet filter:

```python
    index = vi.load(vi.DEFAULT_INDEX if args.corpus == DEFAULT_CORPUS else args.corpus.parent / "index")
    backend = args.backend or choose_backend(records, index)

    if backend != "all" and index is not None and vv.available():
        by_id = {r.id: r for r in records}
        rows = [i for i, rid in enumerate(index["ids"]) if rid in by_id]
        if rows:
            import numpy as np

            matrix = index[backend][rows]
            ids = [index["ids"][i] for i in rows]
            query = vv.embed([args.situation])[0]
            records = [by_id[i] for i in vv.rank(query, matrix, ids, k=args.k or 5)]

    if args.k is not None:
        records = records[: args.k]
    if records:
        print(render(records))
    return 0
```

and add the flag:

```python
    ap.add_argument("--backend", choices=("all", "desc", "code"),
                    help="override automatic selection")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest discover -v`
Expected: PASS, embedding tests skipped.

- [ ] **Step 5: Commit**

```bash
git add claude/.claude/skills/learning-comment-voice/scripts/
git commit -m "Choose the query backend by corpus size

Below 150 entries or 20k characters the whole corpus fits in context, and
returning all of it beats ranking twenty items. No index means nothing to rank."
```

---

### Task 6: The capture skill

**Files:**
- Create: `claude/.claude/skills/learning-comment-voice/SKILL.md`

**Interfaces:**
- Consumes: `voice_extract.extract`, `voice_corpus.write_record`, `voice_corpus.append_stats`, `voice_query.main`.
- Produces: nothing other tasks consume.

This task has no unit test — it is prose Claude follows. Its verification is the end-to-end run in Task 7.

The skill has **two triggers**, which the description must carry both of:
1. Max has handed back hand edits in an interactive commit-editing flow (capture).
2. Claude is about to write or rewrite comments in code (query).

Trigger 1 is also invoked directly from `editing-commits-interactively` in Task 8. The description still carries it, so the skill works when that flow is not the entry point — but the direct call is what makes capture reliable rather than dependent on two descriptions matching the same moment.

- [ ] **Step 1: Write `SKILL.md`**

````markdown
---
name: learning-comment-voice
description: >-
  Capture the comments Max writes by hand, and serve them back as exemplars
  before Claude writes a comment. Use when Max has just finished hand-editing a
  commit during an interactive commit walk and handed the diff back ("done",
  "I'm finished with this one"), and also whenever Claude is about to write or
  rewrite code comments and wants to match Max's voice rather than a generic
  register. Triggers on "capture my comments", "learn from these edits", "what
  would I have written here", or immediately after a rebase stop's edits land.
---

# Learning comment voice

Two jobs sharing one corpus. **Capture** records the comments Max writes by hand.
**Query** serves them back before Claude writes one. Neither calls the other; they
meet at `corpus/` on disk.

The corpus decides **how a comment reads**. `review-comments/references/rules.md`
decides **whether it exists at all**. Keep the two apart — phrasing written down as
rules becomes another style guide, which is the thing this replaces.

## Capture

Run this when Max has hand-edited a commit and said he is done, inside an
interactive commit walk. That diff is by construction his own work, which is the
entire provenance argument — do not capture from a diff Claude produced.

1. **Get the diff of his edits.** At an edit stop that is `git diff`; at a conflict
   stop it is `git diff` against the resolution he approved. If Claude has edited
   the tree since he handed it back, stop — the provenance is gone, and a corpus
   entry that is really Claude's text poisons every retrieval that returns it.

2. **Extract candidates.**

   ```bash
   cd claude/.claude/skills/learning-comment-voice/scripts
   git -C <repo> diff > /tmp/edits.diff
   python3 -c "import voice_extract, sys; print(voice_extract.extract(open('/tmp/edits.diff').read()))"
   ```

   Two lists come back: comments he **added or rewrote**, and comments he
   **deleted**.

3. **Describe each voice candidate comment-blind.** For each one, dispatch a
   subagent with the candidate's `code` field — which already has the comment
   stripped — and this instruction:

   > Describe in one line what this code presents: what it does, and what about it
   > is non-obvious, constrained, or risky. Do not describe what a comment should
   > say. Return the line, then a single word from: why, warning, contract, domain,
   > pointer — whichever best names the kind of remark this code invites.

   **The subagent must never see the comment.** At query time there is no comment,
   so a description written with knowledge of one is better-aimed than anything the
   query side can produce — retrieval that tests well and degrades in use. Passing
   the stripped `code` field is what makes both ends the same function of the same
   input.

4. **Write the records.** One per voice candidate, via `voice_corpus.write_record`.
   Fill `repo`, `path`, `commit`, and `captured` from the current repository state.

5. **Take the deleted comments to the rulebook.** They are not corpus entries. If a
   deletion establishes a principle `rules.md` does not already carry, propose it
   there per that skill's step 7 — propose, do not add unilaterally.

6. **Record the run.** `voice_corpus.append_stats` with the added, rewritten, and
   deleted counts. Comment edits per commit-walk trending down is the only evidence
   this system does anything.

7. **Report what was captured**, comment by comment. A misattribution cannot be
   prevented at capture time — the only defence is Max seeing it immediately and
   deleting the file.

## Query

Before writing or rewriting a comment:

1. Describe the situation the code presents, in one line, **without reference to
   what you are about to say**. Same instruction as step 3 above — that symmetry is
   what makes retrieval work.

2. Ask for exemplars:

   ```bash
   python3 claude/.claude/skills/learning-comment-voice/scripts/voice_query.py \
       --language go --placement doc \
       --situation "a retry loop whose backoff cap tracks an upstream timeout"
   ```

3. **Read them as register, not as content.** They show sentence length, how much
   context is assumed, whether the reason leads or trails. They are not templates
   to fill, and none of them is about your code.

4. Empty output is the normal early state and means nothing is wrong. Write the
   comment as you otherwise would.

## After a capture run

Rebuild the index if the dependencies are installed:

```bash
python3 claude/.claude/skills/learning-comment-voice/scripts/voice_index.py
```

It prints `indexed 0 records` when `numpy`/`sentence-transformers` are absent,
which is the expected state today and costs nothing — the query path falls back to
returning the whole filtered corpus.

## Red flags — STOP

- Capturing from a diff Claude wrote, or from a tree Claude has touched since Max
  handed it back.
- Letting the describing subagent see the comment.
- Storing Claude's original comment text anywhere in a record.
- Writing a vector into a record — vectors are derived and live in the index.
- Adding a rule to `rules.md` that Max has not endorsed.
- Committing a corpus file, a `corpus/` directory, or a sample record into the
  dotfiles repo. The corpus is machine-local and untracked.
````

- [ ] **Step 2: Verify the frontmatter parses and the skill is discoverable**

Run:
```bash
cd /home/max/dotfiles && python3 - <<'PY'
import pathlib, re
p = pathlib.Path("claude/.claude/skills/learning-comment-voice/SKILL.md")
text = p.read_text()
assert text.startswith("---\n"), "frontmatter must open the file"
fm = text.split("---\n")[1]
assert re.search(r"^name: learning-comment-voice$", fm, re.M), "name mismatch"
assert "description:" in fm
print("ok")
PY
```
Expected: `ok`

- [ ] **Step 3: Confirm nothing work-private was touched, and no corpus data was staged**

Run:
```bash
cd /home/max/dotfiles
git status --porcelain claudework/
git status --porcelain claude/.claude/skills/learning-comment-voice/ | grep -i corpus
```
Expected: both empty. The first would mean a work-private file drifted into a public task; the second would mean corpus data reached the repo, which the Global Constraints forbid.

- [ ] **Step 4: Commit**

```bash
git add claude/.claude/skills/learning-comment-voice/SKILL.md
git commit -m "Add the learning-comment-voice skill

Capture and query share a corpus and nothing else. The describing subagent never
sees the comment, so index and query are the same function of the same input."
```

---

### Task 7: End-to-end verification on a real commit walk

**Files:**
- Create: `claude/.claude/skills/learning-comment-voice/scripts/test_end_to_end.py`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

This task proves the pieces compose. It drives a real git repository in a temp
directory, in the style of the hook tests in `claude/.claude/hooks/`.

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""End-to-end: a real repo, a real edit, a real corpus entry, a real query.

Drives git in a temp directory rather than mocking a diff, because the diff format
is the interface between the capture step and everything downstream -- a mocked
one proves only that the mock matches itself.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

import voice_corpus as vc
import voice_extract as ve
import voice_query as vq


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout


def a_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "max@example.com")
    git(repo, "config", "user.name", "Max")
    (repo / "watch.go").write_text("package main\n\nfunc Watch() error {\n\treturn nil\n}\n")
    git(repo, "add", "watch.go")
    git(repo, "commit", "-qm", "initial")
    return repo


class TestCaptureThenQuery(unittest.TestCase):
    def test_a_hand_edited_comment_comes_back_as_an_exemplar(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            repo = a_repo(tmp)
            corpus = tmp / "corpus"

            # Max's hand edit: a doc comment above the declaration.
            (repo / "watch.go").write_text(
                "package main\n\n"
                "// Watch returns once the job reaches a terminal state, which the\n"
                "// Failed condition only reports after backoffLimit is spent.\n"
                "func Watch() error {\n\treturn nil\n}\n"
            )
            voice, deleted = ve.extract(git(repo, "diff"))

            self.assertEqual([], deleted)
            self.assertEqual(2, len(voice), "both comment lines are candidates")
            self.assertEqual("doc", voice[0].placement)
            self.assertEqual("go", voice[0].language)
            self.assertNotIn("Watch returns once", voice[0].code)

            for cand in voice:
                vc.write_record(
                    vc.Record(
                        id=vc.record_id(cand.comment, cand.code),
                        comment=cand.comment, placement=cand.placement,
                        language=cand.language, kind="why", code=cand.code,
                        description="a job watch returning on a terminal condition",
                        enclosing="Watch", repo="repo", path=cand.path,
                        commit=git(repo, "rev-parse", "HEAD").strip(),
                        captured="2026-09-18",
                    ),
                    corpus,
                )

            got = vq.facet_filter(
                vc.load_records(corpus), language="go", placement="doc", kind=None
            )
            self.assertEqual(2, len(got))
            self.assertIn("backoffLimit", " ".join(r.comment for r in got))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd claude/.claude/skills/learning-comment-voice/scripts && python3 -m unittest test_end_to_end -v`
Expected: FAIL — most likely on the `placement` or candidate-count assertion, since this is the first time `extract` sees git's own diff output rather than the test helper's.

- [ ] **Step 3: Fix whatever the real diff format broke**

Likely culprits, in order:
- git emits `\ No newline at end of file` lines, which `_file_chunks` must not treat as content. The `line[:1] in ("+", "-", " ")` guard admits `\` — it does not, since `\` is not in that set, but confirm against real output.
- git's hunk headers carry trailing context (`@@ -1,3 +1,4 @@ func Watch()`), already skipped by the `@@` prefix check.
- Multi-line comment blocks produce one candidate per line, which is intended: each line is a separate exemplar of phrasing.

Fix `voice_extract.py`, not the test. The test encodes git's real output; the helper in `test_voice_extract.py` is the approximation.

- [ ] **Step 4: Run the whole suite**

Run:
```bash
cd claude/.claude/skills/learning-comment-voice/scripts
python3 -m unittest discover > /tmp/voice-tests.log 2>&1; rc=$?
[ $rc -eq 0 ] && echo PASS || { echo FAIL; cat /tmp/voice-tests.log; }
```
Expected: `PASS`. Capture `rc` on its own line before anything else expands — command substitution resets `$?`, so `echo "exit $(date)"` reports the status of `date`.

- [ ] **Step 5: Commit**

```bash
git add claude/.claude/skills/learning-comment-voice/scripts/
git commit -m "Verify capture and query compose against a real repo

Drives git in a temp dir rather than mocking a diff: the diff format is the
interface between capture and everything downstream, and a mocked one proves
only that the mock matches itself."
```

---

---

### Task 8: Call capture from the interactive commit flow

**Files:**
- Modify: `claude/.claude/skills/editing-commits-interactively/SKILL.md` (section "5. The turn")

**Interfaces:**
- Consumes: the capture procedure from Task 6.
- Produces: nothing other tasks consume.

The capture point the whole design rests on. `editing-commits-interactively` already
runs `git diff` at the moment Max says he is done — that diff is his hand edits, and
today it is read once and discarded.

Capture goes at **step 4 of the turn**, immediately after that diff and *before* the
propose-and-edit loop in step 6. Once Claude has edited the tree, the diff is a mix
of both their work and the provenance is gone.

Re-capturing is safe. A record's id is the hash of its comment plus its code, so a
second capture of an unchanged comment rewrites the same file — the turn's loop can
run several times without accumulating duplicates.

- [ ] **Step 1: Insert the capture step**

In `claude/.claude/skills/editing-commits-interactively/SKILL.md`, under `### 5. The turn`, the list currently reads:

```
4. When they say done: `git status` and `git diff` to see exactly what changed.
5. Infer a verification command scoped to what the commit touches and run it.
```

Insert a new step between them and renumber the rest (current 5-7 become 6-8):

```markdown
5. **Capture the comment edits before touching anything.** That diff is the user's
   own work, and it is the only moment it can be attributed to them — once you edit
   in step 7, the tree is a mix of both. Invoke the `learning-comment-voice` skill
   with this diff. It is idempotent, so running it again on a later pass through the
   loop costs nothing. If the skill is unavailable, say so once and continue; the
   commit's turn is not blocked on it.
```

- [ ] **Step 2: Verify the renumbering**

Run:
```bash
cd /home/max/dotfiles
sed -n '/^### 5. The turn/,/^### 6\./p' claude/.claude/skills/editing-commits-interactively/SKILL.md
```
Expected: steps numbered 1 through 8, no repeats, no gaps, and the former step 6
("Read their changes; propose changes") now numbered 7 so the new step's reference to
"step 7" points at it.

- [ ] **Step 3: Confirm the cross-references elsewhere still hold**

Run: `cd /home/max/dotfiles && grep -n 'step 5\|step 6\|step 7' claude/.claude/skills/editing-commits-interactively/SKILL.md`
Expected: the "run the full turn from step 5 right there" line in section 4 still
means the turn as a whole and needs no change; any reference to a numbered step
*within* the turn must point at its new number.

- [ ] **Step 4: Commit**

```bash
git add claude/.claude/skills/editing-commits-interactively/SKILL.md
git commit -m "Capture comment edits at the interactive commit stop

The diff after the user says done is the only moment their comment edits can be
attributed to them; once we edit in the propose loop, the tree is a mix of both."
```

---

### Task 9: Wire the lookup into review-comments

**Files:**
- Modify: `claudework/.claude/skills/review-comments/SKILL.md` (procedure, between steps 3 and 4)

**Interfaces:**
- Consumes: `voice_query.py`.
- Produces: nothing other tasks consume.

The spec's consumer half. `review-comments` currently judges a comment and rewrites
it in whatever register Claude reaches for. The lookup lands between the verdict and
the edit, so a **rewrite** verdict is carried out in Max's voice. It deliberately does
not touch keep or delete verdicts — those are the rulebook's business, and exemplars
have nothing to say about whether a comment should exist.

- [ ] **Step 1: Insert the new step**

In `claudework/.claude/skills/review-comments/SKILL.md`, insert between the current
step 3 ("Judge each against `references/rules.md`") and step 4 ("Apply the clear
ones"), and renumber the steps that follow (current 4-7 become 5-8):

```markdown
4. **Fetch voice exemplars for the rewrites.** For each comment whose verdict is
   **rewrite**, describe in one line what the code presents — not what the comment
   should say — and ask for exemplars:

   ```bash
   python3 ../learning-comment-voice/scripts/voice_query.py \
       --language go --placement block --situation "<one line>"
   ```

   Read them as register: sentence length, how much context is assumed, whether the
   reason leads or trails. They are not templates, and none is about this code.

   Empty output is the normal early state and means nothing is wrong — rewrite as
   you otherwise would. Never block a rewrite on a missing corpus, a missing script,
   or an empty result.

   Verdicts of keep and delete skip this entirely: whether a comment should exist is
   `rules.md`'s question, and no exemplar answers it.
```

- [ ] **Step 2: Verify the renumbering is consistent**

Run:
```bash
cd /home/max/dotfiles && grep -nE '^[0-9]+\. \*\*' claudework/.claude/skills/review-comments/SKILL.md
```
Expected: steps numbered 1 through 8 with no repeats and no gaps. Then confirm the
cross-references still point at the right steps:

```bash
grep -n 'step [0-9]' claudework/.claude/skills/review-comments/SKILL.md
```
Expected: the "see step 7" reference in the old step 5 and the "see the rulebook"
pointer in step 6 now name the steps they actually mean — old step 7 (grow the
rulebook) is now step 8.

- [ ] **Step 3: Confirm nothing else was touched**

Run: `cd /home/max/dotfiles && git status --porcelain`
Expected: `review-comments/SKILL.md` is the only entry beyond changes that were
already in the tree before this plan started. This is the one work-private file the
whole plan touches.

- [ ] **Step 4: Commit**

```bash
git add claudework/.claude/skills/review-comments/SKILL.md
git commit -m "Look up voice exemplars before rewriting a comment

Only rewrite verdicts consult the corpus. Whether a comment should exist is the
rulebook's question, and no exemplar answers it."
```

## Verification

After Task 7, the whole system is exercised but has never run in anger. The first
real use is the proof:

1. Run an interactive commit walk on a branch with comments worth fixing.
2. At a stop, edit comments by hand, hand the diff back, and let the capture run.
3. Confirm `corpus/` gained one file per comment, and read each one — a
   misattribution is only catchable here.
4. Confirm `corpus/_stats.jsonl` gained a line.
5. Run `voice_query.py --language go --situation "..."` and confirm the exemplars
   come back.

Do not report the system working until step 5 has produced output from a corpus
built by step 2. A query against a hand-written corpus proves only the query.

---

## Corrections found during execution

This plan was executed on 2026-09-21. The code blocks above are what was
*proposed*; five defects surfaced in review and the committed modules differ
accordingly. **The modules under `scripts/` are the source of truth** — the blocks
here are kept as written so the reasoning that produced them stays legible, but do
not transcribe them fresh without applying these.

1. **Task 2, rewrite suppression was file-wide.** `if not added: deleted.extend(removed)`
   drops *every* deleted comment in a file whenever any comment was added anywhere in
   it, and `_file_chunks` flattened all hunks into one body so the "same hunk" the
   inline comment claims never existed. Deleted comments are the rulebook's evidence,
   so this discarded them silently. Fixed with per-hunk bodies and adjacency-based pair
   detection: a removed comment is suppressed only when its `-` run is immediately
   followed by a `+` run containing a comment.

2. **Task 2, `code` was not comment-blind for trailing comments.** Only whole-line
   comments were stripped, so `x := 1 // seconds, not millis` kept its comment text in
   `code` — the field that exists precisely so the describing subagent never sees the
   comment. Fixed by keeping the code portion and dropping the comment portion.

3. **Task 7, `_placement` misread multi-line doc comments.** The forward scan for a
   declaration skipped blank lines but not other comment lines, so the first line of any
   two-line doc comment saw the second line, failed the declaration match, and returned
   `block`. Every multi-line doc comment was misclassified. The unit helper only ever
   built single-line comments, which is why 20 tests missed it and the end-to-end test
   caught it immediately. The first fix over-corrected — skipping comment lines
   unconditionally also merged runs separated by a blank line, which in Go is exactly
   what makes a comment *not* a doc comment. Final rule: skip contiguous comment lines
   only.

4. **Task 6 and Task 9, paths did not resolve at runtime.** Both skills invoked scripts
   by paths relative to this repository, but a skill runs with the working directory set
   to whatever project the user is in. The relative hop between packages is unavailable
   too: `~/.claude/skills/<skill>` is a symlink, so `cd`-ing through it lands in the
   physical package directory and `..` climbs inside that package rather than into the
   shared `~/.claude/` tree. Both now use `~/.claude/skills/learning-comment-voice/scripts/...`,
   and the capture step uses `PYTHONPATH` rather than `cd`.

5. **Counts in this plan are stale by construction.** Task 2's "16 tests" was a miscount
   of its own code block (17), and the suite grew as fixes added coverage. The final
   suite is 60 tests, 5 of which skip because `numpy` and `sentence-transformers` are
   not installed — the designed outcome, not a gap.

**Task 8 was never executed.** It would have called capture directly from
`editing-commits-interactively`, but that skill was uncommitted and absent from this
branch. Capture therefore fires only when Claude matches this skill's own description.
Applying Task 8 once that skill is committed is the single highest-value follow-up.
