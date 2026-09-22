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

def build(corpus_dir: Path, index_dir: Path) -> int:
    """Rebuild the index. Returns the number of records indexed."""
    if not vv.available():
        return 0
    records = vc.load_records(corpus_dir)
    if not records:
        return 0

    try:
        import numpy as np

        ids = [r.id for r in records]
        desc = vv.embed([_description(r) for r in records])
        code = vv.embed([r.code for r in records])

        index_dir.mkdir(parents=True, exist_ok=True)
        np.savez(index_dir / "vectors.npz", ids=np.array(ids), desc=desc, code=code)
        return len(ids)
    except Exception:
        # Same reason `load` swallows: the packages importing does not mean the
        # model is on disk, and a rebuild that cannot reach huggingface must
        # report an empty index rather than abort the capture run around it.
        return 0


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
    ap.add_argument("--index", type=Path, default=None,
                    help="default: an `index` directory beside --corpus")
    args = ap.parse_args(argv)
    # Derived from --corpus rather than its own default, so that pointing --corpus
    # somewhere else moves the index with it -- voice_query reads it from
    # exactly here.
    index = args.index or args.corpus.parent / "index"
    count = build(args.corpus, index)
    print(f"indexed {count} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
