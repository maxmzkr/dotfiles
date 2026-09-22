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

# Opening, continuation, and closing lines of a block comment or docstring,
# in every language above that has one.
BLOCK_COMMENT_PREFIXES = ('"""', "'''", '/*', '*', '*/')

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


def _placement(code_before: str, following: list[str], marker: str) -> str:
    if code_before.strip():
        return "trailing"
    crossed_blank = False
    for line in following:
        stripped = line.strip()
        if not stripped:
            crossed_blank = True
            continue
        if stripped.startswith(marker):
            if crossed_blank:
                # A blank line separates this from the run under test -- in Go
                # (and the other languages here) that break is what disqualifies
                # a comment from being a doc comment, so this is a fresh, unrelated
                # run and not evidence about what the candidate precedes.
                return "block"
            # Still inside the same comment block -- a multi-line doc comment's
            # own later lines must not be mistaken for the code that follows it.
            continue
        return "doc" if DECLARATION.match(line) else "block"
    return "block"


def _file_chunks(diff_text: str) -> list[tuple[str, list[list[str]]]]:
    """(path, hunks) per file, each hunk its own body-line list.

    A `@@` line starts a new hunk. Keeping hunks separate (rather than one flat
    body per file) matters for rewrite detection below: two unrelated edits in
    different hunks of the same file must never look adjacent to each other.
    """
    chunks: list[tuple[str, list[list[str]]]] = []
    path: str | None = None
    hunks: list[list[str]] = []
    body: list[str] | None = None
    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            if path is not None:
                if body is not None:
                    hunks.append(body)
                chunks.append((path, hunks))
            path, hunks, body = line[len("+++ b/"):], [], None
        elif line.startswith("@@"):
            if body is not None:
                hunks.append(body)
            body = []
        elif line.startswith(("diff --git", "--- a/", "index ", "new file", "deleted file", "similarity", "rename ")):
            continue
        elif path is not None and body is not None and line[:1] in ("+", "-", " "):
            body.append(line)
    if path is not None:
        if body is not None:
            hunks.append(body)
        chunks.append((path, hunks))
    return chunks


def _segments(body: list[str]) -> list[tuple[str, list[tuple[int, str]]]]:
    """Group `body` into contiguous runs sharing a +/-/space prefix.

    A rewrite is how git renders a matched -/+ pair: the deleted line and its
    replacement sit in adjacent runs. Grouping this way is what lets the
    suppression rule below ask "is this deletion immediately followed by an
    addition" instead of "did this file gain a comment anywhere".
    """
    segments: list[tuple[str, list[tuple[int, str]]]] = []
    current_prefix: str | None = None
    current: list[tuple[int, str]] = []
    for idx, raw in enumerate(body):
        prefix = raw[:1]
        if prefix != current_prefix:
            if current:
                segments.append((current_prefix, current))
            current_prefix, current = prefix, []
        current.append((idx, raw))
    if current:
        segments.append((current_prefix, current))
    return segments


def _strip_comment(line: str, marker: str) -> str | None:
    """The code-only portion of `line`, or None when the whole line is a comment.

    A trailing comment keeps its code prefix; a whole-line comment drops out of
    `code` entirely so the field stays comment-blind either way.

    Block comments go too, though they never become candidates. `code` exists to
    be handed to a subagent that must not see a comment, and a docstring saying
    what is non-obvious about the code is exactly what that subagent is being
    asked to work out for itself.
    """
    if line.strip().startswith(BLOCK_COMMENT_PREFIXES):
        return None
    found = _split_comment(line, marker)
    if found is None:
        return line
    before, _ = found
    return before.rstrip() if before.strip() else None


def extract(diff_text: str) -> tuple[list[Candidate], list[Candidate]]:
    voice: list[Candidate] = []
    deleted: list[Candidate] = []

    for path, hunks in _file_chunks(diff_text):
        language = language_for(path)
        if language is None:
            continue
        marker = LINE_COMMENT[language]

        for body in hunks:
            post = [ln[1:] for ln in body if ln[:1] in ("+", " ")]
            code = "\n".join(
                stripped for stripped in (_strip_comment(ln, marker) for ln in post)
                if stripped is not None
            )

            segments = _segments(body)
            for seg_i, (prefix, lines) in enumerate(segments):
                if prefix == "+":
                    # A run of whole-line comments is one comment, not one per
                    # line: the reasoning a multi-line comment carries is the
                    # whole of it, and splitting it stores fragments while
                    # letting one hunk vote several times in ranking.
                    run: list[tuple[int, str]] = []

                    def flush(run=run):
                        if not run:
                            return
                        first = run[0][0]
                        following = [ln[1:] for ln in body[first + 1:] if ln[:1] in ("+", " ")]
                        voice.append(Candidate(
                            "\n".join(text for _, text in run),
                            _placement("", following, marker),
                            language, code, path,
                        ))
                        run.clear()

                    for idx, raw in lines:
                        found = _split_comment(raw[1:], marker)
                        if found is None:
                            flush()
                            continue
                        before, comment = found
                        if before.strip():
                            # A trailing comment belongs to its own line's code,
                            # so it neither joins nor continues a run.
                            flush()
                            voice.append(Candidate(comment, "trailing", language, code, path))
                            continue
                        run.append((idx, comment))
                    flush()
                elif prefix == "-":
                    # Suppress only when this run of deletions is immediately
                    # followed by an addition run carrying a comment -- that is
                    # an in-place rewrite, already recorded as voice above.
                    # Every other deletion is real evidence and must survive.
                    rewritten = False
                    if seg_i + 1 < len(segments):
                        next_prefix, next_lines = segments[seg_i + 1]
                        if next_prefix == "+":
                            rewritten = any(
                                _split_comment(raw[1:], marker) is not None
                                for _, raw in next_lines
                            )
                    if rewritten:
                        continue
                    for _, raw in lines:
                        found = _split_comment(raw[1:], marker)
                        if found is None:
                            continue
                        _, comment = found
                        deleted.append(Candidate(comment, "block", language, code, path))

    return voice, deleted
