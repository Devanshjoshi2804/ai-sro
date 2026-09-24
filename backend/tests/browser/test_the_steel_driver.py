"""The page driver against a local Chromium, every account in a real browser
context made the way S4 makes one. There is no "no contexts" mode: an account
whose context is not open is `PageGone`, whatever else the browser holds."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from sro.application.ports.page import PageGone, SessionRef
from sro.config import get_settings
from sro.infrastructure.steel import driver as driver_module
from sro.infrastructure.steel.client import websocket_debugger_url
from sro.infrastructure.steel.driver import SteelDriver
from tests.browser.steel_rig import (  # noqa: F401
    Rig,
    cdp_url,
    cdp_url_2,
    close_account,
    driver,
    elsewhere,
    one,
    pages_in,
    rig,
    two,
)

pytestmark = pytest.mark.browser


async def test_a_restarted_worker_finds_its_tab_and_the_page_code_is_still_there(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
) -> None:
    first = SteelDriver(get_settings().page_code_path)
    target = await first.open_tab(one, rig.url("/public"))
    await first.aclose()

    again = SteelDriver(get_settings().page_code_path)
    try:
        await again.goto(one, target, rig.url("/public?next"))

        assert (await again.url_of(one, target)).endswith("/public?next")
        assert await again.evaluate(one, target, "typeof globalThis.sroPage") == "object"
    finally:
        await again.aclose()


async def test_the_page_code_is_in_every_new_document(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))

    assert await driver.evaluate(one, target, "typeof globalThis.sroPage") == "object"


async def test_saved_state_signs_a_fresh_browser_in_even_across_a_restart(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    elsewhere: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    await driver.evaluate(one, target, "localStorage.setItem('kept', 'yes')")
    state = await driver.storage_state(one)

    restorer = SteelDriver(get_settings().page_code_path)
    await restorer.restore_state(elsewhere, state)
    await restorer.aclose()
    landed = await driver.open_tab(elsewhere, rig.url("/app"))

    assert (await driver.url_of(elsewhere, landed)).endswith("/app")
    assert await driver.evaluate(elsewhere, landed, "localStorage.getItem('kept')") == "yes"


async def test_one_account_never_reaches_another_accounts_tab(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    two: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))

    with pytest.raises(PageGone):
        await driver.url_of(two, target)
    with pytest.raises(PageGone):
        await driver.goto(two, target, rig.url("/"))
    with pytest.raises(PageGone):
        await driver.close_tab(two, target)
    assert (await driver.url_of(one, target)).endswith("/public")


async def test_six_tabs_opened_at_once_across_two_accounts_each_stay_with_their_own(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    two: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    accounts = [one, two] * 3

    targets = await asyncio.gather(
        *(driver.open_tab(who, rig.url(f"/public?{n}")) for n, who in enumerate(accounts))
    )

    assert len(set(targets)) == 6
    for n, (who, target) in enumerate(zip(accounts, targets, strict=True)):
        other = two if who is one else one
        assert (await driver.url_of(who, target)).endswith(f"/public?{n}")
        with pytest.raises(PageGone):
            await driver.url_of(other, target)
    assert sorted(await pages_in(one)) == sorted(targets[0::2])
    assert sorted(await pages_in(two)) == sorted(targets[1::2])


async def test_a_context_that_is_gone_is_page_gone_even_when_no_context_is_left(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    two: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    await close_account(one)

    with pytest.raises(PageGone):
        await driver.url_of(one, target)
    with pytest.raises(PageGone):
        await driver.open_tab(one, rig.url("/public"))

    await close_account(two)
    cookie = '{"cookies": [{"name": "a", "value": "b", "domain": "127.0.0.1", "path": "/"}]}'

    with pytest.raises(PageGone):
        await driver.open_tab(one, rig.url("/public"))
    with pytest.raises(PageGone):
        await driver.restore_state(one, cookie)
    with pytest.raises(PageGone):
        await driver.storage_state(one)
    with pytest.raises(PageGone):
        await driver.storage_state(SessionRef("some-other-account", one.cdp_url))


async def test_a_tab_that_never_attaches_is_closed_and_page_gone(
    monkeypatch: pytest.MonkeyPatch,
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    async def never(*_: Any) -> None:
        return None

    monkeypatch.setattr(driver_module, "K_ATTACH_TIMEOUT_S", 0.5)
    monkeypatch.setattr(driver, "_arrived", never)

    with pytest.raises(PageGone):
        await driver.open_tab(one, rig.url("/public"))

    assert await pages_in(one) == []


async def test_the_cdp_url_can_be_a_name_or_a_websocket_and_a_stale_one_is_page_gone(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    assert one.cdp_url.startswith("http://localhost:"), "a name, which Chrome refuses as a Host"
    target = await driver.open_tab(one, rig.url("/public"))

    async with httpx.AsyncClient() as client:
        resolved = await websocket_debugger_url(one.cdp_url, client)
    by_websocket = SessionRef(one.context_id, resolved.replace("127.0.0.1", "localhost"))
    assert (await driver.url_of(by_websocket, target)).endswith("/public")

    stale = SessionRef(one.context_id, resolved.rsplit("/", 1)[0] + "/not-this-browser")
    with pytest.raises(PageGone):
        await driver.url_of(stale, target)
    with pytest.raises(PageGone):
        await driver.open_tab(SessionRef(one.context_id, "http://127.0.0.1:1"), "about:blank")


async def test_a_listener_hears_only_its_own_account(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    two: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    heard: list[str] = []
    await driver.on(one, "request", lambda request: heard.append(request.url))

    other = await driver.open_tab(two, rig.url("/public?two"))
    await driver.goto(two, other, rig.url("/public?two-again"))
    assert heard == [], "account one heard account two's traffic"

    await driver.open_tab(one, rig.url("/public?one"))
    assert any(url.endswith("/public?one") for url in heard)
    assert not any("two" in url for url in heard)
