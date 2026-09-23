from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sro.application.capture.identity import system_of
from sro.application.connection.check_session import CheckSession, SessionHealth
from sro.application.connection.connect_system import RefreshSession
from sro.application.connection.refusals import RefusedCredentials
from sro.application.connection.session_life import SessionLife
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.sign_in import CredentialsRefused, SignInDriver, SignInFailed
from sro.application.ports.system import Clock
from sro.application.ports.vault import CredentialVault
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.secrets import secret_key_of
from sro.domain.shared.errors import DomainError
from sro.domain.skill.signing_in import RecordedLogin, recorded_login
from sro.domain.skill.skill import Skill
from sro.domain.skill.workflow import ordered_cites

USERNAME = "username"
PASSWORD = "password"  # noqa: S105 -- a vault key's name, not a value


class NoCredentials(DomainError):
    code = "no_credentials"


@dataclass(frozen=True, slots=True)
class SignedIn:
    target_system: str
    landed_at: str
    steps: tuple[str, ...]


class StoreCredentials:
    def __init__(self, uow: UnitOfWork, vault: CredentialVault) -> None:
        self._uow = uow
        self._vault = vault

    async def execute(
        self, ctx: RequestContext, *, connection_id: ConnectionId, username: str, password: str
    ) -> None:
        if not username.strip() or not password:
            raise DomainError("a sign-in needs both a username and a password")
        async with self._uow as uow:
            connection = await uow.connections.get(ctx.tenant_id, connection_id)
        recorded = await _recorded(self._uow, ctx, connection)
        if recorded is None:
            await self._vault.store(connection.credential_key(USERNAME), username.strip())
            await self._vault.store(connection.credential_key(PASSWORD), password)
            return
        if not recorded.username:
            await self._vault.store(_key(ctx, recorded, USERNAME), username.strip())
        await self._vault.store(_key(ctx, recorded, PASSWORD), password)


class SignIn:
    def __init__(
        self,
        uow: UnitOfWork,
        vault: CredentialVault,
        browser: BrowserProvider,
        driver: SignInDriver,
        refresh: RefreshSession,
        life: SessionLife | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._uow = uow
        self._vault = vault
        self._browser = browser
        self._driver = driver
        self._refresh = refresh
        self._life = life
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, target_system: str) -> SignedIn:
        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)
        if connection is None:
            raise NoCredentials(f"{target_system} is not connected")

        username, password, key, where = await self._credentials(ctx, connection)
        refusals = RefusedCredentials(self._vault)
        if (standing := await refusals.standing(key)) is not None:
            raise CredentialsRefused(
                f"the password {connection.target_system} signs in with at {where} was refused"
                f"{' at ' + standing.at.isoformat() if standing.at else ''}, so it is not "
                f"tried again. Store a new password for {where} (vault key {key!r}) and it "
                "will be used."
            )

        session = await self._browser.open()
        try:
            result = await self._driver.sign_in(
                debugger_url=session.debugger_url,
                url=connection.base_url,
                username=username,
                password=password,
                choose=await self._chooser(ctx, connection.target_system),
            )
            cookies = list(await self._browser.session_cookies(session.id))
        except CredentialsRefused as refused:
            await refusals.refuse(key, at=self._now(), reason=str(refused))
            raise
        finally:
            await self._browser.close(session.id)

        if not await self._refresh.execute(ctx, cookies=cookies):
            raise SignInFailed(
                "the login finished but the browser held no session for this system. "
                "Connect it by hand once so we can see what it expects."
            )
        if self._life is not None and self._clock is not None:
            await self._life.minted(ctx, system=connection.target_system, at=self._clock.now())
        return SignedIn(
            target_system=connection.target_system,
            landed_at=result.landed_at,
            steps=result.steps,
        )

    def _now(self) -> datetime:
        return self._clock.now() if self._clock is not None else datetime.now(UTC)

    async def _chooser(self, ctx: RequestContext, system: str) -> tuple[str, ...]:
        async with self._uow as uow:
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=200)

        matching = [s for s in skills if _is_a_login(s)]
        preferred = [s for s in matching if s.objective_key.target_system == system]

        wanted: list[str] = []
        for skill in preferred + [s for s in matching if s not in preferred]:
            for step in (skill.versions[-1].steps if skill.versions else ())[:3]:
                for locator in step.ui_plan.locators if step.ui_plan else ():
                    if locator.strategy.value in {"text", "role_and_name"} and locator.query:
                        wanted.append(str(locator.query).split("|")[-1])
        return tuple(dict.fromkeys(wanted))[:6]

    async def _credentials(
        self, ctx: RequestContext, connection: Connection
    ) -> tuple[str, str, str, str]:
        recorded = await _recorded(self._uow, ctx, connection)
        if recorded is not None:
            key = _key(ctx, recorded, PASSWORD)
            password = await self._vault.get(key)
            username = recorded.username or await self._vault.get(_key(ctx, recorded, USERNAME))
            if username and password:
                return username, password, key, recorded.origin
            if username:
                raise NoCredentials(
                    f"{connection.target_system} signs in at {recorded.origin}, and no password "
                    f"is stored under {key!r}. Store it once and it will be used."
                )
            if password:
                raise NoCredentials(
                    f"{connection.target_system} signs in at {recorded.origin}, and the job that "
                    "signs in there recorded no username. Store one with the password."
                )
        key = connection.credential_key(PASSWORD)
        username = await self._vault.get(connection.credential_key(USERNAME))
        password = await self._vault.get(key)
        if not username or not password:
            raise NoCredentials(
                f"no credentials are stored for {connection.target_system}, so it cannot sign "
                "itself back in. Add them once on the connection."
            )
        return username, password, key, connection.target_system


