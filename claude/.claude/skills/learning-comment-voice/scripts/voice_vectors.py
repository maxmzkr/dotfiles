#!/usr/bin/env python3
"""Embedding and cosine ranking, behind an availability check.

Neither numpy nor sentence-transformers is installed on this machine, and neither
is required. Everything here is optional: `available()` answers honestly and every
caller treats False as "return nothing", never as an error.

A few thousand 384-dimensional vectors is microseconds of brute-force cosine in
numpy, so there is no index structure and no vector database -- rows are
L2-normalised at embed time, which makes the dot product the cosine.
"""

MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def available() -> bool:
    try:
        import numpy  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts: list[str]):
    import numpy as np

    raw = _load_model().encode(list(texts))
    matrix = np.asarray(raw, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def rank(query, matrix, ids: list[str], k: int) -> list[str]:
    """The k ids whose rows are nearest `query`, best first."""
    import numpy as np

    if len(ids) == 0:
        return []
    scores = matrix @ query
    order = np.argsort(-scores)[:k]
    return [ids[i] for i in order]
