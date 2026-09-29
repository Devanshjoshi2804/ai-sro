from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.ports.pool import PoolFull
from sro.domain.shared.identifiers import BrowserSessionId
from sro.infrastructure.steel.client import SteelClient


class SteelPool:
    def __init__(
        self,
        clients: Mapping[str, SteelClient],
        *,
        containers_by_tenant: Mapping[str, Sequence[str]] | None = None,
        fallback: Sequence[str] = (),
        per_container: int,
    ) -> None:
        self._clients = dict(clients)
        self._by_tenant = {
            tenant: tuple(urls) for tenant, urls in (containers_by_tenant or {}).items()
        }
        self._fallback = tuple(fallback) or tuple(self._clients)
        self._per = per_container

    def _containers(self, tenant: str) -> tuple[str, ...]:
        return self._by_tenant.get(tenant, self._fallback)

    async def open(
        self, tenant: str, busy: Mapping[str, int], *, pinned: str | None = None
    ) -> tuple[str, str, str]:
        urls = self._containers(tenant)
        if pinned is not None and pinned in urls:
            urls = (pinned,)
        candidates = [(busy.get(url, 0), url) for url in urls if busy.get(url, 0) < self._per]
        if not candidates:
            raise PoolFull(
                f"all {len(urls)} Steel container(s) for tenant {tenant!r} hold "
                f"{self._per} context(s) each"
            )
        _, url = min(candidates, key=lambda pair: pair[0])
        session_id, context_id = await self._clients[url].open_context()
        return url, str(session_id), context_id

    async def close(self, container_url: str, context_id: str) -> None:
        await self._clients[container_url].dispose(context_id)

    async def contexts(self, container_url: str) -> frozenset[str]:
        return await self._clients[container_url].contexts()

    async def live_view_url(self, container_url: str, session_id: str) -> str | None:
        return await self._clients[container_url].live_view_url(BrowserSessionId(session_id))

    async def cdp_url(self, container_url: str) -> str:
        return await self._clients[container_url].debugger_url(BrowserSessionId(container_url))
