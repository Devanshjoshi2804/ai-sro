from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from sro.application.connection.browsers import Browsers
from sro.application.connection.connect_system import RefreshSession
from sro.application.context import RequestContext
from sro.application.execution.headers import client_headers, resolve_headers
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.http import HttpCaller, TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vault import CredentialVault
from sro.domain.connection.connection import Connection, ConnectionStatus
from sro.domain.skill.plan import NetworkPlan

_LOGIN_SCAN_CHARS = 200_000

_LIBRARY_PAGE = 200


class SessionHealth(StrEnum):
    SIGNED_IN = "signed_in"
    SIGNED_OUT = "signed_out"
    NEVER_CONNECTED = "never_connected"
    UNREACHABLE = "unreachable"


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
        browsers: Browsers | None = None,
    ) -> None:
        self._uow = uow
        self._vault = vault
        self._http = http
        self._browser = browser
        self._refresh = refresh
        self._browsers = browsers

    async def execute(self, ctx: RequestContext) -> tuple[SessionCheck, ...]:
        async with self._uow as uow:
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
        return tuple([await self._check(ctx, c) for c in connections])

    async def for_system(self, ctx: RequestContext, *, target_system: str) -> SessionCheck | None:
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

        proved = await self._proved_read(ctx, system)
        probe = str(proved[0].url) if proved else connection.base_url
        headers = {"cookie": header}
        if proved is not None:
            plan, session_scope = proved
            resolved = await resolve_headers(
                plan.headers,
                values={},
                vault=self._vault,
                scope=str(ctx.tenant_id),
                session_scope=session_scope,
            )
            headers = {
                "cookie": header,
                **client_headers(plan.headers, probe),
                **resolved.headers,
            }
        try:
            response = await self._http.send("GET", probe, headers=headers, timeout_s=15.0)
        except TargetUnreachable as error:
            return SessionCheck(connection_id, system, SessionHealth.UNREACHABLE, str(error))

        if _is_login(
            response.status_code,
            response.headers.get("location"),
            connection.base_url,
            response.text,
        ):
            if await self._adopt(ctx, connection) and await self._works(
                ctx, connection, probe, headers
            ):
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

    async def _works(
        self,
        ctx: RequestContext,
        connection: Connection,
        probe: str,
        headers: dict[str, str],
    ) -> bool:
        cookie = await self._vault.get(connection.cookie_key)
        if not cookie:
            return False
        try:
            answer = await self._http.send(
                "GET", probe, headers={**headers, "cookie": cookie}, timeout_s=15.0
            )
        except TargetUnreachable:
            return False
        return not _is_login(
            answer.status_code,
            answer.headers.get("location"),
            connection.base_url,
            answer.text,
        )

    async def _proved_read(
        self, ctx: RequestContext, system: str
    ) -> tuple[NetworkPlan, str] | None:
        async with self._uow as uow:
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=_LIBRARY_PAGE)
        for skill in skills:
            if skill.objective_key.target_system != system or not skill.versions:
                continue
            for step in skill.versions[-1].steps:
                plan = step.network_plan
                if plan is None or plan.method.upper() != "GET":
                    continue
                if "${" not in str(plan.url):
                    key = skill.objective_key
                    return plan, f"{key.target_system}/{key.facility}"
        return None

    async def _adopt(self, ctx: RequestContext, connection: Connection) -> bool:
        if self._browsers is None or self._browser is None or self._refresh is None:
            return False
        try:
            live = await self._browsers.mine(ctx)
        except BrowserUnavailable:
            return False

        for session in live:
            try:
                cookies = list(await self._browser.session_cookies(session.id))
            except BrowserUnavailable:
                continue
            if await self._refresh.execute(ctx, cookies=cookies, trusted=True):
                return True
        return False


def _is_login(status_code: int, location: str | None, base_url: str, body: str = "") -> bool:
    if 300 <= status_code < 400 and location:
        here = urlsplit(base_url).hostname or ""
        there = urlsplit(location).hostname
        return bool(there) and there != here
    lowered = body[:_LOGIN_SCAN_CHARS].lower()
    return status_code == 200 and (
        'type="password"' in lowered or 'autocomplete="current-password"' in lowered
    )
