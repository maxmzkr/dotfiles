#!/usr/bin/env python3
"""Embedding and cosine ranking, behind an availability check.

numpy and sentence-transformers are optional: `available()` answers honestly and
every caller treats False as "return nothing", never as an error. They are looked
for in the venv at COMMENT_VOICE_VENV as well as on the normal path.

A few thousand 384-dimensional vectors is microseconds of brute-force cosine in
numpy, so there is no index structure and no vector database -- rows are
L2-normalised at embed time, which makes the dot product the cosine.
"""

import os
import sys
from pathlib import Path

MODEL_NAME = "all-MiniLM-L6-v2"

# System python is externally managed, so the optional deps live in a venv.
_VENV = os.environ.get("COMMENT_VOICE_VENV") or str(
    Path.home() / ".cache" / "claude" / "learning-comment-voice" / "venv"
)

_model = None


def _add_venv() -> None:
    for site in sorted(Path(_VENV).glob("lib/python3.*/site-packages")):
        if site.is_dir() and str(site) not in sys.path:
            sys.path.append(str(site))


def available() -> bool:
    for attempt in (False, True):
        if attempt:
            _add_venv()
        try:
            import numpy  # noqa: F401
            import sentence_transformers  # noqa: F401
        except ImportError:
            continue
        return True
    return False


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
