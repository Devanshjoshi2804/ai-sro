"""A password the system refused is not typed again until somebody changes it.

Submitting credentials at most once per attempt is not enough on its own:
attempts repeat. A run's rescue rungs plan the password step again after the
form came back, and the session keeper signs in every pass -- a few repeats
and the account is locked, unattended, overnight.

So a refusal is remembered against the credential that was refused -- its
vault key, per tenant, login origin and field -- and nothing types that
password while the refusal stands. It is lifted by the one thing that can fix
it: that vault key being written again, through whichever door. A password
held for one run is the operator answering for that run, so it is typed for
that run regardless.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.application.connection.check_session import CheckSession
from sro.application.connection.connect_system import RefreshSession
from sro.application.connection.keep_open import KeepSessionsOpen
from sro.application.connection.refusals import ForgetsRefusalOnWrite, RefusedCredentials
from sro.application.connection.sign_in import (
    PASSWORD,
    USERNAME,
    EnsureSignedIn,
    SignIn,
    StoreCredentials,
)
from sro.application.context import RequestContext
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.run_secrets import RunSecrets
from sro.application.ports.sign_in import CredentialsRefused
from sro.domain.connection.connection import Connection, ConnectionId
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeSignInDriver,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SIGNED_OUT = '<form><input type="password"></form>'
LOGIN_KEY = f"{f.TENANT.value}/login.example.com/password"
WRONG = "not-the-password"


class _World:
    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.vault = ForgetsRefusalOnWrite(FakeCredentialVault())
        self.browser = FakeBrowserProvider()
        self.http = FakeHttpCaller()
        self.clock = FakeClock()
        self.driver = FakeSignInDriver(refuses="the credentials were refused")
        self.refusals = RefusedCredentials(self.vault)

    async def connect(self) -> Connection:
        connection = Connection(
            id=ConnectionId("con_1"),
            tenant_id=f.TENANT,
            name="WMS",
            target_system="wms",
            base_url="https://wms.example.com/portal",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
        async with self.uow:
            await self.uow.connections.add(connection)
            await self.uow.commit()
        await self.vault.store(connection.cookie_key, "SESSIONID=dead")
        await self.vault.store(connection.credential_key(USERNAME), "operator")
        await self.vault.store(connection.credential_key(PASSWORD), WRONG)
        return connection

    def sign_in(self) -> SignIn:
        refresh = RefreshSession(self.uow, self.vault, self.clock)
        return SignIn(self.uow, self.vault, self.browser, self.driver, refresh, clock=self.clock)

    def keeper(self) -> KeepSessionsOpen:
        ensure = EnsureSignedIn(
            self.sign_in(), CheckSession(self.uow, self.vault, self.http), self.uow
        )
        return KeepSessionsOpen(self.uow, ensure)

    def run(self, run_id: str = "run-1", held: OneTimeSecrets | None = None) -> RunSecrets:
        return RunSecrets(self.vault, held or OneTimeSecrets(), run_id=run_id)


async def test_a_refusal_is_remembered_against_the_password_that_was_refused() -> None:
    world = _World()
    connection = await world.connect()

    with pytest.raises(CredentialsRefused):
        await world.sign_in().execute(CTX, target_system="wms")

    standing = await world.refusals.standing(connection.credential_key(PASSWORD))
    assert standing is not None
    assert standing.at == world.clock.now()
    assert "refused" in standing.reason
    assert await world.refusals.standing(connection.credential_key(USERNAME)) is None


async def test_the_next_keeper_pass_does_not_try_the_same_password_again() -> None:
    world = _World()
    await world.connect()
    for _ in range(3):
        world.http.answer(status_code=200, text=SIGNED_OUT)

    await world.keeper().sweep()
    assert world.driver.calls == 1
    opened = len(world.browser.opened)

    await world.keeper().sweep()
    await world.keeper().sweep()

    assert world.driver.calls == 1
    assert len(world.browser.opened) == opened


async def test_new_credentials_lift_the_refusal() -> None:
    world = _World()
    connection = await world.connect()
    with pytest.raises(CredentialsRefused):
        await world.sign_in().execute(CTX, target_system="wms")

    await StoreCredentials(world.uow, world.vault).execute(
        CTX,
        connection_id=connection.id,
        username="operator",
        password="right",  # noqa: S106 -- a fake vault's value
    )

    assert await world.refusals.standing(connection.credential_key(PASSWORD)) is None
    world.driver.refuses = ""
    world.browser.cookies = ({"name": "SESSIONID", "value": "fresh", "domain": "wms.example.com"},)
    await world.sign_in().execute(CTX, target_system="wms")
    assert world.driver.calls == 2


async def test_any_write_of_that_vault_key_lifts_it_and_no_other_key_does() -> None:
    """`PUT /v1/secrets` and the panel's keep-secret box write the vault directly."""
    world = _World()
    await world.refusals.refuse(LOGIN_KEY, at=world.clock.now(), reason="refused")

    await world.vault.store(f"{f.TENANT.value}/login.example.com/pin", "1234")
    assert await world.refusals.standing(LOGIN_KEY) is not None

    await world.vault.store(LOGIN_KEY, "a new password")
    assert await world.refusals.standing(LOGIN_KEY) is None


