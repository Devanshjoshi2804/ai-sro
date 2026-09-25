"""One Steel container, two account contexts, against real local Steel.

The pool's whole reason to hold browser contexts rather than Steel sessions is
that a self-hosted Steel container's `/v1/sessions` release kills every
session sharing its one Chrome (measured by C0, `scripts/steel_sessions.py`).
Closing one account's context must not touch a sibling's -- that claim only
means anything proven against a real Steel container, not a fake.

Skipped when Steel is not running.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Iterable

import httpx
import pytest

from sro.application.ports.browser import BrowserUnavailable
from sro.domain.shared.identifiers import BrowserSessionId
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.pool import SteelPool

pytestmark = pytest.mark.browser

STEEL_URL = "http://localhost:3010"
CDP_URL = "http://localhost:9223"


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


async def status_of(session_id: str) -> str:
    """Steel's own list, not `GET /v1/sessions/<id>`: self-hosted Steel
    answers `released` there for the session its list calls live."""
    async with httpx.AsyncClient() as http:
        listed = (await http.get(f"{STEEL_URL}/v1/sessions")).json()["sessions"]
    return next((str(one["status"]) for one in listed if one["id"] == session_id), "missing")


@contextlib.asynccontextmanager
async def tracking_contexts() -> AsyncIterator[list[str]]:
    """Every context any `SteelClient` opens while this is active, patched at
    the class level so a test's own second client -- standing in for a second
    process, as `test_a_restarted_client_opens_beside_the_first...` does --
    is tracked too. A sibling worktree's `SteelClient` is a different test
    process with this patch never applied, so its contexts are never in the
    list and never disposed."""
    created: list[str] = []
    original = SteelClient.open_context

    async def tracked(self: SteelClient) -> tuple[BrowserSessionId, str]:
        session_id, context_id = await original(self)
        created.append(context_id)
        return session_id, context_id

    SteelClient.open_context = tracked  # type: ignore[method-assign]
    try:
        yield created
    finally:
        SteelClient.open_context = original  # type: ignore[method-assign]


async def release_every_live_session(steel: SteelClient, created: Iterable[str]) -> None:
    """Disposes only the contexts this test created -- never every context
    Chrome lists, which would end a sibling test's session too (I2)."""
    with contextlib.suppress(BrowserUnavailable):
        for context_id in created:
            await steel.dispose(context_id)
    for session_id in await steel.live_sessions():
        if await status_of(str(session_id)) == "live":
            await steel.close(session_id)


async def test_closing_one_accounts_context_leaves_a_sibling_context_alive(
    client: SteelClient,
) -> None:
    pool = SteelPool({STEEL_URL: client}, per_container=2)

    url, session, first = await pool.open("greyorange", {})
    _, same, second = await pool.open("greyorange", {STEEL_URL: 1})

    assert first != second
    assert session == same
    assert {first, second} <= await pool.contexts(url)

    await pool.close(url, second)

    # `alive` asks Chrome itself (`Target.getBrowserContexts` over the
    # container's one CDP endpoint), not Steel's own session bookkeeping --
    # this is "usable", not merely "not yet reaped": a context that failed to
    # dispose cleanly, or was disposed along with its session, drops out of
    # that list the same call would use to attach a tab to it.
    listed = await pool.contexts(url)
    assert first in listed
    assert second not in listed
    assert await status_of(session) == "live"


async def test_closing_an_unrelated_stale_session_id_never_touches_a_live_context(
    client: SteelClient,
) -> None:
    """A self-hosted Steel's `/v1/sessions/<id>/release` frees the container's
    one browser for ANY id it is sent -- not only an id that owns it (S7
    rereview, R2-1's live probe: releasing a different, already-released id
    answered 200 and took the live session's browser down with it). `close`
    must never reach that endpoint while Chrome still lists a context, no
    matter what id it was asked to release."""
    pool = SteelPool({STEEL_URL: client}, per_container=2)
    url, session, first = await pool.open("greyorange", {})

    await client.close(BrowserSessionId("not-the-session-holding-this-context"))

    assert first in await pool.contexts(url)
    assert await status_of(session) == "live"


async def test_navigating_reading_cookies_or_clearing_one_account_never_touches_the_other(
    client: SteelClient,
) -> None:
    pool = SteelPool({STEEL_URL: client}, per_container=2)

    _, _, first = await pool.open("greyorange", {})
    _, _, second = await pool.open("greyorange", {STEEL_URL: 1})

    await client.navigate(BrowserSessionId(first), "data:text/html,first")
    await client.navigate(BrowserSessionId(second), "data:text/html,second")

    await client.restore(
        BrowserSessionId(first),
        [{"name": "acct", "value": "first", "domain": "example.com", "path": "/"}],
    )

    first_cookies = await client.session_cookies(BrowserSessionId(first))
    second_cookies = await client.session_cookies(BrowserSessionId(second))
    assert any(c["value"] == "first" for c in first_cookies)
    assert not any(c["value"] == "first" for c in second_cookies)

    await client.forget_everything(BrowserSessionId(first))
    assert not await client.session_cookies(BrowserSessionId(first))


async def test_a_restarted_client_opens_beside_the_first_and_closes_only_what_it_names(
    client: SteelClient,
) -> None:
    """The API and the worker are two processes, and either restarts. The
    container's contexts and its one Steel session belong to neither."""
    before = SteelPool({STEEL_URL: client}, per_container=3)
    url, session, first = await before.open("greyorange", {})
    _, _, sibling = await before.open("greyorange", {STEEL_URL: 1})

    async with SteelClient(STEEL_URL, CDP_URL, capacity=3) as restarted:
        after = SteelPool({STEEL_URL: restarted}, per_container=3)
        _, adopted, third = await after.open("greyorange", {STEEL_URL: 2})
        await after.close(url, first)
        await after.close(url, first)

        listed = await after.contexts(url)
        assert adopted == session
        assert first not in listed
        assert {sibling, third} <= listed
        assert await status_of(session) == "live"


async def test_a_close_that_timed_out_leaves_no_slot_taken_in_the_client(
    client: SteelClient,
) -> None:
    pool = SteelPool({STEEL_URL: client}, per_container=1)
    url, _, first = await pool.open("greyorange", {})
    with contextlib.suppress(TimeoutError):
        async with asyncio.timeout(0):
            await pool.close(url, first)

    _, _, second = await pool.open("greyorange", {})

    assert second != first
    assert second in await pool.contexts(url)


async def test_the_teardown_never_disposes_a_sibling_worktrees_context() -> None:
    """A sibling worktree is another process with its own `SteelClient`, so
    nothing here patches it -- `sibling`'s context is opened before
    `tracking_contexts()` is even entered."""
    made = SteelClient(STEEL_URL, CDP_URL, capacity=2)
    if not await made.health():
        pytest.skip("Steel is not running; `make up` first")
    async with made:
        sibling = SteelClient(STEEL_URL, CDP_URL, capacity=2)
        async with sibling:
            _, theirs = await sibling.open_context()
            try:
                async with tracking_contexts() as created:
                    _, mine = await made.open_context()
                    await release_every_live_session(made, created)

                    listed = await made.contexts()
                    assert mine not in listed
                    assert theirs in listed
            finally:
                await sibling.dispose(theirs)
