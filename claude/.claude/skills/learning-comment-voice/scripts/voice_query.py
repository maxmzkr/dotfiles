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
import voice_index as vi
import voice_vectors as vv

DEFAULT_CORPUS = vc.DEFAULT_CORPUS

VECTOR_MIN_ENTRIES = 150
VECTOR_MIN_CHARS = 20000


def facet_filter(records, *, language, placement, kind):
    out = records
    if language:
        out = [r for r in out if r.language == language]
    if placement:
        out = [r for r in out if r.placement == placement]
    if kind:
        out = [r for r in out if r.kind == kind]
    return out


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
    ap.add_argument("--backend", choices=("all", "desc", "code"),
                     help="override automatic selection")
    args = ap.parse_args(argv)

    records = facet_filter(
        vc.load_records(args.corpus),
        language=args.language,
        placement=args.placement,
        kind=args.kind,
    )

    # The index always sits beside the corpus it was built from, so a --corpus
    # anywhere puts this reader and voice_index's builder on the same directory.
    index = vi.load(args.corpus.parent / "index")
    backend = args.backend or choose_backend(records, index)

    if backend != "all" and index is not None and vv.available():
        try:
            by_id = {r.id: r for r in records}
            rows = [i for i, rid in enumerate(index["ids"]) if rid in by_id]
            if rows:
                matrix = index[backend][rows]
                ids = [index["ids"][i] for i in rows]
                query = vv.embed([args.situation])[0]
                records = [by_id[i] for i in vv.rank(query, matrix, ids, k=args.k or 5)]
        except Exception:
            # `available()` only proves the packages import. The model itself is
            # downloaded on first use, so embedding raises offline -- and the
            # skill's promise is that this lookup never blocks a rewrite. Fall
            # through with the facet-filtered records, which is what the
            # no-index path returns anyway.
            pass

    if args.k is not None:
        records = records[: args.k]
    if records:
        print(render(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
