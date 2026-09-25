"""The page driver against a local Chromium, every account in a real browser
context made the way S4 makes one. There is no "no contexts" mode: an account
whose context is not open is `PageGone`, whatever else the browser holds."""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import replace
from typing import Any, Literal

import httpx
import pytest
from playwright.async_api import async_playwright

from sro.application.ports.page import PageGone, PageUnsettled, SessionRef
from sro.application.ports.vision import ProposedGesture
from sro.application.runtime.sight_lane import SightLane
from sro.application.runtime.ui_lane import same_call
from sro.config import get_settings
from sro.domain.execution.compose import Adding
from sro.domain.observation.gesture import AfterState, Body, Call
from sro.domain.recording.events import ActionKind
from sro.domain.shared.hosts import origin_of, system_of
from sro.domain.shared.identifiers import BrowserSessionId
from sro.domain.skill.signing_in import a_sign_in_page, asks_for_a_code, expired
from sro.infrastructure.steel import driver as driver_module
from sro.infrastructure.steel.client import SteelClient, websocket_debugger_url
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
from tests.unit.fakes import FakeVisionDriver
from tests.unit.runtime_support import lane_context, save_step

pytestmark = pytest.mark.browser

PING = "fetch('/api/ping', {method: 'POST'})"
SAVE = "document.getElementById('save').click()"
BASIC = """new Promise((done) => {
  const asking = new XMLHttpRequest();
  asking.open("GET", "/api/basic", true, "u", "p");
  asking.onloadend = () => done(asking.status);
  asking.send();
})"""


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
    async def never(*_: Any, **__: Any) -> None:
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


