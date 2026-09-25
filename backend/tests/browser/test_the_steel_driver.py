"""The page driver against a local Chromium, every account in a real browser
context made the way S4 makes one. There is no "no contexts" mode: an account
whose context is not open is `PageGone`, whatever else the browser holds."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import httpx
import pytest
from playwright.async_api import async_playwright

from sro.application.ports.page import PageGone, SessionRef
from sro.config import get_settings
from sro.domain.observation.gesture import AfterState
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


async def test_a_tab_closed_mid_evaluate_is_page_gone_not_a_raw_playwright_error(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))

    async def close_soon() -> None:
        await asyncio.sleep(0.1)
        await driver.close_tab(one, target)

    closer = asyncio.create_task(close_soon())
    try:
        with pytest.raises(PageGone):
            await driver.evaluate(one, target, "new Promise(() => {})")
    finally:
        await closer


async def test_goto_on_a_disposed_context_is_page_gone_within_a_bound_not_a_30s_hang(
    monkeypatch: pytest.MonkeyPatch,
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    monkeypatch.setattr(driver_module, "K_ACTION_TIMEOUT_S", 1.0)
    target = await driver.open_tab(one, rig.url("/public"))

    stall = await asyncio.start_server(lambda *_: None, "127.0.0.1", 0)
    async with stall:
        host, port = stall.sockets[0].getsockname()[:2]
        serving = asyncio.create_task(stall.serve_forever())
        try:
            await close_account(one)

            loop = asyncio.get_running_loop()
            started = loop.time()
            with pytest.raises(PageGone):
                await driver.goto(one, target, f"http://{host}:{port}/")
            assert loop.time() - started < 10, "goto hung instead of respecting the deadline"
        finally:
            serving.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await serving


async def test_open_tab_closes_the_orphan_tab_when_it_is_gone_mid_navigation(
    monkeypatch: pytest.MonkeyPatch,
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    monkeypatch.setattr(driver_module, "K_ACTION_TIMEOUT_S", 1.0)
    original_call = driver._call

    async def call_after_the_tab_is_gone(
        session: SessionRef, target_id: str, page: Any, action: Any
    ) -> Any:
        await page.close()
        return await original_call(session, target_id, page, action)

    monkeypatch.setattr(driver, "_call", call_after_the_tab_is_gone)

    loop = asyncio.get_running_loop()
    started = loop.time()
    with pytest.raises(PageGone):
        await driver.open_tab(one, rig.url("/public"))
    assert loop.time() - started < 10, "open_tab hung instead of respecting the deadline"

    assert await pages_in(one) == [], "the orphan tab was left behind"


async def test_a_listener_survives_a_reconnect_while_the_context_stays_alive(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    heard: list[str] = []
    await driver.on(one, "request", lambda request: heard.append(request.url))

    target = await driver.open_tab(one, rig.url("/public?before"))
    assert any(url.endswith("/public?before") for url in heard)

    await driver._links[cdp_url].browser.close()

    await driver.goto(one, target, rig.url("/public?after"))
    assert any(url.endswith("/public?after") for url in heard)


async def test_the_default_context_id_never_reaches_a_default_tab(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    async with httpx.AsyncClient() as client:
        endpoint = await websocket_debugger_url(cdp_url, client)
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(endpoint)
        raw = await browser.new_browser_cdp_session()
        made = await raw.send("Target.createTarget", {"url": rig.url("/public")})
        default_target = str(made["targetId"])
        found = await raw.send("Target.getBrowserContexts")
        default_context = str(found["defaultBrowserContextId"])
        await browser.close()

    with pytest.raises(PageGone):
        await driver.url_of(SessionRef(default_context, cdp_url), default_target)


def in_the_app_frame(app: Rig, action: str, css: str, value: str | None = None) -> dict[str, Any]:
    return {
        "action": action,
        "value": value,
        "target": {"css_path": css},
        "frame_path": [{"index": 1, "url": app.url("/app")}],
    }


async def signed_in_on_the_framed_page(app: Rig, through: SteelDriver, who: SessionRef) -> str:
    target = await through.open_tab(who, app.url("/"))
    await app.sign_in_in(through, who, target)
    await through.goto(who, target, app.url("/framed"))
    return target


async def test_act_in_the_recorded_frame_is_confirmed_by_its_state_and_its_own_call(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await signed_in_on_the_framed_page(rig, driver, one)
    typing = in_the_app_frame(rig, "type", "#ct", "GT2")
    mark = await driver.mark(one, target)

    typed = await driver.act(one, target, typing)

    assert (typed.ok, typed.matched_by, typed.repaired) == (True, "css_path", False)
    assert typed.pin
    assert typed.state == AfterState(value="GT2", visible=True, enabled=True)
    held = {**typing, "pin": typed.pin, "expect": {"value": "GT2"}}
    assert await driver.wait_for(one, target, held, 5.0) is True
    wrong = {**typing, "pin": typed.pin, "expect": {"value": "not-typed"}}
    assert await driver.wait_for(one, target, wrong, 0.5) is False

    saved = await driver.act(one, target, in_the_app_frame(rig, "click", "#save"))
    assert saved.ok

    assert await driver.wait_for_call(
        one, target, method="POST", shape="/api/customer-types", since=mark, deadline_s=5.0
    )
    posts = [c for c in await driver.calls_since(one, target, mark) if c.method == "POST"]
    assert [(c.status, c.body) for c in posts] == [(201, '{"ok": true}')]
    assert await driver.calls_since(one, target, await driver.mark(one, target)) == ()


async def test_act_without_a_frame_path_finds_the_one_frame_holding_the_control(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await signed_in_on_the_framed_page(rig, driver, one)

    typed = await driver.act(
        one, target, {**in_the_app_frame(rig, "type", "#ct", "GT3"), "frame_path": None}
    )

    assert typed.ok and typed.state == AfterState(value="GT3", visible=True, enabled=True)
    missing = await driver.act(one, target, in_the_app_frame(rig, "click", "#nowhere"))
    assert (missing.ok, missing.error_kind) == (False, "control_not_found")


async def test_one_account_never_sees_another_accounts_calls(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    two: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    mine = await driver.open_tab(one, rig.url("/public"))
    mark = await driver.mark(one, mine)
    theirs = await signed_in_on_the_framed_page(rig, driver, two)
    their_mark = await driver.mark(two, theirs)

    await driver.act(two, theirs, in_the_app_frame(rig, "type", "#ct", "B"))
    await driver.act(two, theirs, in_the_app_frame(rig, "click", "#save"))

    assert await driver.wait_for_call(
        two, theirs, method="POST", shape="/api/customer-types", since=their_mark, deadline_s=5.0
    )
    assert await driver.calls_since(one, mine, mark) == ()
    assert not await driver.wait_for_call(
        one, mine, method="POST", shape="/api/customer-types", since=mark, deadline_s=0.5
    )
    with pytest.raises(PageGone):
        await driver.mark(one, theirs)
    with pytest.raises(PageGone):
        await driver.calls_since(one, theirs, 0)


async def test_every_wait_on_a_tab_that_closes_is_page_gone_before_its_deadline(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    mark = await driver.mark(one, target)
    loop = asyncio.get_running_loop()

    async def close_soon() -> None:
        await asyncio.sleep(0.2)
        await driver.close_tab(one, target)

    started = loop.time()
    closer = asyncio.create_task(close_soon())
    try:
        with pytest.raises(PageGone):
            await driver.wait_for_call(
                one, target, method="POST", shape="/x", since=mark, deadline_s=30.0
            )
    finally:
        await closer
    assert loop.time() - started < 10, "the wait ran to its deadline on a closed tab"

    with pytest.raises(PageGone):
        await driver.wait_for(one, target, {"pin": "p", "expect": {}}, 30.0)
    with pytest.raises(PageGone):
        await driver.act(one, target, {"action": "click", "target": {"css_path": "h1"}})


async def test_wait_for_on_a_tab_closed_mid_wait_is_page_gone(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))

    async def close_soon() -> None:
        await asyncio.sleep(0.2)
        await driver.close_tab(one, target)

    closer = asyncio.create_task(close_soon())
    try:
        with pytest.raises(PageGone):
            await driver.wait_for(one, target, {"pin": "never", "expect": {}}, 30.0)
    finally:
        await closer
