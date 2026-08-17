"""Ask the system whether the session we hold still works.

A stored session goes stale silently. The vault still has cookies, the
connection still says "connected", and the first thing that notices is an
operator halfway into a demonstration looking at a login page.

So this asks. One unauthenticated-if-stale GET at the system's own address,
with the header the executor would send: a login page or a redirect to the
identity provider means the session is gone, and the app can say so before
anybody wastes a demonstration on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from sro.application.context import RequestContext
from sro.application.ports.http import HttpCaller, TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vault import CredentialVault
from sro.domain.connection.connection import Connection, ConnectionStatus


class SessionHealth(StrEnum):
    SIGNED_IN = "signed_in"
    SIGNED_OUT = "signed_out"
    NEVER_CONNECTED = "never_connected"
    UNREACHABLE = "unreachable"
    """The system did not answer. Says nothing about the session, and must not
    be reported as a bad one -- signing in again would not fix an outage."""


@dataclass(frozen=True, slots=True)
class SessionCheck:
    connection_id: str
    target_system: str
    health: SessionHealth
    detail: str


class CheckSession:
    def __init__(self, uow: UnitOfWork, vault: CredentialVault, http: HttpCaller) -> None:
        self._uow = uow
        self._vault = vault
        self._http = http

    async def execute(self, ctx: RequestContext) -> tuple[SessionCheck, ...]:
        async with self._uow as uow:
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
        return tuple([await self._check(c) for c in connections])

    async def for_system(self, ctx: RequestContext, *, target_system: str) -> SessionCheck | None:
        """None when the tenant has no such connection at all."""
        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)
        return await self._check(connection) if connection else None

    async def _check(self, connection: Connection) -> SessionCheck:
        connection_id, system = connection.id.value, connection.target_system

        header = await self._vault.get(connection.cookie_key)
        if connection.status is ConnectionStatus.PENDING or not header:
            return SessionCheck(
                connection_id, system, SessionHealth.NEVER_CONNECTED, "nobody has signed in yet"
            )

        try:
            response = await self._http.send(
                "GET", connection.base_url, headers={"cookie": header}, timeout_s=15.0
            )
        except TargetUnreachable as error:
            return SessionCheck(connection_id, system, SessionHealth.UNREACHABLE, str(error))

        if _is_login(response.status_code, response.headers.get("location"), connection.base_url):
            return SessionCheck(
                connection_id,
                system,
                SessionHealth.SIGNED_OUT,
                "the system sent us to its login page. Connect it once more.",
            )
        return SessionCheck(connection_id, system, SessionHealth.SIGNED_IN, "the session works")


def _is_login(status_code: int, location: str | None, base_url: str) -> bool:
    """A redirect off the system's own host is the identity provider taking over.

    Judged by host rather than by any word in the URL: "login", "auth" and
    "signin" are all absent from at least one identity provider we work with,
    and present in plenty of pages that are not one.
    """
    if not 300 <= status_code < 400 or not location:
        return False
    here = urlsplit(base_url).hostname or ""
    there = urlsplit(location).hostname
    return bool(there) and there != here