async def test_an_ambiguous_probe_on_old_evidence_is_refused_not_the_main_frame(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    await driver.goto(one, target, rig.url("/framed-twice"))

    result = await driver.act(
        one, target, {**in_the_app_frame(rig, "click", "#save"), "frame_path": None}
    )

    assert (result.ok, result.error_kind) == (False, "frame_ambiguous")


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

    await driver.evaluate(one, mine, PING)
    await driver.act(two, theirs, in_the_app_frame(rig, "type", "#ct", "B"))
    await driver.act(two, theirs, in_the_app_frame(rig, "click", "#save"))

    assert await driver.wait_for_call(
        two, theirs, method="POST", shape="/api/customer-types", since=their_mark, deadline_s=5.0
    )
    assert await driver.wait_for_call(
        one, mine, method="POST", shape="/api/ping", since=mark, deadline_s=5.0
    )
    assert [(c.method, c.url, c.status) for c in await driver.calls_since(one, mine, mark)] == [
        ("POST", rig.url("/api/ping"), 201)
    ]
    theirs_calls = await driver.calls_since(two, theirs, their_mark)
    assert any(c.url == rig.url("/api/customer-types") for c in theirs_calls)
    assert all(c.url != rig.url("/api/ping") for c in theirs_calls)
    assert not await driver.wait_for_call(
        one, mine, method="POST", shape="/api/customer-types", since=mark, deadline_s=0.5
    )
    with pytest.raises(PageGone):
        await driver.mark(one, theirs)
    with pytest.raises(PageGone):
        await driver.calls_since(one, theirs, 0)


async def test_a_token_the_page_sent_before_anyone_asked_is_found_at_once(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    two: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    app_origin = origin_of(rig.url("/app"))
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    since = await driver.mark(one, target)
    await driver.evaluate(one, target, SAVE)
    assert await driver.wait_for_call(
        one, target, method="POST", shape="/api/customer-types", since=since, deadline_s=5.0
    )

    started = asyncio.get_running_loop().time()
    got = await driver.headers_for(one, app_origin, 5.0, needs=("x-csrf-token",))
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 2.0
    assert set(got) == {"x-csrf-token"}
    assert got["x-csrf-token"]

    await driver.open_tab(two, rig.url("/public"))
    assert await driver.headers_for(two, origin_of(rig.url("/public")), 0.3) == {}


async def test_nothing_needed_is_answered_at_once_from_a_context_that_sent_no_token(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    await driver.open_tab(one, rig.url("/public"))
    loop = asyncio.get_running_loop()
    started = loop.time()

    got = await driver.headers_for(one, origin_of(rig.url("/public")), 10.0)

    assert got == {}
    assert loop.time() - started < 1.0


async def test_a_needed_token_that_never_comes_is_answered_inside_the_deadline(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    """The deadline bounds the whole call, the round trips to Chrome
    included: a caller holding its own budget gets the partial answer back
    before that budget is gone, and can say which header was missing."""
    await driver.open_tab(one, rig.url("/public"))
    loop = asyncio.get_running_loop()
    started = loop.time()

    got = await driver.headers_for(one, origin_of(rig.url("/public")), 0.5, needs=("x-csrf-token",))

    assert got == {}
    assert loop.time() - started < 0.5 + 0.05


async def test_a_context_that_dies_with_no_wake_is_page_gone_at_the_deadline(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    """A death nothing announces -- the wake lost between a wait and its
    re-check, a tab whose close listener never registered, a browser that
    restarted behind a proxy that kept the socket -- is still `PageGone`:
    the deadline keeps room for one last look at the context."""
    await driver.open_tab(one, rig.url("/public"))
    parked = asyncio.Event()

    class Deaf(asyncio.Event):
        def set(self) -> None:
            return None

        async def wait(self) -> Literal[True]:
            parked.set()
            return await super().wait()

    driver._seen[(one.cdp_url, one.context_id)] = Deaf()
    waiting = asyncio.create_task(
        driver.headers_for(one, origin_of(rig.url("/app")), 2.0, needs=("x-csrf-token",))
    )
    await asyncio.wait_for(parked.wait(), 5.0)
    await close_account(one)
    loop = asyncio.get_running_loop()
    started = loop.time()

    with pytest.raises(PageGone):
        await waiting
    assert loop.time() - started < 2.0 + 0.05


async def test_a_tab_cancelled_while_its_page_loads_is_closed(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    opening = asyncio.create_task(driver.open_tab(one, rig.url("/held-login")))
    assert await asyncio.to_thread(rig.asked.wait, 10.0)

    opening.cancel()
    with pytest.raises(asyncio.CancelledError):
        await opening

    assert await pages_in(one) == []


async def test_a_fresh_token_is_never_one_sent_before_the_mark(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    app_origin = origin_of(rig.url("/app"))
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    await driver.evaluate(one, target, SAVE)
    assert await driver.headers_for(one, app_origin, 5.0, needs=("x-csrf-token",))

    since = await driver.mark(one, target)
    await driver.goto(one, target, await driver.url_of(one, target))

    assert await driver.headers_for(one, app_origin, 0.5, since=since) == {}
    await driver.evaluate(one, target, SAVE)
    assert set(
        await driver.headers_for(one, app_origin, 5.0, since=since, needs=("x-csrf-token",))
    ) == {"x-csrf-token"}


async def test_no_header_sent_before_a_forgotten_mark_is_answered_until_forget(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    app_origin = origin_of(rig.url("/app"))
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    await driver.evaluate(one, target, SAVE)
    assert await driver.headers_for(one, app_origin, 5.0)

    await driver.forget_headers_before(one, await driver.mark(one, target))

    assert await driver.headers_for(one, app_origin, 0.5) == {}
    await driver.evaluate(one, target, SAVE)
    assert set(await driver.headers_for(one, app_origin, 5.0)) == {"x-csrf-token"}
    await driver.forget(one)
    assert (one.cdp_url, one.context_id) not in driver._floors


ASKED = "fetch('/api/ping', {headers: {'X-Requested-With': 'XMLHttpRequest'}})"


async def test_each_token_is_its_newest_value_not_only_the_newest_request(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    app_origin = origin_of(rig.url("/app"))
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    since = await driver.mark(one, target)
    await driver.evaluate(one, target, SAVE)
    assert await driver.wait_for_call(
        one, target, method="POST", shape="/api/customer-types", since=since, deadline_s=5.0
    )
    await driver.evaluate(one, target, ASKED)

    got = await driver.headers_for(
        one, app_origin, 5.0, since=since, needs=("x-csrf-token", "x-requested-with")
    )

    assert got["x-requested-with"] == "XMLHttpRequest"
    assert got["x-csrf-token"]


async def test_a_needed_token_that_arrives_after_the_call_starts_is_waited_for(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    app_origin = origin_of(rig.url("/app"))
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    since = await driver.mark(one, target)
    await driver.evaluate(one, target, ASKED)
    parked = asyncio.Event()

    class Seen(asyncio.Event):
        async def wait(self) -> Literal[True]:
            parked.set()
            return await super().wait()

    driver._seen[(one.cdp_url, one.context_id)] = Seen()
    waiting = asyncio.create_task(
        driver.headers_for(one, app_origin, 10.0, since=since, needs=("x-csrf-token",))
    )
    await asyncio.wait_for(parked.wait(), 5.0)

    await driver.evaluate(one, target, SAVE)

    got = await waiting
    assert got["x-csrf-token"]
    assert got["x-requested-with"] == "XMLHttpRequest"


async def test_a_needed_token_that_never_arrives_is_absent_at_the_deadline(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    app_origin = origin_of(rig.url("/app"))
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    since = await driver.mark(one, target)
    await driver.evaluate(one, target, ASKED)

    got = await driver.headers_for(one, app_origin, 1.0, since=since, needs=("x-csrf-token",))

    assert got == {"x-requested-with": "XMLHttpRequest"}


async def test_an_authorization_the_browser_adds_itself_is_seen(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    assert await driver.evaluate(one, target, BASIC) == 200

    await driver.evaluate(one, target, "fetch('/api/basic').then((r) => r.status)")

    got = await driver.headers_for(
        one, origin_of(rig.url("/public")), 5.0, needs=("authorization",)
    )
    assert got == {"authorization": "Basic dTpw"}


async def test_forgetting_a_context_drops_every_header_it_sent(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    app_origin = origin_of(rig.url("/app"))
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    await driver.evaluate(one, target, SAVE)
    assert await driver.headers_for(one, app_origin, 5.0, needs=("x-csrf-token",))

    await driver.forget(one)

    assert (one.cdp_url, one.context_id) not in driver._requests
    assert (one.cdp_url, one.context_id) not in driver._seen
    assert await driver.headers_for(one, app_origin, 0.3) == {}


async def test_a_context_that_dies_while_headers_are_awaited_is_page_gone(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    await driver.open_tab(one, rig.url("/public"))
    loop = asyncio.get_running_loop()
    parked = asyncio.Event()

    class Seen(asyncio.Event):
        async def wait(self) -> Literal[True]:
            parked.set()
            return await super().wait()

    driver._seen[(one.cdp_url, one.context_id)] = Seen()
    waiting = asyncio.create_task(
        driver.headers_for(one, origin_of(rig.url("/app")), 10.0, needs=("x-csrf-token",))
    )
    await asyncio.wait_for(parked.wait(), 5.0)
    started = loop.time()

    await close_account(one)

    with pytest.raises(PageGone):
        await waiting
    assert loop.time() - started < 5.0


async def test_two_marks_at_once_listen_once(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))

    await asyncio.gather(driver.mark(one, target), driver.mark(one, target))

    listening = driver._listeners[(one.cdp_url, one.context_id)]
    assert [event for event, _ in listening] == ["request", "response"]


async def test_every_wait_on_a_tab_that_closes_is_page_gone_before_its_deadline(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    mark = await driver.mark(one, target)
    loop = asyncio.get_running_loop()
    waiting = asyncio.Event()
    logged = driver._log

    def log_and_tell(page: Any) -> Any:
        waiting.set()
        return logged(page)

    driver._log = log_and_tell  # type: ignore[method-assign]

    async def close_once_waiting() -> None:
        await waiting.wait()
        await driver.close_tab(one, target)

    started = loop.time()
    closer = asyncio.create_task(close_once_waiting())
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
    await driver.evaluate(
        one,
        target,
        """(() => {
          const holds = globalThis.sroPage.holds;
          globalThis.sroPage.holds = (p) => {
            if (!window.__told) {
              window.__told = true;
              fetch("/api/ping", { method: "POST" });
            }
            return holds(p);
          };
        })()""",
    )

    async def close_once_waiting() -> None:
        assert await asyncio.to_thread(rig.pinged.wait, 10)
        await driver.close_tab(one, target)

    closer = asyncio.create_task(close_once_waiting())
    try:
        with pytest.raises(PageGone):
            await driver.wait_for(one, target, {"pin": "never", "expect": {}}, 30.0)
    finally:
        await closer


async def test_a_password_page_is_recognised_across_the_oidc_round_trip_and_stops_after_sign_in(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/"))

    assert a_sign_in_page(await driver.signals(one, target))

    await rig.sign_in_in(driver, one, target)

    assert not a_sign_in_page(await driver.signals(one, target))


async def test_a_one_time_code_field_is_recognised_by_its_autocomplete(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    await driver.evaluate(
        one,
        target,
        "document.body.insertAdjacentHTML('beforeend', '<input autocomplete=\"one-time-code\">')",
    )

    signals = await driver.signals(one, target)

    assert a_sign_in_page(signals) and asks_for_a_code(signals)


async def test_two_accounts_signals_never_cross(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    two: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    signing_in = await driver.open_tab(one, rig.url("/"))
    elsewhere_target = await driver.open_tab(two, rig.url("/public"))

    assert a_sign_in_page(await driver.signals(one, signing_in))

    other_signals = await driver.signals(two, elsewhere_target)
    assert not a_sign_in_page(other_signals)
    assert not any("idp/authorize" in visited for visited in other_signals.visited)


@pytest.mark.parametrize(
    ("start", "lands"),
    [("/?response_mode=fragment", "/cb"), ("/?response_mode=form_post", "/app")],
)
async def test_the_round_trip_ends_whatever_way_the_code_comes_back(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
    start: str,
    lands: str,
) -> None:
    target = await driver.open_tab(one, rig.url(start))
    assert a_sign_in_page(await driver.signals(one, target))

    await rig.sign_in_in(driver, one, target, lands=lands)
    assert not a_sign_in_page(await driver.signals(one, target))

    await driver.goto(one, target, rig.url("/public"))
    assert not a_sign_in_page(await driver.signals(one, target))


async def test_an_error_return_ends_the_round_trip(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/?prompt=none"))

    signals = await driver.signals(one, target)

    assert "/cb" in signals.url and not a_sign_in_page(signals)


async def test_the_round_trip_alone_marks_an_identifier_first_page(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/?acr_values=identifier"))

    signals = await driver.signals(one, target)

    assert not signals.password and "username" in signals.autocomplete
    assert a_sign_in_page(signals)


async def test_the_navigation_log_keeps_no_parameter_value(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)

    signals = await driver.signals(one, target)

    assert signals.visited
    assert all(
        "=" not in url.partition("?")[2].replace("redirect_uri=", "") for url in signals.visited
    )
    assert any(url.endswith("/cb?code&state") for url in signals.visited)


async def test_a_login_form_arriving_mid_navigation_is_read_once_it_has_loaded(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    await driver.evaluate(one, target, f"location.href = {rig.url('/held-login')!r}")
    assert await asyncio.to_thread(rig.asked.wait, 10.0)

    reading = asyncio.create_task(driver.signals(one, target))
    early, _ = await asyncio.wait({reading}, timeout=1.0)
    rig.answer.set()

    assert not early and (await reading).password


async def test_a_tab_closed_while_its_signals_are_read_is_page_gone(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    await driver.evaluate(one, target, f"location.href = {rig.url('/held-login')!r}")
    assert await asyncio.to_thread(rig.asked.wait, 10.0)

    reading = asyncio.create_task(driver.signals(one, target))
    await driver.close_tab(one, target)

    with pytest.raises(PageGone):
        await reading


async def test_a_held_main_frame_navigation_is_page_unsettled_not_a_raw_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    monkeypatch.setattr(driver_module, "K_ACTION_TIMEOUT_S", 1.0)
    target = await driver.open_tab(one, rig.url("/public"))
    await driver.evaluate(one, target, f"location.href = {rig.url('/held-login')!r}")
    assert await asyncio.to_thread(rig.asked.wait, 10.0)

    with pytest.raises(PageUnsettled):
        await driver.signals(one, target)


async def test_a_tab_whose_log_was_lost_to_a_restart_is_never_read_as_outside_a_round_trip(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
) -> None:
    first = SteelDriver(get_settings().page_code_path)
    target = await first.open_tab(one, rig.url("/?acr_values=identifier"))
    await first.aclose()

    again = SteelDriver(get_settings().page_code_path)
    try:
        signals = await again.signals(one, target)
    finally:
        await again.aclose()

    assert signals.visited is None and a_sign_in_page(signals)


async def test_an_adopted_tab_reads_normally_after_its_next_clean_navigation(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
) -> None:
    first = SteelDriver(get_settings().page_code_path)
    target = await first.open_tab(one, rig.url("/app"))
    await first.aclose()

    again = SteelDriver(get_settings().page_code_path)
    try:
        await again.goto(one, target, rig.url("/public?one"))
        await again.goto(one, target, rig.url("/public?two"))

        signals = await again.signals(one, target)
    finally:
        await again.aclose()

    assert signals.visited is not None
    assert not a_sign_in_page(signals)
    assert not expired(signals, "/app")


async def test_a_request_sent_before_the_mark_is_never_the_steps_own_call(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    first = await driver.mark(one, target)
    await driver.evaluate(one, target, "void fetch('/api/ping?hold', {method: 'POST'})")
    assert await asyncio.to_thread(rig.pinged.wait, 10)

    mark = await driver.mark(one, target)
    rig.release.set()

    assert await driver.wait_for_call(
        one, target, method="POST", shape="/api/ping", since=first, deadline_s=5.0
    )
    assert await driver.calls_since(one, target, mark) == ()
    assert not await driver.wait_for_call(
        one, target, method="POST", shape="/api/ping", since=mark, deadline_s=0.5
    )


async def test_a_mark_taken_before_a_reconnect_sees_no_calls_at_all(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    mark = await driver.mark(one, target)

    await driver._links[cdp_url].browser.close()
    after = await driver.mark(one, target)
    await driver.evaluate(one, target, PING)

    assert await driver.wait_for_call(
        one, target, method="POST", shape="/api/ping", since=after, deadline_s=5.0
    )
    assert await driver.calls_since(one, target, mark) == ()
    assert not await driver.wait_for_call(
        one, target, method="POST", shape="/api/ping", since=mark, deadline_s=0.5
    )


async def test_a_recorded_frame_that_is_gone_fails_rather_than_guessing_another(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await signed_in_on_the_framed_page(rig, driver, one)
    gone = {**in_the_app_frame(rig, "type", "#ct", "GT2")}
    gone["frame_path"] = [{"index": 7, "url": rig.url("/nowhere")}]

    answer = await driver.act(one, target, gone)

    assert (answer.ok, answer.error_kind) == (False, "frame_not_found")


async def test_holds_is_asked_in_the_frame_act_touched(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await signed_in_on_the_framed_page(rig, driver, one)
    typing = {**in_the_app_frame(rig, "type", "#ct", "GT4"), "frame_path": None}
    typed = await driver.act(one, target, typing)
    app = next(f for f in driver._links[cdp_url].pages[target].frames if f.url.endswith("/app"))
    await app.evaluate("document.getElementById('ct').id = 'renamed'")

    held = {**typing, "pin": typed.pin, "expect": {"value": "GT4"}}
    assert await driver.wait_for(one, target, held, 5.0) is True


_CENTRE_IN_APP_FRAME = """(css) => {
  const frame = document.querySelectorAll("iframe")[1];
  const outer = frame.getBoundingClientRect();
  const inner = frame.contentDocument.querySelector(css).getBoundingClientRect();
  return [Math.round(outer.left + frame.clientLeft + inner.left + inner.width / 2),
          Math.round(outer.top + frame.clientTop + inner.top + inner.height / 2)];
}"""


async def test_sight_types_and_saves_in_the_frame_and_settles_by_its_own_call(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await signed_in_on_the_framed_page(rig, driver, one)
    page = await driver._page(one, target)
    ct = await page.evaluate(_CENTRE_IN_APP_FRAME, "#ct")
    save = await page.evaluate(_CENTRE_IN_APP_FRAME, "#save")
    model = FakeVisionDriver(
        ProposedGesture(ActionKind.TYPE, x=ct[0], y=ct[1], value="GT2"),
        ProposedGesture(ActionKind.CLICK, x=save[0], y=save[1]),
        ProposedGesture(ActionKind.HOVER, done=True),
    )
    step, saved = save_step(
        status=201, body=Body(text='{"name": "GT1"}', mime_type="application/json")
    )
    by_id = {
        key: replace(
            one_,
            url=rig.url("/app"),
            system=system_of(rig.url("/")),
            requests=[replace(one_.requests[0], url=rig.url("/api/customer-types"))],
        )
        for key, one_ in saved.items()
    }
    ctx = lane_context(by_id)
    assert ctx.held is not None
    ctx = replace(ctx, held=replace(ctx.held, target_id=target, session=one))

    screen = await driver.screenshot(one, target)
    result = await SightLane(driver, model, None).execute(
        replace(step, system=system_of(rig.url("/"))), {"Customer Type": "GT2"}, ctx
    )

    assert screen.image.startswith(b"\x89PNG") and screen.width > 0 and screen.height > 0
    assert result.verdict == "done", result.reason
    assert dict(result.learned) == {
        "strategy": "role_and_name",
        "query": "button|Save",
        "frame_path": json.dumps([{"index": 1, "url": "/app"}]),
    }
    posted = [c for c in result.calls if c.method == "POST"]
    assert [(c.status, c.own_frame, c.request_body) for c in posted] == [
        (201, True, '{"name":"GT2"}')
    ]


async def test_a_call_sent_and_not_yet_answered_is_already_in_the_log(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    mark = await driver.mark(one, target)
    await driver.evaluate(one, target, "void fetch('/api/ping?hold', {method: 'POST'})")
    assert await asyncio.to_thread(rig.pinged.wait, 10)

    pending = await driver.calls_since(one, target, mark)
    rig.release.set()

    assert [(c.method, c.status) for c in pending] == [("POST", None)]
    assert await driver.wait_for_call(
        one, target, method="POST", shape="/api/ping", since=mark, deadline_s=5.0
    )
    assert [(c.method, c.status) for c in await driver.calls_since(one, target, mark)] == [
        ("POST", 201)
    ]


async def test_a_mark_forgets_the_frame_the_last_step_acted_in(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await signed_in_on_the_framed_page(rig, driver, one)
    assert (await driver.act(one, target, in_the_app_frame(rig, "type", "#ct", "GT2"))).ok
    mark = await driver.mark(one, target)
    app = next(f for f in driver._links[cdp_url].pages[target].frames if f.url.endswith("/app"))

    await app.evaluate(PING)

    assert await driver.wait_for_call(
        one, target, method="POST", shape="/api/ping", since=mark, deadline_s=5.0
    )
    assert [c.own_frame for c in await driver.calls_since(one, target, mark)] == [False]


async def test_a_point_is_confirmed_only_when_the_recorded_control_is_what_it_hit(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await signed_in_on_the_framed_page(rig, driver, one)
    page = await driver._page(one, target)
    await page.wait_for_load_state()
    app = next(f for f in page.frames if f.url.endswith("/app"))
    await app.evaluate(
        "document.getElementById('save').insertAdjacentHTML('beforebegin',"
        ' \'<input id="desc" aria-label="Description">\')'
    )
    recorded = in_the_app_frame(rig, "type", "#ct")

    async def pointed(css: str, action: ActionKind, value: str | None) -> str:
        x, y = await page.evaluate(_CENTRE_IN_APP_FRAME, css)
        hit = await driver.hit_test(one, target, x, y)
        assert hit is not None and isinstance(hit.get("pin"), str)
        await driver.point(one, target, action, x, y, value, hit["frame_path"])
        return str(hit["pin"])

    async def holds(pin: str, expect: dict[str, object]) -> bool:
        return await driver.wait_for(one, target, {**recorded, "pin": pin, "expect": expect}, 0.5)

    wrong_field = await pointed("#desc", ActionKind.TYPE, "GT2")
    assert not await holds(wrong_field, {"value": "GT2"})
    save = await pointed("#save", ActionKind.CLICK, None)
    assert not await holds(save, {"visible": True, "enabled": True})
    await app.evaluate("document.getElementById('ct').value = 'GT1'")
    prefilled = await pointed("#ct", ActionKind.HOVER, None)
    assert not await holds(prefilled, {"value": "GT9"})
    typed = await pointed("#ct", ActionKind.TYPE, "GT9")
    assert await holds(typed, {"value": "GT1GT9", "visible": True, "enabled": True})


async def test_a_field_nobody_recorded_is_found_by_its_label_filled_and_saved(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
) -> None:
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    department = {
        "action": "select",
        "write": False,
        "target": {
            "role": "combobox",
            "name": "Department",
            "landmarks": [{"role": "form", "name": "Customer Type"}],
        },
    }

    found = await driver.resolve(one, target, department)
    outline = await driver.outline(one, target, [])

    assert (found.ok, found.candidates, found.matched_by) == (True, 1, "within_role_name")
    assert outline is not None
    fields = {one["label"]: one["options"] for one in outline["fields"]}
    assert fields["Department"] == ["Finance", "Operations"]
    chosen = await driver.act(one, target, {**department, "value": "Operations"})
    held = {**department, "pin": chosen.pin, "expect": {"value": "Operations"}}
    assert chosen.ok and await driver.wait_for(one, target, held, 5.0)
    holding = (await driver.resolve(one, target, department)).held
    assert holding == "Operations"
    await driver.act(one, target, {"action": "type", "value": "GT9", "target": {"css_path": "#ct"}})
    mark = await driver.mark(one, target)
    await driver.act(one, target, {"action": "click", "target": {"css_path": "#save"}})
    assert await driver.wait_for_call(
        one, target, method="POST", shape="/api/customer-types", since=mark, deadline_s=5.0
    )
    assert rig.saved[-1] == {"name": "GT9", "department": "Operations"}
    (save,) = [c for c in await driver.calls_since(one, target, mark) if c.method == "POST"]
    recorded = Call(
        "POST",
        rig.url("/api/customer-types"),
        201,
        1.0,
        request_body=Body(text='{"name": "GT1"}', mime_type="application/json"),
    )
    assert same_call(save, recorded, Adding(fresh={"department": holding})) == {
        "department": "department"
    }
    assert same_call(save, recorded, Adding(fresh={"department": "Finance"})) is None


async def test_connecting_a_system_keeps_a_token_from_any_path_of_its_own(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
) -> None:
    async with SteelClient("http://steel.invalid", cdp_url) as client:
        said = await client.session_headers(BrowserSessionId("only"), rig.url("/landing"))

    assert said.get("x-csrf-token") == "landing-token"


async def test_connecting_a_system_returns_once_the_token_is_sent(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
) -> None:
    loop = asyncio.get_running_loop()
    async with SteelClient("http://steel.invalid", cdp_url) as client:
        began = loop.time()
        said = await client.session_headers(BrowserSessionId("only"), rig.url("/landing"))
        took = loop.time() - began

    assert said.get("x-csrf-token") == "landing-token"
    assert took < 3


async def test_a_mark_whose_connection_went_away_is_page_gone(
    rig: Rig,  # noqa: F811
    one: SessionRef,  # noqa: F811
    driver: SteelDriver,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = await driver.open_tab(one, rig.url("/public"))
    found = driver._page

    async def then_lost(session: SessionRef, target_id: str) -> Any:
        page = await found(session, target_id)
        driver._links.clear()
        return page

    monkeypatch.setattr(driver, "_page", then_lost)

    with pytest.raises(PageGone):
        await driver.mark(one, target)
