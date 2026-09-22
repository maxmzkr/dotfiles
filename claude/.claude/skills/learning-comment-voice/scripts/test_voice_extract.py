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

    def test_an_unrelated_deleted_comment_survives_alongside_an_unrelated_added_one(self):
        voice, deleted = ve.extract(
            diff("a.go", "-// increment old\n x := 1\n+// note added\n y := 2")
        )
        self.assertEqual(["// note added"], comments(voice))
        self.assertEqual(
            ["// increment old"],
            comments(deleted),
            "a deletion not immediately followed by an addition is not a rewrite",
        )

    def test_a_deleted_comment_in_one_hunk_survives_an_added_comment_in_another_hunk(self):
        text = (
            "diff --git a/a.go b/a.go\n"
            "--- a/a.go\n"
            "+++ b/a.go\n"
            "@@ -1,3 +1,3 @@\n"
            "-// old note\n"
            " x := 1\n"
            "@@ -10,3 +10,4 @@\n"
            "+// new note\n"
            " y := 2\n"
        )
        voice, deleted = ve.extract(text)
        self.assertEqual(["// new note"], comments(voice))
        self.assertEqual(
            ["// old note"],
            comments(deleted),
            "hunks must not be flattened together for rewrite detection",
        )


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

    def test_a_multiline_comment_run_directly_above_a_declaration_is_doc(self):
        voice, _ = ve.extract(
            diff(
                "a.go",
                "+// Watch blocks until the job settles, which the\n"
                "+// Failed condition only reports once retries are spent.\n"
                "+func Watch() error {",
            )
        )
        self.assertEqual(1, len(voice), "the run is one comment, not one per line")
        self.assertEqual("doc", voice[0].placement, "placement comes from the run's first line")
        self.assertEqual(
            "// Watch blocks until the job settles, which the\n"
            "// Failed condition only reports once retries are spent.",
            voice[0].comment,
            "both lines verbatim, markers included",
        )

    def test_a_comment_run_separated_from_a_declaration_by_a_blank_line_is_block(self):
        voice, _ = ve.extract(
            diff(
                "a.go",
                "+// stray note about Block A, unrelated to what follows\n"
                "+\n"
                "+// Block B blocks until the job settles.\n"
                "+func BlockB() error {",
            )
        )
        self.assertEqual(2, len(voice), "the blank line breaks the run into two comments")
        self.assertEqual(
            "block",
            voice[0].placement,
            "a blank line breaks adjacency -- godoc and gofmt both require it, "
            "so this run is not a doc comment for the declaration two runs down",
        )
        self.assertEqual("doc", voice[1].placement, "this run runs straight into the declaration")


class TestCommentRuns(unittest.TestCase):
    def test_a_run_interrupted_by_code_yields_one_comment_per_run(self):
        voice, _ = ve.extract(
            diff(
                "a.go",
                "+// first run, line one\n"
                "+// first run, line two\n"
                "+x := compute()\n"
                "+// second run",
            )
        )
        self.assertEqual(
            ["// first run, line one\n// first run, line two", "// second run"],
            comments(voice),
        )

    def test_a_trailing_comment_stays_its_own_candidate(self):
        voice, _ = ve.extract(
            diff("a.go", "+// why this loop exists\n+x := 1 // seconds, not millis")
        )
        self.assertEqual(
            ["// why this loop exists", "// seconds, not millis"],
            comments(voice),
            "a trailing comment belongs to its line's code, not to the run above it",
        )
        self.assertEqual(["block", "trailing"], [c.placement for c in voice])

    def test_a_run_split_across_addition_segments_is_not_joined(self):
        voice, _ = ve.extract(
            diff("a.go", "+// added above\n x := 1\n+// added below")
        )
        self.assertEqual(["// added above", "// added below"], comments(voice))


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

    def test_code_excludes_a_python_docstring(self):
        voice, _ = ve.extract(
            diff(
                "run.py",
                "+# the vendor returns 200 on failure\n"
                "+def check(resp):\n"
                '+    """Raise unless the body says ok; the status line lies."""\n'
                "+    assert resp.json()['ok']",
            )
        )
        self.assertNotIn("the status line lies", voice[0].code)
        self.assertIn("def check(resp):", voice[0].code)

    def test_code_excludes_a_c_style_block_comment(self):
        voice, _ = ve.extract(
            diff(
                "a.go",
                "+// why this is here\n"
                "+/*\n"
                "+ * The vendor sends the fields out of order.\n"
                "+ */\n"
                "+x := compute()",
            )
        )
        self.assertNotIn("out of order", voice[0].code)
        self.assertIn("x := compute()", voice[0].code)

    def test_code_keeps_the_code_half_of_a_trailing_comment_but_not_the_comment(self):
        voice, _ = ve.extract(diff("a.go", "+x := 1 // seconds, not millis"))
        self.assertIn("x := 1", voice[0].code)
        self.assertNotIn("seconds, not millis", voice[0].code)


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
