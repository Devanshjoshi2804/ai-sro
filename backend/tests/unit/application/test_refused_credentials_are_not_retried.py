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

Inside a run, "refused" is decided by evidence, the rule the driver uses: the
password was typed, and the same host then shows its sign-in form again with the
password box empty. A fresh form after the browser had landed in the system is
the session ending, and the password is typed again.
"""

from __future__ import annotations

from collections.abc import Mapping
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
from sro.application.execution.run_secrets import RunSecrets, WatchingChannel
from sro.application.ports.channel import Reply
from sro.application.ports.sign_in import CredentialsRefused
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.shared.identifiers import DeviceId, TenantId
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


FORM = "https://login.example.com/auth"
SYSTEM = "https://wms.example.com/portal"


async def test_the_form_coming_back_empty_after_the_submit_is_a_refusal() -> None:
    """The evidence the driver uses, seen by the run engine: the password went
    in, and the same host shows its sign-in form again with the box empty."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    await run.saw(FORM, signed_out=True, credential_empty=True)
    assert await run(LOGIN_KEY) == WRONG
    run.typed(WRONG)
    run.pressed()
    await run.saw(FORM, signed_out=True, credential_empty=True)

    standing = await world.refusals.standing(LOGIN_KEY)
    assert standing is not None
    assert WRONG not in standing.reason
    assert await run(LOGIN_KEY) is None
    assert await world.run("run-2")(LOGIN_KEY) is None


async def test_a_re_login_after_the_session_expired_types_it_again() -> None:
    """The browser landed in the system in between: a fresh form later is the
    session ending, not the password being refused."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    await run.saw(FORM, signed_out=True, credential_empty=True)
    assert await run(LOGIN_KEY) == WRONG
    run.typed(WRONG)
    run.pressed()
    await run.saw(SYSTEM, signed_out=False, credential_empty=False)
    await run.saw(FORM, signed_out=True, credential_empty=True)

    assert await world.refusals.standing(LOGIN_KEY) is None
    assert await run(LOGIN_KEY) == WRONG


async def test_a_form_still_holding_the_password_is_a_submit_in_flight() -> None:
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    await run.saw(FORM, signed_out=True, credential_empty=True)
    assert await run(LOGIN_KEY) == WRONG
    run.typed(WRONG)
    run.pressed()
    await run.saw(FORM, signed_out=True, credential_empty=False)

    assert await world.refusals.standing(LOGIN_KEY) is None
    assert await run(LOGIN_KEY) == WRONG


async def test_a_password_handed_out_but_never_typed_is_not_refused() -> None:
    """A rung whose command missed the field typed nothing, so an empty form
    after it says nothing about the password."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    await run.saw(FORM, signed_out=True, credential_empty=True)
    assert await run(LOGIN_KEY) == WRONG
    await run.saw(FORM, signed_out=True, credential_empty=True)

    assert await world.refusals.standing(LOGIN_KEY) is None
    assert await run(LOGIN_KEY) == WRONG


async def test_a_new_password_stored_during_the_run_is_typed() -> None:
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()
    await run.saw(FORM, signed_out=True, credential_empty=True)
    assert await run(LOGIN_KEY) == WRONG
    run.typed(WRONG)
    run.pressed()
    await run.saw(FORM, signed_out=True, credential_empty=True)
    assert await run(LOGIN_KEY) is None

    await world.vault.store(LOGIN_KEY, "the right one")

    assert await run(LOGIN_KEY) == "the right one"


async def test_a_refused_held_password_is_not_latched_on_the_vault_key() -> None:
    """Held for one run and refused says nothing about what the vault keeps."""
    world = _World()
    held = OneTimeSecrets()
    held.hold(LOGIN_KEY, "typed just now", run_id="run-1")
    run = world.run("run-1", held)

    await run.saw(FORM, signed_out=True, credential_empty=True)
    assert await run(LOGIN_KEY) == "typed just now"
    run.typed("typed just now")
    run.pressed()
    await run.saw(FORM, signed_out=True, credential_empty=True)

    assert await world.refusals.standing(LOGIN_KEY) is None


class _Browser:
    """Answers each command kind with one scripted reply."""

    def __init__(self, replies: dict[str, Reply]) -> None:
        self.replies = replies

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        return self.replies[kind]

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return ()

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        return False


