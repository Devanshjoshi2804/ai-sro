from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class PoolFull(Exception):
    code = "pool_full"


class BrowserPool(Protocol):
    async def open(self, tenant: str, busy: Mapping[str, int]) -> tuple[str, str]: ...

    async def close(self, container_url: str, context_id: str) -> None: ...

    async def alive(self, container_url: str, context_id: str) -> bool: ...

    async def cdp_url(self, container_url: str) -> str: ...
