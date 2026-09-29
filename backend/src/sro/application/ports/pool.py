from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class PoolFull(Exception):
    code = "pool_full"


class BrowserPool(Protocol):
    async def open(
        self, tenant: str, busy: Mapping[str, int], *, pinned: str | None = None
    ) -> tuple[str, str, str]: ...

    async def close(self, container_url: str, context_id: str) -> None: ...

    async def contexts(self, container_url: str) -> frozenset[str]: ...

    async def cdp_url(self, container_url: str) -> str: ...

    async def live_view_url(self, container_url: str, session_id: str) -> str | None: ...
