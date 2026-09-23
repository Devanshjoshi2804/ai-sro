from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vault import CredentialVault
from sro.domain.connection.connection import ConnectionId
from sro.domain.shared.errors import InvariantViolation


class StoreSessionHeaders:
    def __init__(self, uow: UnitOfWork, vault: CredentialVault) -> None:
        self._uow = uow
        self._vault = vault

    async def execute(
        self,
        ctx: RequestContext,
        *,
        connection_id: ConnectionId,
        facility: str,
        headers: dict[str, str],
    ) -> tuple[str, ...]:
        if not facility.strip():
            raise InvariantViolation(
                "session headers are stored per site: a login covers one facility's calls"
            )

        async with self._uow as uow:
            connection = await uow.connections.get(ctx.tenant_id, connection_id)

        written: list[str] = []
        for name, value in headers.items():
            key = f"{ctx.tenant_id}/{connection.target_system}/{facility}/{name.lower()}"
            await self._vault.store(key, value)
            written.append(name.lower())
        return tuple(written)
