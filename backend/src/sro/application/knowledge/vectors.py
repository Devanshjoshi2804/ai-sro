"""Embedding, treated as the optional thing it is.

Similarity only *orders* what a structured filter already chose, so a backend
that is unreachable, unauthenticated or slow must cost the caller its ordering
and nothing else. Measured the hard way: with a bad key, an unguarded call took
down every conversation and every ingest, for a feature whose absence is a
supported deployment.
"""

from __future__ import annotations

import logging

from sro.application.ports.embedding import Embedder

logger = logging.getLogger(__name__)


async def embed_or_none(
    embedder: Embedder, texts: tuple[str, ...]
) -> tuple[tuple[float, ...], ...]:
    """One vector per text, or an empty one each. Never raises."""
    if not texts:
        return ()
    if not embedder.available:
        return tuple(() for _ in texts)
    try:
        vectors = await embedder.embed(texts)
    except Exception:
        # Broad on purpose: every SDK has its own exception tree, and the answer
        # is the same for all of them -- carry on without an ordering.
        logger.warning("embedding unavailable; retrieval falls back to matching terms")
        return tuple(() for _ in texts)

    if len(vectors) != len(texts):
        logger.warning("embedding returned %d vectors for %d texts", len(vectors), len(texts))
        return tuple(() for _ in texts)
    return vectors
