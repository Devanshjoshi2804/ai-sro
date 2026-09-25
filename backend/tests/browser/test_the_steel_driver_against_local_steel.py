"""The page driver against real local Steel: one container, two account
contexts from `SteelPool.open`, the `cdp_url` the pool hands out, and a rig
Steel's Chrome reaches through `host.docker.internal`.

Every case here failed live in the S5 review. Skipped when Steel is not
running. Run each test alone: they share the container's one browser.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator

import pytest

from sro.application.ports.page import PageGone, SessionRef
from sro.config import get_settings
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.driver import SteelDriver
from sro.infrastructure.steel.pool import SteelPool
from tests.browser.steel_rig import Rig, driver  # noqa: F401
from tests.browser.test_the_steel_pool_against_local_steel import (  # noqa: F401
    STEEL_URL,
    client,
)

pytestmark = pytest.mark.browser

Accounts = tuple[SteelPool, str, SessionRef, SessionRef]


@pytest.fixture
def steel_rig() -> Iterator[Rig]:
    made = Rig(for_steel=True)
    try:
        yield made
    finally:
        made.close()


@pytest.fixture
async def accounts(client: SteelClient) -> AsyncIterator[Accounts]:  # noqa: F811
    pool = SteelPool({STEEL_URL: client}, per_container=2)
    url, first = await pool.open("greyorange", {})
    _, second = await pool.open("greyorange", {STEEL_URL: 1})
    cdp = await pool.cdp_url(url)
    try:
        yield pool, url, SessionRef(first, cdp), SessionRef(second, cdp)
    finally:
        for context_id in (first, second):
            if await pool.alive(url, context_id):
                await pool.close(url, context_id)


async def test_a_tab_closed_right_after_it_opens_leaves_steel_and_its_neighbour_up(
    client: SteelClient,  # noqa: F811
    accounts: Accounts,
    steel_rig: Rig,
    driver: SteelDriver,  # noqa: F811
) -> None:
    pool, url, a, b = accounts

    for _ in range(5):
        target = await driver.open_tab(a, steel_rig.url("/public"))
        await driver.close_tab(a, target)

    assert await client.health()
    assert await pool.alive(url, a.context_id)
    assert await pool.alive(url, b.context_id), "the container's Chrome went down"
    sibling = await driver.open_tab(b, steel_rig.url("/public"))
    assert (await driver.url_of(b, sibling)).endswith("/public")


async def test_two_accounts_in_one_container_never_meet(
    accounts: Accounts,
    steel_rig: Rig,
    driver: SteelDriver,  # noqa: F811
) -> None:
    _, _, a, b = accounts
    heard: list[str] = []
    await driver.on(a, "request", lambda request: heard.append(request.url))

    signed = await driver.open_tab(a, steel_rig.url("/"))
    await steel_rig.sign_in_in(driver, a, signed)
    heard_from_a = len(heard)
    assert heard_from_a > 0

    other = await driver.open_tab(b, steel_rig.url("/app"))
    assert "/idp/authorize" in await driver.url_of(b, other)
    assert len(heard) == heard_from_a, "account a heard account b's traffic"

    names_a = {c["name"] for c in json.loads(await driver.storage_state(a))["cookies"]}
    names_b = {c["name"] for c in json.loads(await driver.storage_state(b))["cookies"]}
    assert "sid" in names_a
    assert "sid" not in names_b

    with pytest.raises(PageGone):
        await driver.url_of(b, signed)

    both = [a, b] * 3
    targets = await asyncio.gather(
        *(driver.open_tab(who, steel_rig.url(f"/public?{n}")) for n, who in enumerate(both))
    )
    for n, (who, target) in enumerate(zip(both, targets, strict=True)):
        assert (await driver.url_of(who, target)).endswith(f"/public?{n}")
        with pytest.raises(PageGone):
            await driver.url_of(b if who is a else a, target)


async def test_saved_state_moves_to_another_account_across_a_restart(
    accounts: Accounts,
    steel_rig: Rig,
    driver: SteelDriver,  # noqa: F811
) -> None:
    _, _, a, b = accounts
    signed = await driver.open_tab(a, steel_rig.url("/"))
    await steel_rig.sign_in_in(driver, a, signed)
    await driver.evaluate(a, signed, "localStorage.setItem('kept', 'yes')")
    state = await driver.storage_state(a)

    restorer = SteelDriver(get_settings().page_code_path)
    await restorer.restore_state(b, state)
    await restorer.aclose()
    landed = await driver.open_tab(b, steel_rig.url("/app"))

    assert (await driver.url_of(b, landed)).endswith("/app")
    assert await driver.evaluate(b, landed, "localStorage.getItem('kept')") == "yes"


async def test_a_restarted_worker_finds_its_tab_with_the_page_code(
    accounts: Accounts,
    steel_rig: Rig,
) -> None:
    _, _, a, _ = accounts
    first = SteelDriver(get_settings().page_code_path)
    target = await first.open_tab(a, steel_rig.url("/public"))
    await first.aclose()

    again = SteelDriver(get_settings().page_code_path)
    try:
        await again.goto(a, target, steel_rig.url("/public?next"))
        assert await again.evaluate(a, target, "typeof globalThis.sroPage") == "object"
    finally:
        await again.aclose()


async def test_a_closed_context_is_page_gone_even_when_none_is_left(
    accounts: Accounts,
    steel_rig: Rig,
    driver: SteelDriver,  # noqa: F811
) -> None:
    pool, url, a, b = accounts
    target = await driver.open_tab(a, steel_rig.url("/public"))

    await pool.close(url, a.context_id)
    with pytest.raises(PageGone):
        await driver.url_of(a, target)

    await pool.close(url, b.context_id)
    with pytest.raises(PageGone):
        await driver.open_tab(a, steel_rig.url("/public"))
    with pytest.raises(PageGone):
        await driver.restore_state(a, '{"cookies": []}')
    with pytest.raises(PageGone):
        await driver.storage_state(a)
    with pytest.raises(PageGone):
        await driver.storage_state(SessionRef("some-other-account", a.cdp_url))


async def test_steel_s_http_cdp_url_connects_and_a_stale_one_is_page_gone(
    accounts: Accounts,
    steel_rig: Rig,
    driver: SteelDriver,  # noqa: F811
) -> None:
    _, _, a, _ = accounts
    by_name = SessionRef(a.context_id, "http://localhost:9223")
    target = await driver.open_tab(by_name, steel_rig.url("/public"))
    assert (await driver.url_of(by_name, target)).endswith("/public")

    stale = SessionRef(a.context_id, a.cdp_url.rsplit("/", 1)[0] + "/not-this-browser")
    with pytest.raises(PageGone):
        await driver.url_of(stale, target)