class EnsureSignedIn:
    def __init__(
        self,
        sign_in: SignIn,
        check: CheckSession,
        uow: UnitOfWork,
        life: SessionLife | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._sign_in = sign_in
        self._check = check
        self._uow = uow
        self._life = life
        self._clock = clock

    async def for_url(self, ctx: RequestContext, url: str | None) -> bool:
        async with self._uow as uow:
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
        system = system_of(connections, url)
        return await self.execute(ctx, target_system=system) if system else False

    async def execute(self, ctx: RequestContext, *, target_system: str) -> bool:
        health = await self._check.for_system(ctx, target_system=target_system)
        if health is None or health.health is SessionHealth.UNREACHABLE:
            return False
        if health.health is SessionHealth.SIGNED_IN:
            if await self._ageing(ctx, target_system):
                try:
                    await self._sign_in.execute(ctx, target_system=target_system)
                except (NoCredentials, SignInFailed):
                    return True
            elif self._life is not None and self._clock is not None:
                await self._life.worked(ctx, system=target_system, at=self._clock.now())
            return True

        if self._life is not None and self._clock is not None:
            await self._life.died(ctx, system=target_system, at=self._clock.now())
        try:
            await self._sign_in.execute(ctx, target_system=target_system)
        except (NoCredentials, SignInFailed):
            return False
        return True

    async def _ageing(self, ctx: RequestContext, system: str) -> bool:
        if self._life is None or self._clock is None:
            return False
        return (await self._life.of(ctx, system=system)).worth_refreshing(self._clock.now())


def _is_a_login(skill: Skill) -> bool:
    said = f"{skill.name} {skill.objective_key.objective_type}".lower()
    return any(word in said for word in ("login", "log in", "sign in", "authenticate", "auth"))


async def _recorded(
    uow: UnitOfWork, ctx: RequestContext, connection: Connection
) -> RecordedLogin | None:
    async with uow:
        known = await uow.workflows.known(ctx.tenant_id)
        tagged = [job for job in known if job.signs_in]
        cited = tuple(sorted({one for job in tagged for one in ordered_cites(job)}))
        seen = await uow.gestures.gestures_for(ctx.tenant_id, ids=cited) if cited else ()
    return recorded_login(connection.base_url, tagged, {one.id: one for one in seen})


def _key(ctx: RequestContext, recorded: RecordedLogin, field: str) -> str:
    return secret_key_of(ctx.tenant_id.value, recorded.origin, field)
