from __future__ import annotations

import logging

from sro.application.ports.embedding import Embedder

logger = logging.getLogger(__name__)


async def embed_or_none(
    embedder: Embedder, texts: tuple[str, ...]
) -> tuple[tuple[float, ...], ...]:
    if not texts:
        return ()
    if not embedder.available:
        return tuple(() for _ in texts)
    try:
        vectors = await embedder.embed(texts)
    except Exception:
        logger.warning("embedding unavailable; retrieval falls back to matching terms")
        return tuple(() for _ in texts)

    if len(vectors) != len(texts):
        logger.warning("embedding returned %d vectors for %d texts", len(vectors), len(texts))
        return tuple(() for _ in texts)
    return vectors
