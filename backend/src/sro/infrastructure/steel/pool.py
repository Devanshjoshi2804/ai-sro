from __future__ import annotations

from collections.abc import Mapping

from sro.application.ports.pool import PoolFull
from sro.domain.shared.identifiers import BrowserSessionId
from sro.infrastructure.steel.client import SteelClient


class SteelPool:
    def __init__(self, clients: Mapping[str, SteelClient], *, per_container: int) -> None:
        self._clients = dict(clients)
        self._per = per_container

    async def open(self, busy: Mapping[str, int]) -> tuple[str, str]:
        for url, client in self._clients.items():
            if busy.get(url, 0) < self._per:
                session = await client.open()
                return url, str(session.id)
        raise PoolFull(
            f"all {len(self._clients)} Steel container(s) hold {self._per} context(s) each"
        )

    async def close(self, container_url: str, context_id: str) -> None:
        await self._clients[container_url].close(BrowserSessionId(context_id))

    async def alive(self, container_url: str, context_id: str) -> bool:
        return await self._clients[container_url].alive(BrowserSessionId(context_id))

    async def cdp_url(self, container_url: str) -> str:
        return await self._clients[container_url].debugger_url(BrowserSessionId(container_url))
