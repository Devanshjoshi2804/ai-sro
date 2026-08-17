"""A stored session is only worth storing if it is kept current.

Written once at connect and never again, the session in the vault names a
session the server has already rotated away from. Restoring it lands the
operator on the login page -- the exact thing connecting once was meant to
prevent. Every capture that ends signed in refreshes it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from sro.application.connection.check_session import CheckSession, SessionHealth
from sro.application.connection.connect_system import RefreshSession
from sro.application.context import RequestContext
from sro.domain.connection.connection import Connection, ConnectionId
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

WMS = "https://wms.example.com/portal"


def _cookie(name: str, value: str, domain: str = "wms.example.com") -> dict[str, object]:
    return {"name": name, "value": value, "domain": domain, "path": "/"}


async def _connected(uow: FakeUnitOfWork) -> Connection:
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


@pytest.mark.asyncio
async def test_a_signed_in_capture_replaces_the_session_it_started_with() -> None:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    connection = await _connected(uow)
    await vault.store(connection.session_key, json.dumps({"origin": WMS, "cookies": []}))

    refreshed = await RefreshSession(uow, vault, FakeClock()).execute(
        CTX, cookies=[_cookie("SESSIONID", "rotated")]
    )

    assert refreshed == 1
    stored = json.loads(await vault.get(connection.session_key) or "{}")
    assert stored["cookies"] == [_cookie("SESSIONID", "rotated")]
    # Both forms, or the executor keeps sending the header the browser no
    # longer agrees with.
    assert await vault.get(connection.cookie_key) == "SESSIONID=rotated"


@pytest.mark.asyncio
async def test_cookies_from_somewhere_else_never_overwrite_a_good_session() -> None:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    connection = await _connected(uow)
    await vault.store(connection.cookie_key, "SESSIONID=good")

    refreshed = await RefreshSession(uow, vault, FakeClock()).execute(
        CTX, cookies=[_cookie("other", "x", domain="unrelated.example.org")]
    )

    assert refreshed == 0
    assert await vault.get(connection.cookie_key) == "SESSIONID=good"


@pytest.mark.asyncio
async def test_a_capture_that_held_no_cookies_leaves_the_session_alone() -> None:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    connection = await _connected(uow)
    await vault.store(connection.cookie_key, "SESSIONID=good")

    assert await RefreshSession(uow, vault, FakeClock()).execute(CTX, cookies=[]) == 0
    assert await vault.get(connection.cookie_key) == "SESSIONID=good"


@pytest.mark.asyncio
async def test_a_capture_that_ended_logged_out_does_not_replace_a_working_session() -> None:
    """The failure this whole mechanism could cause if it trusted "has cookies".

    Signed out, the browser still holds the routing and anti-forgery cookies. It
    has lost the session one, and refreshing from it would overwrite a session
    that still works.
    """
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    connection = await _connected(uow)
    await vault.store(connection.cookie_key, "SESSIONID=good; CSRF=abc")

    refreshed = await RefreshSession(uow, vault, FakeClock()).execute(
        CTX, cookies=[_cookie("CSRF", "def")]
    )

    assert refreshed == 0
    assert await vault.get(connection.cookie_key) == "SESSIONID=good; CSRF=abc"


@pytest.mark.asyncio
async def test_a_dead_session_is_found_by_asking_not_by_waiting() -> None:
    uow, vault, http = FakeUnitOfWork(), FakeCredentialVault(), FakeHttpCaller()
    connection = await _connected(uow)
    await vault.store(connection.cookie_key, "SESSIONID=expired")
    http.answer(status_code=302, headers={"location": "https://login.example.org/oauth2/authorize"})

    (check,) = await CheckSession(uow, vault, http).execute(CTX)

    assert check.health is SessionHealth.SIGNED_OUT
    # The connection row still says connected. That is exactly why asking beats
    # remembering.
    assert http.sent[0]["headers"] == {"cookie": "SESSIONID=expired"}


@pytest.mark.asyncio
async def test_a_system_that_is_down_is_not_reported_as_a_bad_session() -> None:
    uow, vault, http = FakeUnitOfWork(), FakeCredentialVault(), FakeHttpCaller()
    connection = await _connected(uow)
    await vault.store(connection.cookie_key, "SESSIONID=fine")
    http.unreachable = True

    (check,) = await CheckSession(uow, vault, http).execute(CTX)

    # Signing in again would not fix an outage, so it must not be asked for.
    assert check.health is SessionHealth.UNREACHABLE


@pytest.mark.asyncio
async def test_a_redirect_inside_the_system_is_not_a_login_page() -> None:
    uow, vault, http = FakeUnitOfWork(), FakeCredentialVault(), FakeHttpCaller()
    connection = await _connected(uow)
    await vault.store(connection.cookie_key, "SESSIONID=fine")
    http.answer(status_code=302, headers={"location": "https://wms.example.com/portal/home"})

    (check,) = await CheckSession(uow, vault, http).execute(CTX)

    assert check.health is SessionHealth.SIGNED_IN


@pytest.mark.asyncio
async def test_a_login_nobody_was_watching_is_adopted() -> None:
    """Three times in one afternoon a good session was thrown away.

    An operator signed in inside a browser this deployment had open, and the
    console reported them signed out because nothing happened to be polling
    that particular window. Signing in is the whole job; noticing is ours.
    """
    uow, vault, browser, http = (
        FakeUnitOfWork(),
        FakeCredentialVault(),
        FakeBrowserProvider(),
        FakeHttpCaller(),
    )
    connection = await _connected(uow)
    await vault.store(connection.cookie_key, "SESSIONID=expired")
    http.answer(status_code=302, headers={"location": "https://login.example.org/authorize"})

    # A browser this deployment opened, in which somebody has signed in.
    await browser.open()
    browser.cookies = ({"name": "SESSIONID", "value": "signed-in", "domain": "wms.example.com"},)

    check = CheckSession(uow, vault, http, browser, RefreshSession(uow, vault, FakeClock()))
    (found,) = await check.execute(CTX)

    assert found.health is SessionHealth.SIGNED_IN
    assert await vault.get(connection.cookie_key) == "SESSIONID=signed-in"


@pytest.mark.asyncio
async def test_nothing_is_adopted_from_a_browser_holding_nothing() -> None:
    """An open browser is not a signed-in one, and an empty one must not
    overwrite a session that is merely expired."""
    uow, vault, browser, http = (
        FakeUnitOfWork(),
        FakeCredentialVault(),
        FakeBrowserProvider(),
        FakeHttpCaller(),
    )
    connection = await _connected(uow)
    await vault.store(connection.cookie_key, "SESSIONID=expired")
    http.answer(status_code=302, headers={"location": "https://login.example.org/authorize"})

    await browser.open()
    browser.cookies = ({"name": "x-ms-cpim-csrf", "value": "n", "domain": ".login.example.org"},)

    check = CheckSession(uow, vault, http, browser, RefreshSession(uow, vault, FakeClock()))
    (found,) = await check.execute(CTX)

    assert found.health is SessionHealth.SIGNED_OUT
    assert await vault.get(connection.cookie_key) == "SESSIONID=expired"
