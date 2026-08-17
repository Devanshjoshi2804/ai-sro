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

from sro.application.connection.connect_system import RefreshSession
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
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
    def __init__(
        self,
        uow: UnitOfWork,
        vault: CredentialVault,
        http: HttpCaller,
        browser: BrowserProvider | None = None,
        refresh: RefreshSession | None = None,
    ) -> None:
        self._uow = uow
        self._vault = vault
        self._http = http
        self._browser = browser
        self._refresh = refresh

    async def execute(self, ctx: RequestContext) -> tuple[SessionCheck, ...]:
        async with self._uow as uow:
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
        return tuple([await self._check(ctx, c) for c in connections])

    async def for_system(self, ctx: RequestContext, *, target_system: str) -> SessionCheck | None:
        """None when the tenant has no such connection at all."""
        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)
        return await self._check(ctx, connection) if connection else None

    async def _check(self, ctx: RequestContext, connection: Connection) -> SessionCheck:
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
            # Before saying so: is somebody signed in right now in a browser we
            # opened? An operator who signs in and closes the tab has done the
            # whole job, and three times today a good session was thrown away
            # because the console happened not to be watching that window.
            if await self._adopt(ctx, connection):
                return SessionCheck(
                    connection_id, system, SessionHealth.SIGNED_IN, "the session works"
                )
            return SessionCheck(
                connection_id,
                system,
                SessionHealth.SIGNED_OUT,
                "the system sent us to its login page. Connect it once more.",
            )
        return SessionCheck(connection_id, system, SessionHealth.SIGNED_IN, "the session works")

    async def _adopt(self, ctx: RequestContext, connection: Connection) -> bool:
        """Take a session from a browser that is signed in, if one is open.

        Nothing here signs anybody in: it looks at browsers this deployment
        already has open and keeps what an operator has already done. A live
        browser holding a cookie for this system is a completed login that
        nobody wrote down.
        """
        if self._browser is None or self._refresh is None:
            return False
        try:
            live = await self._browser.live_sessions()
        except BrowserUnavailable:
            return False

        for session_id in live:
            try:
                cookies = list(await self._browser.session_cookies(session_id))
            except BrowserUnavailable:
                continue
            # Trusted: the browser is open and holds the application's own
            # cookie, which is what signing in produces and what an identity
            # provider's cookies alone are not.
            if await self._refresh.execute(ctx, cookies=cookies, trusted=True):
                return True
        return False


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