async def test_a_run_is_not_handed_a_refused_password() -> None:
    """Nothing to type means the step stops on its needs_secret ask, and the
    panel asks the operator for a new one."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    await world.refusals.refuse(LOGIN_KEY, at=world.clock.now(), reason="refused")

    assert await world.run()(LOGIN_KEY) is None


async def test_a_password_held_for_one_run_is_typed_for_that_run_only() -> None:
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    await world.refusals.refuse(LOGIN_KEY, at=world.clock.now(), reason="refused")
    held = OneTimeSecrets()
    held.hold(LOGIN_KEY, "try this", run_id="run-1")

    assert await world.run("run-1", held)(LOGIN_KEY) == "try this"
    assert await world.run("run-2", held)(LOGIN_KEY) is None
    assert await world.refusals.standing(LOGIN_KEY) is not None


async def test_a_password_a_run_already_typed_is_not_typed_again_and_is_latched() -> None:
    """The production lockout path: the password step typed the stored value,
    the sign-in form came back, and a rescue rung planned the step again."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    assert await run(LOGIN_KEY) == WRONG
    run.typed(WRONG)

    assert await run(LOGIN_KEY) is None
    standing = await world.refusals.standing(LOGIN_KEY)
    assert standing is not None
    assert WRONG not in standing.reason
    assert await world.run("run-2")(LOGIN_KEY) is None


async def test_a_password_handed_out_but_never_typed_can_be_asked_for_again() -> None:
    """A rung whose command missed the field typed nothing; the next rung
    planning the same step is not a second attempt at signing in."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    assert await run(LOGIN_KEY) == WRONG
    assert await run(LOGIN_KEY) == WRONG
    assert await world.refusals.standing(LOGIN_KEY) is None


async def test_a_new_password_stored_during_the_run_is_typed() -> None:
    """The operator answered the ask by storing a new one. It is a different
    password, so typing it is not a retry."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()
    assert await run(LOGIN_KEY) == WRONG
    run.typed(WRONG)
    assert await run(LOGIN_KEY) is None

    await world.vault.store(LOGIN_KEY, "the right one")

    assert await run(LOGIN_KEY) == "the right one"


async def test_a_held_password_that_was_typed_is_not_latched_on_the_vault_key() -> None:
    """Held for one run and refused says nothing about what the vault keeps."""
    world = _World()
    held = OneTimeSecrets()
    held.hold(LOGIN_KEY, "typed just now", run_id="run-1")
    run = world.run("run-1", held)

    assert await run(LOGIN_KEY) == "typed just now"
    run.typed("typed just now")

    assert await run(LOGIN_KEY) is None
    assert await world.refusals.standing(LOGIN_KEY) is None
