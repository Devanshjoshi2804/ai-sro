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
            # Cookies are bearer credentials: whoever holds them is the operator
            # until they expire. They go to the vault, never to a recording.
            await self._vault.store(
                connection.session_key,
                json.dumps({"origin": connection.base_url, "cookies": cookies}),
            )
            connection.authenticated(self._clock.now())
            await uow.connections.save(connection)
            await uow.commit()
        return connection


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
