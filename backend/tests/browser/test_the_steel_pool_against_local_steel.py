"""One Steel container, two account contexts, against real local Steel.

The pool's whole reason to hold browser contexts rather than Steel sessions is
that a self-hosted Steel container's `/v1/sessions` release kills every
session sharing its one Chrome (measured by C0, `scripts/steel_sessions.py`).
Closing one account's context must not touch a sibling's -- that claim only
means anything proven against a real Steel container, not a fake.

Skipped when Steel is not running.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

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
    async with made:
        try:
            yield made
        finally:
            if made._session_id is not None:
                await made.close(made._session_id)


async def test_closing_one_accounts_context_leaves_a_sibling_context_alive(
    client: SteelClient,
) -> None:
    pool = SteelPool({STEEL_URL: client}, per_container=2)

    url, first = await pool.open({})
    _, second = await pool.open({STEEL_URL: 1})

    assert first != second
    assert await pool.alive(url, first)
    assert await pool.alive(url, second)

    await pool.close(url, second)

    # `alive` asks Chrome itself (`Target.getBrowserContexts` over the
    # container's one CDP endpoint), not Steel's own session bookkeeping --
    # this is "usable", not merely "not yet reaped": a context that failed to
    # dispose cleanly, or was disposed along with its session, drops out of
    # that list the same call would use to attach a tab to it.
    assert await pool.alive(url, first)
    assert not await pool.alive(url, second)
