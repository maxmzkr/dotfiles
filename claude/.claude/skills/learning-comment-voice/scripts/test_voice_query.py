#!/usr/bin/env python3
"""Tests for voice_query."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

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

    def test_kind_narrows(self):
        recs = [
            vc.Record(id="1", comment="// a", placement="block", language="go", kind="warning",
                      code="x", description="d", enclosing=None, repo="r", path="p", commit="c", captured="2026-09-18"),
            vc.Record(id="2", comment="// b", placement="block", language="go", kind="why",
                      code="x", description="d", enclosing=None, repo="r", path="p", commit="c", captured="2026-09-18"),
        ]
        got = vq.facet_filter(recs, language=None, placement=None, kind="warning")
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
                rc = vq.main(["--corpus", d, "--situation", "x", "-k", "2"])
        self.assertEqual(0, rc)
        self.assertEqual(2, out.getvalue().count("// comment"))

    def test_all_backend_returns_everything_when_k_is_absent(self):
        with tempfile.TemporaryDirectory() as d:
            for n in range(5):
                stored(Path(d), comment=f"// comment {n}", code=f"x{n}")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = vq.main(["--corpus", d, "--situation", "x"])
        self.assertEqual(0, rc)
        self.assertEqual(5, out.getvalue().count("// comment"))

    def test_kind_narrows_the_printed_output(self):
        with tempfile.TemporaryDirectory() as d:
            stored(Path(d), kind="warning")
            stored(Path(d), comment="// b", code="y", kind="why")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = vq.main(["--corpus", d, "--situation", "x", "--kind", "warning"])
        self.assertEqual(0, rc)
        self.assertIn("// the API replays these in sequence", out.getvalue())
        self.assertNotIn("// b", out.getvalue())

    def test_non_matching_kind_prints_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            stored(Path(d), kind="why")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = vq.main(["--corpus", d, "--situation", "x", "--kind", "warning"])
        self.assertEqual(0, rc)
        self.assertEqual("", out.getvalue().strip())


class FakeMatrix:
    """Just enough of an ndarray for `index[backend][rows]`.

    Each row is a string naming the record it belongs to, so a row/id
    misalignment is visible in the assertion rather than silently returning a
    confidently wrong exemplar -- which is exactly how this block would fail.
    """

    def __init__(self, rows):
        self.rows = list(rows)

    def __getitem__(self, idx):
        return FakeMatrix(self.rows[i] for i in idx)


class TestVectorRanking(unittest.TestCase):
    """The ranking block, exercised without numpy or sentence-transformers."""

    def test_rows_stay_aligned_with_ids_across_a_reordered_and_stale_index(self):
        with tempfile.TemporaryDirectory() as d:
            alpha = stored(Path(d), comment="// alpha", code="x")
            beta = stored(Path(d), comment="// beta", code="y")
            # Index order is neither corpus load order nor a subset of it: beta
            # first, a record deleted from the corpus in the middle.
            index = {
                "ids": [beta.id, "a-stale-id", alpha.id],
                "desc": FakeMatrix([f"row-{beta.id}", "row-stale", f"row-{alpha.id}"]),
            }
            seen = {}

            def fake_rank(query, matrix, ids, k):
                seen["pairs"] = list(zip(ids, matrix.rows))
                seen["query"] = query
                return list(reversed(ids))[:k]

            out = io.StringIO()
            with mock.patch.object(vq.vi, "load", return_value=index), \
                 mock.patch.object(vq.vv, "available", return_value=True), \
                 mock.patch.object(vq.vv, "embed", return_value=["a-query-vector"]), \
                 mock.patch.object(vq.vv, "rank", side_effect=fake_rank), \
                 redirect_stdout(out):
                rc = vq.main(["--corpus", d, "--situation", "ordering", "--backend", "desc"])

        self.assertEqual(0, rc)
        self.assertEqual(
            [(beta.id, f"row-{beta.id}"), (alpha.id, f"row-{alpha.id}")],
            seen["pairs"],
            "each ranked row must be the row of the id handed alongside it",
        )
        self.assertEqual("a-query-vector", seen["query"])
        self.assertLess(
            out.getvalue().index("// alpha"),
            out.getvalue().index("// beta"),
            "output order follows rank's order, not corpus load order",
        )

    def test_an_embedding_failure_degrades_to_the_facet_filtered_records(self):
        with tempfile.TemporaryDirectory() as d:
            alpha = stored(Path(d), comment="// alpha", code="x")
            stored(Path(d), comment="// beta", code="y", language="python")
            # The index must match a surviving record, or the ranking block is
            # skipped for want of rows and the test proves nothing.
            index = {"ids": [alpha.id], "desc": FakeMatrix([f"row-{alpha.id}"])}

            def offline(_texts):
                raise OSError("We couldn't connect to huggingface.co")

            out = io.StringIO()
            with mock.patch.object(vq.vi, "load", return_value=index), \
                 mock.patch.object(vq.vv, "available", return_value=True), \
                 mock.patch.object(vq.vv, "embed", side_effect=offline), \
                 redirect_stdout(out):
                rc = vq.main(["--corpus", d, "--situation", "ordering",
                              "--language", "go", "--backend", "desc"])

        self.assertEqual(0, rc, "the lookup must never block the rewrite it serves")
        self.assertIn("// alpha", out.getvalue())
        self.assertNotIn("// beta", out.getvalue(), "the facet filter still applies")


class TestIndexLocation(unittest.TestCase):
    def test_builder_and_reader_agree_on_a_non_default_corpus(self):
        import voice_index as vi

        with tempfile.TemporaryDirectory() as d:
            corpus = Path(d) / "mycorpus" / "corpus"
            stored(corpus)
            built, read = {}, {}

            def record_build(corpus_dir, index_dir):
                built["dir"] = index_dir
                return 0

            def record_load(index_dir):
                read["dir"] = index_dir
                return None

            with mock.patch.object(vi, "build", side_effect=record_build), \
                 redirect_stdout(io.StringIO()):
                vi.main(["--corpus", str(corpus)])
            with mock.patch.object(vq.vi, "load", side_effect=record_load), \
                 redirect_stdout(io.StringIO()):
                vq.main(["--corpus", str(corpus), "--situation", "x"])

        self.assertEqual(built["dir"], read["dir"])
        self.assertEqual(corpus.parent / "index", built["dir"])


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

    def test_exactly_min_entries_with_ample_chars_uses_desc(self):
        records = self._records(vq.VECTOR_MIN_ENTRIES, comment_len=200)
        self.assertEqual("desc", vq.choose_backend(records, index={"ids": ["0"]}))

    def test_one_fewer_than_min_entries_stays_on_all(self):
        records = self._records(vq.VECTOR_MIN_ENTRIES - 1, comment_len=200)
        self.assertEqual("all", vq.choose_backend(records, index={"ids": ["0"]}))

    def test_exactly_min_chars_with_ample_entries_uses_desc(self):
        n = 1000  # well above VECTOR_MIN_ENTRIES
        comment_len = vq.VECTOR_MIN_CHARS // n
        records = self._records(n, comment_len=comment_len)
        self.assertEqual(vq.VECTOR_MIN_CHARS, sum(len(r.comment) for r in records))
        self.assertEqual("desc", vq.choose_backend(records, index={"ids": ["0"]}))

    def test_one_char_fewer_than_min_stays_on_all(self):
        n = 1000  # well above VECTOR_MIN_ENTRIES; same record count as the exact-boundary case
        comment_len = vq.VECTOR_MIN_CHARS // n
        records = self._records(n - 1, comment_len=comment_len) + self._records(1, comment_len=comment_len - 1)
        self.assertEqual(n, len(records))
        self.assertEqual(vq.VECTOR_MIN_CHARS - 1, sum(len(r.comment) for r in records))
        self.assertEqual("all", vq.choose_backend(records, index={"ids": ["0"]}))


if __name__ == "__main__":
    unittest.main()
