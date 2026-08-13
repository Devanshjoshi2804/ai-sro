"""Give the executor the session headers a browser sends and cannot explain.

A cookie is easy: the browser hands it over and the connect flow already keeps
it. The rest are not. Blue Yonder sends `CSRF-ENCRYPT-TOKEN` on every write, the
value is issued at login, and no page, cookie or storage key exposes it -- only
the requests the application itself makes carry it.

So the value is supplied here, once per session, by whoever can read one: an
operator with dev tools open, or the capture adapter, which sees every request
header of the session it is attached to. Storing it beside the cookie is
consistent with what it is -- a bearer credential for the same session -- and
keeps it out of the skill, which is the plane that must hold no secret.

The honest limit: these expire with the session, and a run whose header has
expired fails at the first write rather than silently doing half a task.
"""

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
        """Returns the key names written, never the values."""
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
