"""Connecting once has to mean once.

A session refreshed from every capture still dies over a long weekend. What
makes a connection a connector rather than a saved password is that it can open
the system again by itself -- and, just as much, that it knows when not to.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.application.connection.check_session import CheckSession, SessionHealth
from sro.application.connection.connect_system import (
    ConnectSystem,
    NotAuthenticated,
    RefreshSession,
    StoreSession,
    _system_from,
)
from sro.application.connection.sign_in import (
    PASSWORD,
    USERNAME,
    EnsureSignedIn,
    NoCredentials,
    SignIn,
)
from sro.application.context import RequestContext
from sro.domain.connection.connection import Connection, ConnectionId, ConnectionStatus
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeSignInDriver,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS = "https://wms.example.com/portal"


async def _connection(uow: FakeUnitOfWork) -> Connection:
    connection = Connection(
        id=ConnectionId("con_1"),
        tenant_id=f.TENANT,
        name="WMS",
        target_system="blue_yonder",
        base_url=WMS,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
    async with uow:
        await uow.connections.add(connection)
        await uow.commit()
    return connection


def _sign_in(
    uow: FakeUnitOfWork,
    vault: FakeCredentialVault,
    browser: FakeBrowserProvider,
    driver: FakeSignInDriver,
) -> SignIn:
    return SignIn(uow, vault, browser, driver, RefreshSession(uow, vault, FakeClock()))


@pytest.mark.asyncio
async def test_a_connection_signs_itself_back_in_and_keeps_what_it_gets() -> None:
    uow, vault, browser = FakeUnitOfWork(), FakeCredentialVault(), FakeBrowserProvider()
    connection = await _connection(uow)
    await vault.store(connection.credential_key(USERNAME), "operator")
    await vault.store(connection.credential_key(PASSWORD), "s3cret")
    browser.cookies = ({"name": "SESSIONID", "value": "fresh", "domain": "wms.example.com"},)

    signed_in = await _sign_in(uow, vault, browser, FakeSignInDriver()).execute(
        CTX, target_system="blue_yonder"
    )

    assert signed_in.landed_at == WMS
    assert await vault.get(connection.cookie_key) == "SESSIONID=fresh"
    # The browser was for producing a session, and holding it open would keep
    # the provider's only slot from the next demonstration.
    assert browser.closed == [browser.opened[-1]]


@pytest.mark.asyncio
async def test_nothing_stored_means_a_clear_refusal_not_a_silent_login_page() -> None:
    uow, vault, browser = FakeUnitOfWork(), FakeCredentialVault(), FakeBrowserProvider()
    await _connection(uow)
    driver = FakeSignInDriver()

    with pytest.raises(NoCredentials):
        await _sign_in(uow, vault, browser, driver).execute(CTX, target_system="blue_yonder")

    # And no browser was opened to find that out.
    assert driver.calls == 0
    assert browser.opened == []


@pytest.mark.asyncio
async def test_a_working_session_is_never_replaced_by_signing_in_again() -> None:
    """The expensive mistake this guard exists for.

    On a system that permits one session at a time -- Blue Yonder appears to be
    one -- signing in again to a system already open signs the operator's own
    browser out from under them.
    """
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    browser, http = FakeBrowserProvider(), FakeHttpCaller()
    connection = await _connection(uow)
    await vault.store(connection.cookie_key, "SESSIONID=working")
    await vault.store(connection.credential_key(USERNAME), "operator")
    await vault.store(connection.credential_key(PASSWORD), "s3cret")
    http.answer(status_code=200)
    driver = FakeSignInDriver()

    ensure = EnsureSignedIn(
        _sign_in(uow, vault, browser, driver), CheckSession(uow, vault, http), uow
    )
    assert await ensure.execute(CTX, target_system="blue_yonder") is True
    assert driver.calls == 0
    assert await vault.get(connection.cookie_key) == "SESSIONID=working"


@pytest.mark.asyncio
async def test_an_expired_session_is_replaced_without_anybody_being_asked() -> None:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    browser, http = FakeBrowserProvider(), FakeHttpCaller()
    connection = await _connection(uow)
    await vault.store(connection.cookie_key, "SESSIONID=expired")
    await vault.store(connection.credential_key(USERNAME), "operator")
    await vault.store(connection.credential_key(PASSWORD), "s3cret")
    http.answer(status_code=302, headers={"location": "https://login.example.org/authorize"})
    browser.cookies = ({"name": "SESSIONID", "value": "fresh", "domain": "wms.example.com"},)
    driver = FakeSignInDriver()

    ensure = EnsureSignedIn(
        _sign_in(uow, vault, browser, driver), CheckSession(uow, vault, http), uow
    )
    assert await ensure.execute(CTX, target_system="blue_yonder") is True
    assert driver.calls == 1
    assert await vault.get(connection.cookie_key) == "SESSIONID=fresh"


@pytest.mark.asyncio
async def test_an_outage_does_not_spend_the_credentials() -> None:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    browser, http = FakeBrowserProvider(), FakeHttpCaller()
    connection = await _connection(uow)
    await vault.store(connection.cookie_key, "SESSIONID=fine")
    await vault.store(connection.credential_key(USERNAME), "operator")
    await vault.store(connection.credential_key(PASSWORD), "s3cret")
    http.unreachable = True
    driver = FakeSignInDriver()

    ensure = EnsureSignedIn(
        _sign_in(uow, vault, browser, driver), CheckSession(uow, vault, http), uow
    )
    assert await ensure.execute(CTX, target_system="blue_yonder") is False
    # Signing in would not fix an outage, and would throw away a session that
    # may well still work once the system answers again.
    assert driver.calls == 0
    assert await vault.get(connection.cookie_key) == "SESSIONID=fine"


@pytest.mark.asyncio
async def test_a_login_that_needs_a_human_says_so_rather_than_looping() -> None:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    browser, http = FakeBrowserProvider(), FakeHttpCaller()
    connection = await _connection(uow)
    await vault.store(connection.cookie_key, "SESSIONID=expired")
    await vault.store(connection.credential_key(USERNAME), "operator")
    await vault.store(connection.credential_key(PASSWORD), "s3cret")
    http.answer(status_code=302, headers={"location": "https://login.example.org/authorize"})
    driver = FakeSignInDriver(fails="this system asks for a second factor")

    ensure = EnsureSignedIn(
        _sign_in(uow, vault, browser, driver), CheckSession(uow, vault, http), uow
    )
    assert await ensure.execute(CTX, target_system="blue_yonder") is False
    assert browser.closed == [browser.opened[-1]]


@pytest.mark.parametrize(
    ("url", "system"),
    [
        # Two environments of one WMS have to land on one key, or a skill taught
        # in QA is a skill about a different system.
        ("https://bf56-kms-wms-web-np2.jdadelivers.com/portal", "blue_yonder"),
        ("https://prod-wms.jdadelivers.com/portal", "blue_yonder"),
        ("https://wms.acme.com/portal", "acme"),
        ("https://wms.acme.co.uk/portal", "acme"),
    ],
)
def test_the_system_key_comes_from_the_address_not_from_a_person(url: str, system: str) -> None:
    assert _system_from(url) == system


@pytest.mark.asyncio
async def test_the_console_can_watch_because_identity_cookies_are_not_a_session() -> None:
    """What makes "I have signed in" unnecessary.

    An identity provider sets cookies before anybody types a password, so
    "the browser has cookies" said signed-in while the login page was still on
    screen. Keeping is refused until a cookie exists for the system's own host,
    which is what the console polls for.
    """
    uow, vault, browser = FakeUnitOfWork(), FakeCredentialVault(), FakeBrowserProvider()
    connection = await _connection(uow)
    keep = StoreSession(uow, vault, FakeClock(), browser)
    session = await browser.open()

    browser.cookies = ({"name": "x-ms-cpim-csrf", "value": "n", "domain": ".login.example.org"},)
    with pytest.raises(NotAuthenticated):
        await keep.execute(CTX, connection_id=connection.id, browser_session_id=session.id)

    browser.cookies = ({"name": "SESSIONID", "value": "real", "domain": "wms.example.com"},)
    kept = await keep.execute(CTX, connection_id=connection.id, browser_session_id=session.id)

    assert kept.status is ConnectionStatus.CONNECTED
    assert await vault.get(connection.cookie_key) == "SESSIONID=real"


@pytest.mark.asyncio
async def test_the_health_probe_carries_the_session_it_is_asking_about() -> None:
    """It was rebuilt without the cookie once a proved read was found, so every
    check went out unauthenticated and every connection looked signed out --
    leaving the verdict to rest entirely on adopting an open browser."""
    uow, vault, http = FakeUnitOfWork(), FakeCredentialVault(), FakeHttpCaller()
    connection = await _connection(uow)
    await vault.store(connection.cookie_key, "SESSIONID=alive")
    # A skill whose read needs no parameter: that is what the probe picks, and
    # it is the branch where the cookie went missing.
    proved = f.skill(
        versions=0,
        objective_key=f.objective(target_system="blue_yonder"),
    )
    proved.add_version(
        f.skill_version(
            steps=(
                f.step(
                    network_plan=f.network_plan(
                        method="GET",
                        url=Template("https://wms.example.com/data/suppliers?limit=50"),
                        body=None,
                    )
                ),
            )
        )
    )
    skill = proved
    async with uow:
        await uow.skills.add(skill)
        await uow.commit()
    http.answer(status_code=200)

    health = await CheckSession(uow, vault, http).for_system(CTX, target_system="blue_yonder")

    assert health is not None and health.health is SessionHealth.SIGNED_IN
    assert http.sent[0]["headers"]["cookie"] == "SESSIONID=alive"


@pytest.mark.asyncio
async def test_an_open_browser_is_not_a_signed_in_one() -> None:
    """A browser keeps its cookie jar in a profile that outlives the session in
    it, so an expired cookie for the right host read as a completed login. That
    reported "the session works" over a connection whose every call was being
    redirected to the identity provider."""
    uow, vault, http = FakeUnitOfWork(), FakeCredentialVault(), FakeHttpCaller()
    browser = FakeBrowserProvider()
    await browser.open()
    browser.cookies = ({"name": "SESSIONID", "value": "stale", "domain": "wms.example.com"},)
    connection = await _connection(uow)
    await vault.store(connection.cookie_key, "SESSIONID=stale")
    elsewhere = {"location": "https://identity.example.com/oauth2/authorize"}
    # Turned away before adoption, and turned away again with what adoption
    # found -- which is the whole question adoption was answering by itself.
    http.answer(status_code=302, headers=elsewhere)
    http.answer(status_code=302, headers=elsewhere)

    health = await CheckSession(
        uow, vault, http, browser, RefreshSession(uow, vault, FakeClock())
    ).for_system(CTX, target_system="blue_yonder")

    assert health is not None and health.health is SessionHealth.SIGNED_OUT


@pytest.mark.asyncio
async def test_a_browser_is_emptied_before_a_human_signs_into_it() -> None:
    """A provider that keeps one browser keeps one cookie jar.

    A second tenant opened a browser to connect the same system, the WMS showed
    it already signed in as the first tenant, and this flow stored that session
    under the second tenant's name. Nobody typed a password, and one tenant
    ended up holding another's warehouse session -- found by connecting a fresh
    tenant and watching it come up "signed in".
    """
    uow, browser = FakeUnitOfWork(), FakeBrowserProvider()
    browser.cookies = (
        {"name": "REFSSessionID", "value": "somebody-else", "domain": "wms.example.com"},
    )

    opened = await ConnectSystem(uow, browser, FakeClock(), FakeIdFactory()).execute(
        CTX, base_url=WMS
    )

    assert browser.emptied == [opened.browser_session_id], "emptied, and before it was navigated"
    assert browser.cookies == (), "whatever the last tenant left is gone"
