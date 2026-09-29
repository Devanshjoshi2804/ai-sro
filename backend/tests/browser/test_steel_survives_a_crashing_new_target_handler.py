"""Steel's Node process must survive a tab closing before Steel's own
new-target handler finishes its awaited CDP calls (see
`.superpowers/sdd/2026-09-24-execution-runtime/task-S5-rereview-1.md`,
"Second crash path"). A self-closing sign-in popup can trigger this the same
way our own `close_tab` can, and either kills every account sharing the
container's one Chrome.

The container is started with `NODE_OPTIONS=--unhandled-rejections=warn`
(`infra/docker-compose.yml`) so the unhandled rejection Steel never catches is
logged instead of exiting Node. This test proves the container -- and a
sibling account's context -- survives 20 rapid open/close cycles, including
one popup that closes itself, in the account under test.

Run alone:
`uv run pytest tests/browser/test_steel_survives_a_crashing_new_target_handler.py \
    -q -o faulthandler_timeout=120`

Skipped when Steel is not running.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from playwright.async_api import async_playwright

from sro.config import get_settings
from sro.domain.shared.identifiers import BrowserSessionId
from sro.infrastructure.steel.client import SteelClient
from tests.browser.test_the_steel_pool_against_local_steel import (
    release_every_live_session,
    tracking_contexts,
)

pytestmark = pytest.mark.browser

STEEL_URL = get_settings().steel_base_url
CDP_URL = get_settings().steel_cdp_url

_ROUNDS = 20
_POPUP_ROUND = 10

# A close right on `about:blank`'s heels beats Steel's new-target handler to
# the target most of the time, so instrumenting it never even starts. A real
# navigation gives the handler's unguarded awaits (`setExtraHTTPHeaders`,
# `installMouseHelper`, ...) time to be mid-flight when the tab goes away --
# reproduced live: without `NODE_OPTIONS=--unhandled-rejections=warn`, this
# exact loop crashes Steel's Node with an uncaught `TargetCloseError` out of
# `installMouseHelper` within a handful of rounds.
_LIVE_URL = "https://example.com"
_CLOSE_DELAY_S = 0.03

_SELF_CLOSING_POPUP = (
    "data:text/html,"
    "<script>"
    "var w=window.open('about:blank');"
    "w.document.write('<script>window.close()<\\/script>');"
    "</script>"
)


@pytest.fixture
async def client() -> AsyncIterator[SteelClient]:
    made = SteelClient(STEEL_URL, CDP_URL, capacity=2)
    try:
        if not await made.health():
            pytest.skip("Steel is not running; `make up` first")
    except Exception as exc:
        pytest.skip(f"Steel is not reachable: {exc}")
    async with made, tracking_contexts() as created:
        try:
            yield made
        finally:
            await release_every_live_session(made, created)


async def test_a_container_survives_20_tabs_closing_before_steels_handler_finishes(
    client: SteelClient,
) -> None:
    session, victim = await client.open_context()
    _, sibling = await client.open_context()

    async with async_playwright() as driver:
        browser = await driver.chromium.connect_over_cdp(await client.debugger_url(session))
        try:
            raw = await browser.new_browser_cdp_session()
            for round_ in range(_ROUNDS):
                if round_ == _POPUP_ROUND:
                    made = await raw.send(
                        "Target.createTarget",
                        {"url": _SELF_CLOSING_POPUP, "browserContextId": victim},
                    )
                    # The popup closes itself; nothing further to send.
                    _ = made
                else:
                    made = await raw.send(
                        "Target.createTarget",
                        {"url": _LIVE_URL, "browserContextId": victim},
                    )
                    await asyncio.sleep(_CLOSE_DELAY_S)
                    await raw.send("Target.closeTarget", {"targetId": made["targetId"]})
            await raw.detach()
        finally:
            await browser.close()

    assert await client.health()
    assert sibling in await client.contexts()

    await client.navigate(BrowserSessionId(sibling), "data:text/html,sibling still usable")
