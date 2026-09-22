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
