from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DIMENSIONS = 768

_BATCH = 100


class NoEmbedder:
    @property
    def available(self) -> bool:
        return False

    @property
    def dimensions(self) -> int:
        return DIMENSIONS

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(() for _ in texts)


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str, *, client: Any | None = None) -> None:
        self._model = model
        if client is not None:
            self._client = client
            return
        from google import genai

        self._client = genai.Client(api_key=api_key)

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
            if len(returned) != len(batch):
                logger.warning(
                    "embedding returned %d vectors for %d texts", len(returned), len(batch)
                )
                vectors.extend(() for _ in batch)
                continue
            vectors.extend(tuple(embedding.values or ()) for embedding in returned)
        return tuple(vectors)
