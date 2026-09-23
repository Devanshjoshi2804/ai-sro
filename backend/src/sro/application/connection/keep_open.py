from __future__ import annotations

from dataclasses import dataclass

from sro.application.connection.release_strays import ReleaseStrayBrowsers
from sro.application.connection.sign_in import EnsureSignedIn
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.recording.recording import RecordingStatus
from sro.domain.shared.identifiers import PrincipalId


@dataclass(frozen=True, slots=True)
class Swept:
    open_now: tuple[str, ...] = ()
    left_alone: tuple[str, ...] = ()

    unreachable: tuple[str, ...] = ()
    released: tuple[str, ...] = ()


KEEPER = PrincipalId("session-keeper")


class KeepSessionsOpen:
    def __init__(
        self,
        uow: UnitOfWork,
        ensure: EnsureSignedIn,
        strays: ReleaseStrayBrowsers | None = None,
    ) -> None:
        self._uow = uow
        self._ensure = ensure
        self._strays = strays

    async def sweep(self) -> Swept:
        async with self._uow as uow:
            connections = await uow.connections.list_connected()

        open_now: list[str] = []
        busy: list[str] = []
        unreachable: list[str] = []
        for connection in connections:
            ctx = RequestContext(tenant_id=connection.tenant_id, principal_id=KEEPER)
            if await self._demonstrating(ctx):
                busy.append(connection.target_system)
                continue
            if await self._ensure.execute(ctx, target_system=connection.target_system):
                open_now.append(connection.target_system)
            else:
                unreachable.append(connection.target_system)
        released = () if busy or self._strays is None else await self._strays.execute()
        return Swept(tuple(open_now), tuple(busy), tuple(unreachable), tuple(released))

    async def _demonstrating(self, ctx: RequestContext) -> bool:
        async with self._uow as uow:
            recordings = await uow.recordings.list_for_tenant(ctx.tenant_id, limit=25)
        return any(r.status is RecordingStatus.CAPTURING for r in recordings)
