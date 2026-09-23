"""The connection's own sign-in uses the credentials a run would.

Measured on the deployed tenant, 2026-09-23: the connection-level credential
keys are empty, and signing in happens by running the mined login job -- its
step types the username recorded in the job's evidence, and its password step
reads `<tenant>/<login origin>/password` from the vault, the key the panel's
password box writes. A server-side sign-in that read anything else would find
nothing, or a different password than the one the operator last stored.

So the use case signs in the way the run does: the tagged sign-in job's
recorded username, the password under the login origin's key. The connection's
own keys are a fallback for a tenant with no such job, which is today's
behaviour unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.application.connection.connect_system import RefreshSession
from sro.application.connection.refusals import ForgetsRefusalOnWrite, RefusedCredentials
from sro.application.connection.sign_in import (
    PASSWORD,
    USERNAME,
    NoCredentials,
    SignIn,
    StoreCredentials,
)
from sro.application.context import RequestContext
from sro.application.ports.sign_in import CredentialsRefused
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.secrets import secret_key_of
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.shared.errors import Conflict
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeCredentialVault,
    FakeSignInDriver,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SYSTEM = "https://wms.example.com"
LOGIN = "https://login.example.com"
LOGIN_KEY = secret_key_of(f.TENANT.value, "login.example.com", "password")
COOKIE: tuple[dict[str, object], ...] = (
    {"name": "SESSIONID", "value": "fresh", "domain": "wms.example.com"},
)


def _typed(gesture_id: str, at: float, *, value: str | None, secret: bool) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=f.TENANT.value,
        stream_id="s",
        batch_id="b",
        at=at,
        url=f"{LOGIN}/auth",
        system=LOGIN,
        tab_id=1,
        frame_url=None,
        action=Action(
            kind="type",
            at=at,
            value=value,
            url=f"{LOGIN}/auth",
            target=Target(tag="input", name="password" if secret else "username", secret=secret),
        ),
    )


def _login_job(*, signs_in: bool = True) -> Workflow:
    return Workflow(
        id="wfl_login",
        tenant=f.TENANT.value,
        title="Log in",
        narrative="n",
        steps=[
            Step(order=0, says="type the username", system=None, cites=["g-user"]),
            Step(order=1, says="type the password", system=None, cites=["g-pass"]),
        ],
        signs_in=signs_in,
    )


class _World:
    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.vault = ForgetsRefusalOnWrite(FakeCredentialVault())
        self.browser = FakeBrowserProvider()
        self.browser.cookies = COOKIE
        self.clock = FakeClock()
        self.driver = FakeSignInDriver()

    async def connect(
        self, *, job: Workflow | None, username: str | None = "operator-7"
    ) -> Connection:
        connection = Connection(
            id=ConnectionId("con_1"),
            tenant_id=f.TENANT,
            name="WMS",
            target_system="wms",
            base_url=f"{SYSTEM}/portal",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
        async with self.uow:
            await self.uow.connections.add(connection)
            await self.uow.commit()
        await self.uow.gestures.add_gestures(
            (
                _typed("g-user", 1.0, value=username, secret=False),
                _typed("g-pass", 2.0, value=None, secret=True),
            )
        )
        if job is not None:
            await self.uow.workflows.save(job)
        return connection

    def sign_in(self) -> SignIn:
        refresh = RefreshSession(self.uow, self.vault, self.clock)
        return SignIn(self.uow, self.vault, self.browser, self.driver, refresh, clock=self.clock)


async def test_the_recorded_username_and_the_login_origins_password_are_used() -> None:
    world = _World()
    connection = await world.connect(job=_login_job())
    await world.vault.store(LOGIN_KEY, "what the panel stored")
    await world.vault.store(connection.credential_key(USERNAME), "stale-user")
    await world.vault.store(connection.credential_key(PASSWORD), "stale-password")

    await world.sign_in().execute(CTX, target_system="wms")

    assert world.driver.given == ("operator-7", "what the panel stored")


async def test_a_refusal_is_latched_on_the_key_that_was_typed() -> None:
    world = _World()
    connection = await world.connect(job=_login_job())
    await world.vault.store(LOGIN_KEY, "wrong")
    world.driver.refuses = "the credentials were refused"

    with pytest.raises(CredentialsRefused):
        await world.sign_in().execute(CTX, target_system="wms")

    refusals = RefusedCredentials(world.vault)
    assert await refusals.standing(LOGIN_KEY) is not None
    assert await refusals.standing(connection.credential_key(PASSWORD)) is None

    with pytest.raises(CredentialsRefused):
        await world.sign_in().execute(CTX, target_system="wms")
    assert world.driver.calls == 1


async def test_with_no_tagged_sign_in_job_the_connections_own_keys_are_used() -> None:
    world = _World()
    connection = await world.connect(job=_login_job(signs_in=False))
    await world.vault.store(connection.credential_key(USERNAME), "operator")
    await world.vault.store(connection.credential_key(PASSWORD), "kept on the connection")

    await world.sign_in().execute(CTX, target_system="wms")

    assert world.driver.given == ("operator", "kept on the connection")


async def test_with_no_tagged_job_and_nothing_on_the_connection_it_still_says_so() -> None:
    world = _World()
    await world.connect(job=None)

    with pytest.raises(NoCredentials):
        await world.sign_in().execute(CTX, target_system="wms")
    assert world.driver.calls == 0


async def test_a_job_whose_password_nobody_stored_falls_back_only_when_nothing_is_known() -> None:
    """The job's username is recorded, so something IS known: the missing
    password is named, not papered over with whatever the connection holds."""
    world = _World()
    connection = await world.connect(job=_login_job())
    await world.vault.store(connection.credential_key(USERNAME), "operator")
    await world.vault.store(connection.credential_key(PASSWORD), "kept on the connection")

    with pytest.raises(NoCredentials, match=r"login\.example\.com"):
        await world.sign_in().execute(CTX, target_system="wms")
    assert world.driver.calls == 0


async def test_credentials_stored_on_the_connection_go_where_the_sign_in_reads_them() -> None:
    """One key per password: storing through the connection's credentials
    endpoint writes the login origin's key, which lifts its refusal too."""
    world = _World()
    connection = await world.connect(job=_login_job())
    await world.vault.store(LOGIN_KEY, "wrong")
    await RefusedCredentials(world.vault).refuse(LOGIN_KEY, at=world.clock.now(), reason="no")

    await StoreCredentials(world.uow, world.vault).execute(
        CTX,
        connection_id=connection.id,
        username=" operator-7 ",
        password="right",  # noqa: S106 -- a fake vault's value
    )

    assert await world.vault.get(LOGIN_KEY) == "right"
    assert await world.vault.get(connection.credential_key(PASSWORD)) is None
    await world.sign_in().execute(CTX, target_system="wms")
    assert world.driver.given == ("operator-7", "right")


