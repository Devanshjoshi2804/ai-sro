"""Text to a vector, for ordering candidates a structured filter already chose.

Optional in the same way transcription is: without a backend, retrieval falls
back to matching terms, which is worse at synonyms and no worse at anything
else. It is never the thing that decides which system or which entity a request
is about -- that is a filter, not a distance.
"""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    @property
    def available(self) -> bool: ...

    @property
    def dimensions(self) -> int:
        """Fixed per deployment: the column is sized by it, so changing model
        means re-embedding rather than mixing two geometries in one index."""
        ...

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """One vector per text, in order. Empty when unavailable."""
        ...
