"""Sign systems back in before their sessions die, not after.

Everything else here reacts: a run fails, a session is refreshed, the run is
retried. That works and it is not enough -- the first batch of the morning
should not be the thing that discovers the weekend expired the session, and an
operator opening the console at 8am should not be looking at a login page.

So a keeper wakes up, asks each connected system whether its session is working
and how old it is, and replaces the ones that are past half their measured
life. What "half their life" means is learned per system rather than set here.

Two things it will not do. It never signs in while somebody is demonstrating,
because this WMS permits one session and taking it would sign the operator out
mid-task. And it never signs in during an outage, because burning credentials
against a system that cannot answer is how an account gets locked.
"""

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
    """Systems somebody is demonstrating against, and why nothing was touched."""

    unreachable: tuple[str, ...] = ()
    released: tuple[str, ...] = ()
    """Browsers given back because nothing claimed them. This deployment has
    one, and a session that outlived whatever opened it holds it forever."""


KEEPER = PrincipalId("session-keeper")
"""Whose name goes on a login nobody asked for. A refresh is not attributable
to whoever happened to ask last, and an audit trail that says so is worth the
one extra constant."""


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
        """One pass over every connected system, in every tenant.

        Nobody is making this request, so there is no tenant to scope it to --
        the keeper reads the connection list itself and acts for each tenant in
        turn, which is the one place in this codebase that crosses that line.
        """
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
        # Last, and only when nobody is demonstrating: a sign-in opens a
        # browser of its own, and reaping between opening and using it would
        # take the slot out from under the thing that just asked for it.
        released = () if busy or self._strays is None else await self._strays.execute()
        return Swept(tuple(open_now), tuple(busy), tuple(unreachable), tuple(released))

    async def _demonstrating(self, ctx: RequestContext) -> bool:
        """Whether anybody is teaching right now. Their browser holds the
        session this would otherwise replace."""
        async with self._uow as uow:
            recordings = await uow.recordings.list_for_tenant(ctx.tenant_id, limit=25)
        return any(r.status is RecordingStatus.CAPTURING for r in recordings)
