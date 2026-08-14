"""Embeddings, through Gemini, and the no-op that stands in without a key."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DIMENSIONS = 768
"""Matches the column. `gemini-embedding-001` is asked for this size rather than
its default, because the store cannot mix two geometries in one index."""

_BATCH = 100
"""Requests are capped server-side; a catalogue is thousands of claims."""


class NoEmbedder:
    """Retrieval still works: structured filters narrow, terms order.

    Worse at synonyms, no worse at anything else — and it is never what decides
    which system or entity a request is about.
    """

    @property
    def available(self) -> bool:
        return False

    @property
    def dimensions(self) -> int:
        return DIMENSIONS

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(() for _ in texts)


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def available(self) -> bool:
        return True

    @property
    def dimensions(self) -> int:
        return DIMENSIONS

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        from google.genai import types

        vectors: list[tuple[float, ...]] = []
        for start in range(0, len(texts), _BATCH):
            batch = list(texts[start : start + _BATCH])
            response = await self._client.aio.models.embed_content(
                model=self._model,
                contents=batch,
                config=types.EmbedContentConfig(output_dimensionality=DIMENSIONS),
            )
            returned = response.embeddings or []
            # One vector per text, in order, or the store silently attaches the
            # wrong meaning to the wrong claim. A short reply is dropped rather
            # than aligned by hope.
            if len(returned) != len(batch):
                logger.warning(
                    "embedding returned %d vectors for %d texts", len(returned), len(batch)
                )
                vectors.extend(() for _ in batch)
                continue
            vectors.extend(tuple(embedding.values or ()) for embedding in returned)
        return tuple(vectors)
