#!/usr/bin/env python3
"""Tests for voice_commit.

The extraction tests build the two messages their assertions depend on. The
reflog tests build a throwaway repo and reword with a scripted editor, because
the `rebase (reword)` reflog entry is the whole provenance signal under test and
only git itself can produce it.
"""

import os
import subprocess
import tempfile
import unittest

import voice_commit as vc


def run(before, after):
    return vc.extract(before, after, code="a.go\nb.go", path="abc1234", commit="abc1234")


class TestExtract(unittest.TestCase):
    def test_a_rewritten_paragraph_is_voice_and_the_draft_is_deleted(self):
        voice, deleted = run(
            "feat: subject\n\nA long draft paragraph.\n",
            "feat: subject\n\nShort and his.\n",
        )

        self.assertEqual(["Short and his."], [c.comment for c in voice])
        self.assertEqual(["A long draft paragraph."], [c.comment for c in deleted])

    def test_a_rewritten_subject_is_voice(self):
        voice, _ = run("feat: the draft subject\n\nBody.\n", "feat: his subject\n\nBody.\n")

        self.assertEqual(["feat: his subject"], [c.comment for c in voice])

    def test_every_new_paragraph_lands_in_one_candidate(self):
        voice, _ = run("feat: s\n\nDraft.\n", "feat: s\n\nFirst.\n\nSecond.\n")

        self.assertEqual(["First.\n\nSecond."], [c.comment for c in voice])

    def test_an_unchanged_message_yields_nothing(self):
        voice, deleted = run("feat: s\n\nBody.\n", "feat: s\n\nBody.\n")

        self.assertEqual([], voice)
        self.assertEqual([], deleted)

    def test_a_rewrapped_paragraph_counts_as_his(self):
        voice, deleted = run("feat: s\n\nOne long line that\nwraps here.\n", "feat: s\n\nOne long line\nthat wraps here.\n")

        self.assertEqual(["One long line\nthat wraps here."], [c.comment for c in voice])
        self.assertEqual(["One long line that\nwraps here."], [c.comment for c in deleted])

    def test_git_comment_lines_are_not_message(self):
        voice, _ = run("feat: s\n", "feat: s\n\n# Conflicts:\n#\tfile.go\n")

        self.assertEqual([], voice)


def git(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout


def commit(cwd, name, message):
    with open(os.path.join(cwd, name), "w") as fh:
        fh.write(name)
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", message)


def reword_first_of_last(cwd, n, message):
    """Interactive rebase over the last n commits, rewording the first with message."""
    env = dict(os.environ)
    env["GIT_SEQUENCE_EDITOR"] = "sed -i '1s/^pick/reword/'"
    env["GIT_EDITOR"] = f"sh -c 'printf \"%s\" \"$0\" > \"$1\"' '{message}'"
    git(cwd, "rebase", "-q", "-i", f"HEAD~{n}", env=env)


class TestRewords(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "t")
        commit(self.repo, "base", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_reword_pairs_with_the_commit_it_rewrote(self):
        commit(self.repo, "a", "feat: draft\n\nDraft body.")
        commit(self.repo, "b", "feat: second")
        original = git(self.repo, "rev-parse", "HEAD~1").strip()

        reword_first_of_last(self.repo, 2, "feat: his\n\nHis body.\n")

        pairs = vc.rewords(self.repo)
        self.assertEqual(1, len(pairs))
        old, new = pairs[0]
        self.assertEqual(original, old)
        self.assertEqual("feat: his\n\nHis body.\n", git(self.repo, "log", "-1", "--format=%B", new).rstrip("\n") + "\n")

    def test_a_reword_whose_parent_changed_still_pairs(self):
        commit(self.repo, "a", "feat: first")
        commit(self.repo, "b", "feat: draft")
        original = git(self.repo, "rev-parse", "HEAD").strip()

        env = dict(os.environ)
        env["GIT_SEQUENCE_EDITOR"] = "sed -i -e '1s/^pick/reword/' -e '2s/^pick/reword/'"
        env["GIT_EDITOR"] = "sh -c 'printf \"feat: his\\n\" > \"$1\"' --"
        git(self.repo, "rebase", "-q", "-i", "HEAD~2", env=env)

        olds = [old for old, _ in vc.rewords(self.repo)]
        self.assertIn(original, olds)

    def test_amends_are_not_rewords(self):
        commit(self.repo, "a", "feat: draft")
        git(self.repo, "commit", "-q", "--amend", "-m", "feat: claude's rewrite")

        self.assertEqual([], vc.rewords(self.repo))

    def test_only_the_latest_rebase_is_read(self):
        commit(self.repo, "a", "feat: draft")
        commit(self.repo, "b", "feat: second")
        reword_first_of_last(self.repo, 2, "feat: earlier\n")
        reword_first_of_last(self.repo, 1, "feat: later\n")

        pairs = vc.rewords(self.repo)
        self.assertEqual(["feat: later"], [git(self.repo, "log", "-1", "--format=%s", new).strip() for _, new in pairs])


if __name__ == "__main__":
    unittest.main()
