from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.token import TokenSource
from sro.domain.connection.connection import ConnectionId
from sro.domain.shared.errors import NotFound


@dataclass(frozen=True, slots=True)
class TokenEstablished:
    target_system: str


class EstablishToken:
    def __init__(self, uow: UnitOfWork, tokens: TokenSource | None) -> None:
        self._uow = uow
        self._tokens = tokens

    async def execute(
        self,
        ctx: RequestContext,
        *,
        connection_id: ConnectionId,
        username: str,
        password: str,
    ) -> TokenEstablished:
        if self._tokens is None:
            raise NotFound(
                "this deployment has no identity provider configured, so it cannot hold a "
                "credential of its own"
            )
        async with self._uow as uow:
            connection = await uow.connections.get(ctx.tenant_id, connection_id)
        await self._tokens.establish(
            tenant=ctx.tenant_id.value,
            system=connection.target_system,
            username=username,
            password=password,
        )
        return TokenEstablished(target_system=connection.target_system)
