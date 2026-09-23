from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    @property
    def available(self) -> bool: ...

    @property
    def dimensions(self) -> int: ...

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...
