"""Connecting a system: open a browser at it, let a human log in, keep the session.

The credentials are typed by the operator into the system's own login page, in a
browser we opened for them. They never pass through this application, are never
in a request body we handle, and are never in a recording — the capture recorder
drops credential values where they are typed.

What we keep is the *session* the login produced, encrypted in the vault. That is
what lets the executor replay a call tomorrow without a human, and what lets the
next capture start already logged in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.vault import CredentialVault
from sro.domain.connection.connection import Connection, ConnectionId, ConnectionStatus
from sro.domain.shared.identifiers import BrowserSessionId


class NotAuthenticated(Exception):
    """The browser was opened but nobody completed the login."""


@dataclass(frozen=True, slots=True)
class OpenedConnection:
    connection_id: ConnectionId
    live_view_url: str
    browser_session_id: BrowserSessionId
    debugger_url: str
    """For the capture adapter. Never put on the wire."""


class ConnectSystem:
    def __init__(
        self,
        uow: UnitOfWork,
        browser: BrowserProvider,
        clock: Clock,
        ids: IdFactory,
    ) -> None:
        self._uow = uow
        self._browser = browser
        self._clock = clock
        self._ids = ids

    async def execute(
        self,
        ctx: RequestContext,
        *,
        name: str,
        target_system: str,
        base_url: str,
    ) -> OpenedConnection:
        """Create or reuse the connection, and open a browser at its login page."""
        async with self._uow as uow:
            existing = await uow.connections.find_by_system(ctx.tenant_id, target_system)
            connection = existing or Connection(
                id=ConnectionId(f"con_{self._ids.new_recording_id().value.split('_')[-1]}"),
                tenant_id=ctx.tenant_id,
                name=name,
                target_system=target_system,
                base_url=base_url,
                created_at=self._clock.now(),
            )
            if existing is None:
                await uow.connections.add(connection)
            await uow.commit()

        session = await self._browser.open(start_url=connection.base_url)
        # Opening "at" a URL is two steps: the provider ignores the start URL
        # for an attached browser, so an unnavigated session would show the
        # operator a blank page to sign into.
        await self._browser.navigate(session.id, connection.base_url)
        return OpenedConnection(
            connection_id=connection.id,
            live_view_url=session.live_view_url,
            browser_session_id=session.id,
            debugger_url=session.debugger_url,
        )


def _cookie_header(cookies: list[dict[str, object]], origin: str) -> str:
    """The cookies this system's own host would receive, as one header.

    Scoped by host on purpose: the identity-provider cookies belong to the login
    domain and sending them to the application proves nothing, while the
    application's own session cookie is the thing being kept.
    """
    host = urlsplit(origin).hostname or ""
    wanted = [
        cookie
        for cookie in cookies
        if host.endswith(str(cookie.get("domain", "")).lstrip("."))
        or str(cookie.get("domain", "")).lstrip(".") in host
    ]
    return "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in wanted)


class StoreSession:
    """Keep the session a human just created, so nothing has to ask them again."""

    def __init__(
        self,
        uow: UnitOfWork,
        vault: CredentialVault,
        clock: Clock,
        browser: BrowserProvider,
    ) -> None:
        self._uow = uow
        self._vault = vault
        self._clock = clock
        self._browser = browser

    async def execute(
        self,
        ctx: RequestContext,
        *,
        connection_id: ConnectionId,
        browser_session_id: BrowserSessionId,
    ) -> Connection:
        cookies = list(await self._browser.session_cookies(browser_session_id))
        if not cookies:
            raise NotAuthenticated(
                "the browser holds no cookies, so the login did not complete. Sign in inside "
                "the session, then try again."
            )

        async with self._uow as uow:
            connection = await uow.connections.get(ctx.tenant_id, connection_id)
            await _keep(self._vault, connection, cookies, self._clock.now())
            await uow.connections.save(connection)
            await uow.commit()
        return connection


class RefreshSession:
    """Keep the stored session current, every time a browser proves it is signed in.

    Written once at connect, a session is stale by the following week: the
    application rotates its session cookie, the identity provider issues a new
    one, and the blob in the vault names a session the server has forgotten.
    Restoring it puts the operator back on the login page -- which is the thing
    connecting once was supposed to prevent.

    So every capture that ends signed in refreshes it. Connect once means
    connect once only if what was connected is kept alive.
    """

    def __init__(self, uow: UnitOfWork, vault: CredentialVault, clock: Clock) -> None:
        self._uow = uow
        self._vault = vault
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, cookies: list[dict[str, object]]) -> int:
        """Refresh every connection these cookies can speak for. Returns how many."""
        if not cookies:
            return 0
        async with self._uow as uow:
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
            refreshed = 0
            for connection in connections:
                # A cookie header with nothing in it means these cookies are not
                # this system's -- a second connection open in another tab, say.
                # Overwriting a good session with it would be the bug we are here
                # to fix, pointed the other way.
                header = _cookie_header(cookies, connection.base_url)
                if not header or not _still_signed_in(
                    header, await self._vault.get(connection.cookie_key)
                ):
                    continue
                await _keep(self._vault, connection, cookies, self._clock.now())
                await uow.connections.save(connection)
                refreshed += 1
            await uow.commit()
        return refreshed


def _names(header: str) -> set[str]:
    return {pair.split("=", 1)[0].strip() for pair in header.split(";") if "=" in pair}


def _still_signed_in(header: str, stored: str | None) -> bool:
    """Whether this browser ended the session logged in, judged by what it kept.

    A capture that finished on the identity provider still holds cookies -- the
    routing and anti-forgery ones survive being signed out -- so "has cookies"
    is not the question. What a logged-out browser has *lost* is the
    application's own session cookie. Refreshing from it would replace a working
    session with a logged-out one, which is worse than never refreshing at all.
    """
    return not stored or _names(stored) <= _names(header)


async def _keep(
    vault: CredentialVault,
    connection: Connection,
    cookies: list[dict[str, object]],
    now: datetime,
) -> None:
    """Both forms of the session, written together.

    Cookies are bearer credentials: whoever holds them is the operator until
    they expire. They go to the vault, never to a recording.

    The blob is what a browser restores; the header is what the executor sends.
    Keeping only the blob meant a skill kept replaying a cookie header written
    weeks earlier: two places held "the session", they aged apart, and every
    call came back 302 to the login page while the browser was happily signed
    in. One store, refreshed together.
    """
    await vault.store(
        connection.session_key,
        json.dumps({"origin": connection.base_url, "cookies": cookies}),
    )
    await vault.store(connection.cookie_key, _cookie_header(cookies, connection.base_url))
    connection.authenticated(now)


class LoadSession:
    """The stored session, for a browser that needs to start already logged in."""

    def __init__(self, uow: UnitOfWork, vault: CredentialVault) -> None:
        self._uow = uow
        self._vault = vault

    async def execute(
        self, ctx: RequestContext, *, target_system: str
    ) -> tuple[dict[str, object], ...]:
        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)

        if connection is None or connection.status is ConnectionStatus.PENDING:
            return ()

        stored = await self._vault.get(connection.session_key)
        if stored is None:
            return ()
        payload = json.loads(stored)
        cookies: list[dict[str, object]] = payload.get("cookies", [])
        return tuple(cookies)