async def test_a_username_other_than_the_one_the_job_signs_in_with_is_refused() -> None:
    """A run types the job's recorded username; storing a password for another
    account under that login would pair it with the wrong user."""
    world = _World()
    connection = await world.connect(job=_login_job())
    await world.vault.store(LOGIN_KEY, "kept")

    with pytest.raises(Conflict, match="recorded username") as raised:
        await StoreCredentials(world.uow, world.vault).execute(
            CTX,
            connection_id=connection.id,
            username="someone-else",
            password="new-secret",  # noqa: S106 -- a fake vault's value
        )

    assert "new-secret" not in str(raised.value)
    assert "someone-else" not in str(raised.value)
    assert await world.vault.get(LOGIN_KEY) == "kept"


async def test_the_recorded_username_in_another_case_is_the_same_username() -> None:
    """Identity providers match usernames without regard to case."""
    world = _World()
    connection = await world.connect(job=_login_job())

    await StoreCredentials(world.uow, world.vault).execute(
        CTX,
        connection_id=connection.id,
        username="OPERATOR-7",
        password="right",  # noqa: S106 -- a fake vault's value
    )

    assert await world.vault.get(LOGIN_KEY) == "right"


async def test_a_job_that_recorded_no_username_takes_the_one_stored_with_the_password() -> None:
    world = _World()
    connection = await world.connect(job=_login_job(), username=None)

    await StoreCredentials(world.uow, world.vault).execute(
        CTX,
        connection_id=connection.id,
        username=" operator-9 ",
        password="right",  # noqa: S106 -- a fake vault's value
    )

    assert await world.vault.get(LOGIN_KEY) == "right"
    await world.sign_in().execute(CTX, target_system="wms")
    assert world.driver.given == ("operator-9", "right")


async def test_a_standing_refusal_names_the_login_that_needs_a_new_password() -> None:
    world = _World()
    await world.connect(job=_login_job())
    await world.vault.store(LOGIN_KEY, "wrong")
    await RefusedCredentials(world.vault).refuse(LOGIN_KEY, at=world.clock.now(), reason="no")

    with pytest.raises(CredentialsRefused, match=r"login\.example\.com") as raised:
        await world.sign_in().execute(CTX, target_system="wms")
    assert "wrong" not in str(raised.value)
