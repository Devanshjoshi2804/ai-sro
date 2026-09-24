from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.connection.connection import Connection


class ListConnections:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> tuple[Connection, ...]:
        async with self._uow as uow:
            return await uow.connections.list_for_tenant(ctx.tenant_id)
