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
