"""Connect once, stay connected.

Keeping a session alive by refreshing it from every capture only works while
somebody keeps using the system. Leave it a long weekend and the session dies
of old age, and the operator is back at a login page -- which is not what a
connected system means to anybody who has used one.

So the connection can hold credentials, encrypted in the vault, and sign itself
back in. That is what makes it a connector rather than a saved password: a human
enters it once, and everything after that -- a demonstration, a batch at 3am, an
API call that needs a fresh cookie header -- finds the system already open.

The credentials are typed by the driver into the system's own login page. They
are never logged, never returned by any endpoint, never written into a
recording, and never sent to any host but the one the connection names.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.capture.identity import system_of
from sro.application.connection.check_session import CheckSession, SessionHealth
from sro.application.connection.connect_system import RefreshSession
from sro.application.connection.session_life import SessionLife
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.sign_in import SignInDriver, SignInFailed
from sro.application.ports.system import Clock
from sro.application.ports.vault import CredentialVault
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.shared.errors import DomainError
from sro.domain.skill.skill import Skill

USERNAME = "username"
PASSWORD = "password"  # noqa: S105 -- a vault key's name, not a value


class NoCredentials(DomainError):
    """Nothing stored to sign in with, so nothing can be done unattended."""

    code = "no_credentials"


@dataclass(frozen=True, slots=True)
class SignedIn:
    target_system: str
    landed_at: str
    steps: tuple[str, ...]


class StoreCredentials:
    """Keep what a human typed once, so nothing has to ask them again."""

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
        await self._vault.store(connection.credential_key(USERNAME), username.strip())
        await self._vault.store(connection.credential_key(PASSWORD), password)


class SignIn:
    """Open a browser, sign in with what is stored, keep the session it produced."""

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

        username, password = await self._credentials(connection)
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
        finally:
            # The browser existed to produce a session and has done so. Leaving
            # it open would hold the provider's only slot against the next
            # demonstration.
            await self._browser.close(session.id)

        if not await self._refresh.execute(ctx, cookies=cookies):
            raise SignInFailed(
                "the login finished but the browser held no session for this system. "
                "Connect it by hand once so we can see what it expects."
            )
        # The clock this session is measured against starts here.
        if self._life is not None and self._clock is not None:
            await self._life.minted(ctx, system=connection.target_system, at=self._clock.now())
        return SignedIn(
            target_system=connection.target_system,
            landed_at=result.landed_at,
            steps=result.steps,
        )

    async def _chooser(self, ctx: RequestContext, system: str) -> tuple[str, ...]:
        """What a demonstration of this login clicked before the form appeared.

        Azure B2C opens by asking which tenant somebody belongs to, and that
        page offers links rather than fields. Which of them is right is a fact
        about this deployment, so it is read from a recording of somebody
        choosing rather than guessed at -- and where nobody has demonstrated a
        login, nothing is chosen and the driver behaves as before.
        """
        async with self._uow as uow:
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=200)

        # Preferring this system's own demonstration, but not requiring it: the
        # login taught here is filed under the system name derived when it was
        # sealed, and an early one landed under "ai". Passing an option that
        # belongs to another system costs nothing -- the driver clicks only text
        # that is actually on the page in front of it.
        matching = [s for s in skills if _is_a_login(s)]
        preferred = [s for s in matching if s.objective_key.target_system == system]

        wanted: list[str] = []
        for skill in preferred + [s for s in matching if s not in preferred]:
            for step in (skill.versions[-1].steps if skill.versions else ())[:3]:
                for locator in step.ui_plan.locators if step.ui_plan else ():
                    if locator.strategy.value in {"text", "role_and_name"} and locator.query:
                        wanted.append(str(locator.query).split("|")[-1])
        return tuple(dict.fromkeys(wanted))[:6]

    async def _credentials(self, connection: Connection) -> tuple[str, str]:
        username = await self._vault.get(connection.credential_key(USERNAME))
        password = await self._vault.get(connection.credential_key(PASSWORD))
        if not username or not password:
            raise NoCredentials(
                f"no credentials are stored for {connection.target_system}, so it cannot sign "
                "itself back in. Add them once on the connection."
            )
        return username, password


class EnsureSignedIn:
    """A session, whatever it takes -- and nothing more than it takes.

    Called before anything that needs the system open. If the stored session
    still works it does nothing at all, because signing in again would throw
    away a working session and, on a system that permits one at a time, would
    sign the operator's own browser out.
    """

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
        """Same, for a caller that knows an address and not a system name.

        Which is every teaching session: the operator pastes a URL, and which
        connected system that belongs to is ours to work out, not theirs to
        declare.
        """
        async with self._uow as uow:
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
        system = system_of(connections, url)
        return await self.execute(ctx, target_system=system) if system else False

    async def execute(self, ctx: RequestContext, *, target_system: str) -> bool:
        """True if the system is open. False only when nobody can be asked."""
        health = await self._check.for_system(ctx, target_system=target_system)
        if health is None or health.health is SessionHealth.UNREACHABLE:
            # An outage is not a login problem, and signing in during one only
            # burns the credentials against a system that cannot answer.
            return False
        if health.health is SessionHealth.SIGNED_IN:
            # Working now, and old enough to stop working during whatever is
            # about to be asked of it. Replacing it here costs one login;
            # finding out halfway through a batch costs the batch.
            if await self._ageing(ctx, target_system):
                try:
                    await self._sign_in.execute(ctx, target_system=target_system)
                except (NoCredentials, SignInFailed):
                    return True  # the session we have still works
            elif self._life is not None and self._clock is not None:
                await self._life.worked(ctx, system=target_system, at=self._clock.now())
            return True

        if self._life is not None and self._clock is not None:
            # It used to work and does not now, which is the only way anybody
            # learns how long these last.
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
    """Whether this skill is somebody signing in.

    By what it was called and what it was for, because a login recorded before
    the system name was derived properly is still a demonstration of this
    login.
    """
    said = f"{skill.name} {skill.objective_key.objective_type}".lower()
    return any(word in said for word in ("login", "log in", "sign in", "authenticate", "auth"))
