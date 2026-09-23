from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlsplit

from sro.application.connection.browsers import Browsers
from sro.application.connection.cookies import belongs_to
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.vault import CredentialVault
from sro.domain.connection.connection import Connection, ConnectionId, ConnectionStatus
from sro.domain.shared.identifiers import BrowserSessionId


class NotAuthenticated(Exception):
    code = "not_authenticated"


@dataclass(frozen=True, slots=True)
class OpenedConnection:
    connection_id: ConnectionId
    live_view_url: str
    browser_session_id: BrowserSessionId
    debugger_url: str

    target_system: str
    name: str


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
        base_url: str,
        name: str | None = None,
        target_system: str | None = None,
    ) -> OpenedConnection:
        target_system = (target_system or "").strip() or _system_from(base_url)
        name = (name or "").strip() or _name_from(base_url)
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
        await self._browser.forget_everything(session.id)
        await self._browser.navigate(session.id, connection.base_url)
        return OpenedConnection(
            connection_id=connection.id,
            live_view_url=session.live_view_url,
            browser_session_id=session.id,
            debugger_url=session.debugger_url,
            target_system=connection.target_system,
            name=connection.name,
        )


_KNOWN_SYSTEMS = {
    "jdadelivers.com": "blue_yonder",
    "blueyonder.com": "blue_yonder",
    "manh.com": "manhattan",
    "sap.com": "sap",
}


def _system_from(base_url: str) -> str:
    host = (urlsplit(base_url).hostname or "").lower()
    for domain, system in _KNOWN_SYSTEMS.items():
        if host == domain or host.endswith(f".{domain}"):
            return system
    parts = [part for part in host.split(".") if part not in {"www", "com", "co", "uk", "net"}]
    return (parts[-1] if parts else host).replace("-", "_") or "system"


def _facility_of(base_url: str) -> str:
    query = dict(parse_qsl(urlsplit(base_url).query))
    for key in ("siteId", "site", "facility", "warehouseId"):
        if query.get(key):
            return str(query[key])
    return "default"


def _name_from(base_url: str) -> str:
    return urlsplit(base_url).hostname or base_url


def _cookie_header(cookies: list[dict[str, object]], origin: str) -> str:
    wanted = [cookie for cookie in cookies if belongs_to(cookie, origin)]
    return "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in wanted)


class StoreSession:
    def __init__(
        self,
        uow: UnitOfWork,
        vault: CredentialVault,
        clock: Clock,
        browser: BrowserProvider,
        browsers: Browsers,
    ) -> None:
        self._uow = uow
        self._vault = vault
        self._clock = clock
        self._browser = browser
        self._browsers = browsers

    async def execute(
        self,
        ctx: RequestContext,
        *,
        connection_id: ConnectionId,
        browser_session_id: BrowserSessionId,
    ) -> Connection:
        await self._browsers.session(ctx, browser_session_id)
        cookies = list(await self._browser.session_cookies(browser_session_id))
        async with self._uow as uow:
            connection = await uow.connections.get(ctx.tenant_id, connection_id)
        if not _cookie_header(cookies, connection.base_url):
            raise NotAuthenticated(
                "nobody has signed in yet: the browser holds no session for this system."
            )

        headers = await self._browser.session_headers(browser_session_id, connection.base_url)

        async with self._uow as uow:
            connection = await uow.connections.get(ctx.tenant_id, connection_id)
            await _keep(self._vault, connection, cookies, self._clock.now())
            for name, value in headers.items():
                await self._vault.store(
                    f"{ctx.tenant_id}/{connection.target_system}/"
                    f"{_facility_of(connection.base_url)}/{name}",
                    value,
                )
            await uow.connections.save(connection)
            await uow.commit()
        return connection


class RefreshSession:
    def __init__(self, uow: UnitOfWork, vault: CredentialVault, clock: Clock) -> None:
        self._uow = uow
        self._vault = vault
        self._clock = clock

    async def execute(
        self,
        ctx: RequestContext,
        *,
        cookies: list[dict[str, object]],
        trusted: bool = False,
    ) -> int:
        if not cookies:
            return 0
        async with self._uow as uow:
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
            refreshed = 0
            for connection in connections:
                header = _cookie_header(cookies, connection.base_url)
                if not header or not (
                    trusted
                    or _still_signed_in(header, await self._vault.get(connection.cookie_key))
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
    return not stored or _names(stored) <= _names(header)


async def _keep(
    vault: CredentialVault,
    connection: Connection,
    cookies: list[dict[str, object]],
    now: datetime,
) -> None:
    await vault.store(
        connection.session_key,
        json.dumps({"origin": connection.base_url, "cookies": cookies}),
    )
    header = _cookie_header(cookies, connection.base_url)
    await vault.store(connection.cookie_key, header)
    await vault.store(
        f"{connection.cookie_key.rsplit('/', 1)[0]}/{_facility_of(connection.base_url)}/cookie",
        header,
    )
    connection.authenticated(now)


class LoadSession:
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


class AcknowledgeFailures:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self, ctx: RequestContext, *, connection_id: ConnectionId, reason: str
    ) -> Connection:
        async with self._uow as uow:
            connection = await uow.connections.get(ctx.tenant_id, connection_id)
            connection.acknowledge_failures(self._clock.now(), ctx.principal_id.value, reason)
            await uow.connections.save(connection)
            await uow.commit()
        return connection