async def test_the_run_learns_both_facts_from_the_browser_conversation() -> None:
    """What was typed and what the page then showed, read off the commands the
    run engine already sends -- so the engine itself needs no new hook."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()
    browser = _Browser(
        {
            "ui.url": Reply(
                ok=True, result={"url": FORM, "signed_out": True, "credential_empty": True}
            ),
            "ui.perform": Reply(ok=True, result={"performed": True}),
        }
    )
    watched = WatchingChannel(browser, run)
    device = DeviceId("dev-1")

    await watched.send(f.TENANT, device, kind="ui.url", payload={})
    value = await run(LOGIN_KEY)
    await watched.send(
        f.TENANT, device, kind="ui.perform", payload={"action": "type", "value": value}
    )
    await watched.send(f.TENANT, device, kind="ui.perform", payload={"action": "click"})
    await watched.send(f.TENANT, device, kind="ui.url", payload={})

    assert await world.refusals.standing(LOGIN_KEY) is not None


async def test_a_command_the_browser_did_not_perform_typed_nothing() -> None:
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()
    browser = _Browser(
        {
            "ui.url": Reply(
                ok=True, result={"url": FORM, "signed_out": True, "credential_empty": True}
            ),
            "ui.perform": Reply(ok=False, error_kind="control_not_found"),
        }
    )
    watched = WatchingChannel(browser, run)
    device = DeviceId("dev-1")

    await watched.send(f.TENANT, device, kind="ui.url", payload={})
    value = await run(LOGIN_KEY)
    await watched.send(f.TENANT, device, kind="ui.perform", payload={"value": value})
    await watched.send(f.TENANT, device, kind="ui.url", payload={})

    assert await world.refusals.standing(LOGIN_KEY) is None


async def test_the_browsers_own_sign_in_counts_as_typing_the_password() -> None:
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()
    browser = _Browser(
        {
            "ui.url": Reply(
                ok=True, result={"url": FORM, "signed_out": True, "credential_empty": True}
            ),
            "sign_in": Reply(ok=True, result={"did": ["submitted"]}),
        }
    )
    watched = WatchingChannel(browser, run)
    device = DeviceId("dev-1")

    await watched.send(f.TENANT, device, kind="ui.url", payload={})
    value = await run(LOGIN_KEY)
    await watched.send(
        f.TENANT, device, kind="sign_in", payload={"username": "u", "password": value}
    )
    await watched.send(f.TENANT, device, kind="ui.url", payload={})

    assert await world.refusals.standing(LOGIN_KEY) is not None


SAME_HOST_FORM = "https://wms.example.com/auth"


async def test_a_same_host_login_that_landed_types_it_again_when_the_session_ends() -> None:
    """The form lives on the system's own host: landing is the same host with
    no login box on screen, and a later form is a new sign-in."""
    world = _World()
    key = f"{f.TENANT.value}/wms.example.com/password"
    await world.vault.store(key, WRONG)
    run = world.run()

    await run.saw(SAME_HOST_FORM, signed_out=True, credential_empty=True)
    assert await run(key) == WRONG
    run.typed(WRONG)
    run.pressed()
    await run.saw(SYSTEM, signed_out=False, credential_empty=False)
    run.pressed()
    await run.saw(SAME_HOST_FORM, signed_out=True, credential_empty=True)

    assert await world.refusals.standing(key) is None
    assert await run(key) == WRONG


async def test_an_empty_form_with_no_submit_after_the_typing_is_not_a_refusal() -> None:
    """The value went into some box, nothing was pressed: nothing was submitted."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    await run.saw(FORM, signed_out=True, credential_empty=True)
    assert await run(LOGIN_KEY) == WRONG
    run.typed(WRONG)
    await run.saw(FORM, signed_out=True, credential_empty=True)

    assert await world.refusals.standing(LOGIN_KEY) is None
    assert await run(LOGIN_KEY) == WRONG


async def test_a_page_without_a_login_box_before_the_refusal_buys_one_more_try_only() -> None:
    """A spinner between the submit and the refused form looks like a landing.
    The second submit is not given that benefit: at most two, never three."""
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    for _ in range(2):
        await run.saw(FORM, signed_out=True, credential_empty=True)
        assert await run(LOGIN_KEY) == WRONG
        run.typed(WRONG)
        run.pressed()
        await run.saw(FORM, signed_out=False, credential_empty=False)
        await run.saw(FORM, signed_out=True, credential_empty=True)

    assert await world.refusals.standing(LOGIN_KEY) is not None
    assert await run(LOGIN_KEY) is None


async def test_every_re_login_after_the_run_moved_on_is_typed_again() -> None:
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)
    run = world.run()

    for _ in range(3):
        await run.saw(FORM, signed_out=True, credential_empty=True)
        assert await run(LOGIN_KEY) == WRONG
        run.typed(WRONG)
        run.pressed()
        await run.saw(SYSTEM, signed_out=False, credential_empty=False)
        run.pressed()

    assert await world.refusals.standing(LOGIN_KEY) is None


async def test_a_password_held_for_the_run_survives_being_looked_up() -> None:
    """Asking whether a password exists must not use up the operator's answer."""
    world = _World()
    held = OneTimeSecrets()
    held.hold(LOGIN_KEY, "typed just now", run_id="run-1")
    run = world.run("run-1", held)

    assert await run(LOGIN_KEY) == "typed just now"
    assert await run(LOGIN_KEY) == "typed just now"


def _front_tab(*, ours: bool) -> Reply:
    return Reply(
        ok=True,
        result={
            "url": None,
            "elsewhere": FORM,
            "elsewhere_is_ours": ours,
            "signed_out": True,
            "credential_empty": True,
        },
    )


async def _type_submit_look(world: _World, run: RunSecrets, look: Reply) -> None:
    browser = _Browser(
        {
            "ui.url": Reply(
                ok=True, result={"url": FORM, "signed_out": True, "credential_empty": True}
            ),
            "ui.perform": Reply(ok=True, result={"performed": True}),
        }
    )
    watched = WatchingChannel(browser, run)
    device = DeviceId("dev-1")
    await watched.send(f.TENANT, device, kind="ui.url", payload={})
    value = await run(LOGIN_KEY)
    await watched.send(
        f.TENANT, device, kind="ui.perform", payload={"action": "type", "value": value}
    )
    await watched.send(f.TENANT, device, kind="ui.perform", payload={"action": "press"})
    browser.replies["ui.url"] = look
    await watched.send(f.TENANT, device, kind="ui.url", payload={})


async def test_the_operators_own_front_tab_decides_nothing() -> None:
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)

    await _type_submit_look(world, world.run(), _front_tab(ours=False))

    assert await world.refusals.standing(LOGIN_KEY) is None


async def test_the_runs_own_tab_on_another_origin_still_counts() -> None:
    world = _World()
    await world.vault.store(LOGIN_KEY, WRONG)

    await _type_submit_look(world, world.run(), _front_tab(ours=True))

    assert await world.refusals.standing(LOGIN_KEY) is not None
