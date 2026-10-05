#!/usr/bin/env python3
"""Tests for voice_pr.

Each test builds the version history its assertions depend on. `gh` posts LF and
the browser saves CRLF, so `posted` and `by_hand` are the two ways a version can
arrive, and the line endings are the whole provenance signal under test.
"""

import unittest

import voice_pr as vp


def posted(at: str, body: str) -> vp.Version:
    return vp.Version(at, body)


def by_hand(at: str, body: str) -> vp.Version:
    return vp.Version(at, body.replace("\n", "\r\n"))


def run(versions):
    return vp.extract(versions, code="title\n\nfile.go", path="#1")


class TestExtract(unittest.TestCase):
    def test_a_rewrite_of_the_posted_draft_is_voice_and_the_draft_is_deleted(self):
        voice, deleted = run([
            posted("2026-09-01T10:00", "## Problem\n\nA long draft paragraph.\n"),
            by_hand("2026-09-01T11:00", "## Problem\n\nShort and his.\n"),
        ])

        self.assertEqual(["Short and his."], [c.comment for c in voice])
        self.assertEqual(["A long draft paragraph."], [c.comment for c in deleted])

    def test_a_run_of_hand_edits_is_compared_against_the_draft_before_it(self):
        voice, _ = run([
            posted("2026-09-01T10:00", "Draft."),
            by_hand("2026-09-01T11:00", "First pass.\n\nSecond paragraph."),
            by_hand("2026-09-01T11:05", "Final pass.\n\nSecond paragraph."),
        ])

        self.assertEqual(["Final pass.\n\nSecond paragraph."], [c.comment for c in voice])

    def test_a_posted_edit_after_his_is_not_voice(self):
        voice, _ = run([
            posted("2026-09-01T10:00", "Draft."),
            by_hand("2026-09-01T11:00", "His.\n"),
            posted("2026-09-01T12:00", "His.\n\nClaude added this.\n"),
        ])

        self.assertEqual(["His."], [c.comment for c in voice])

    def test_a_pr_opened_in_the_browser_is_voice_in_full(self):
        voice, deleted = run([by_hand("2026-09-01T10:00", "## Problem\n\nAll his.")])

        self.assertEqual(["## Problem\n\nAll his."], [c.comment for c in voice])
        self.assertEqual([], deleted)

    def test_an_uploaded_screenshot_is_not_voice(self):
        voice, _ = run([
            posted("2026-09-01T10:00", "## Problem\n\nDraft."),
            by_hand("2026-09-01T11:00", '## Problem\n\n<img width="10" alt="image" src="https://x/y" />'),
        ])

        self.assertEqual([], voice)

    def test_only_posted_versions_yield_nothing(self):
        voice, deleted = run([
            posted("2026-09-01T10:00", "Draft."),
            posted("2026-09-01T11:00", "Redraft."),
        ])

        self.assertEqual([], voice)
        self.assertEqual([], deleted)

    def test_a_body_with_no_line_break_is_not_attributed(self):
        # Without a line ending there is no signal, so it cannot be claimed as his.
        voice, _ = run([
            posted("2026-09-01T10:00", "Draft.\n"),
            by_hand("2026-09-01T11:00", "One line"),
        ])

        self.assertEqual([], voice)

    def test_versions_are_ordered_by_time_not_by_arrival(self):
        voice, _ = run([
            by_hand("2026-09-01T11:00", "His.\n"),
            posted("2026-09-01T10:00", "Draft.\n"),
        ])

        self.assertEqual(["His."], [c.comment for c in voice])


if __name__ == "__main__":
    unittest.main()
