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
            self.assertEqual(1, len(voice), "the two-line doc comment is one candidate")
            self.assertEqual("doc", voice[0].placement)
            self.assertEqual("go", voice[0].language)
            self.assertEqual(
                "// Watch returns once the job reaches a terminal state, which the\n"
                "// Failed condition only reports after backoffLimit is spent.",
                voice[0].comment,
            )
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
            self.assertEqual(1, len(got))
            self.assertIn("backoffLimit", " ".join(r.comment for r in got))


if __name__ == "__main__":
    unittest.main()
