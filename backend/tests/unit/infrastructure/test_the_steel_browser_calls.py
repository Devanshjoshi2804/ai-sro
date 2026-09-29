"""The container's browser-level CDP calls, against a websocket this test
serves. A wedged Chrome accepts the socket and never answers; the call runs
under the account lock, so it must end on its own deadline."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable

import pytest
import websockets

from sro.application.ports.browser import BrowserUnavailable
from sro.infrastructure.steel import client as steel_module
from sro.infrastructure.steel.client import SteelClient

type Answer = Callable[[dict[str, object]], dict[str, object] | None]


async def _chrome(answer: Answer) -> AsyncIterator[SteelClient]:
    async def serve(link: websockets.ServerConnection) -> None:
        async for raw in link:
            said = json.loads(raw)
            reply = answer(said)
            if reply is not None:
                await link.send(json.dumps({"id": said["id"], **reply}))

    async with websockets.serve(serve, "127.0.0.1", 0) as server:
        port = next(iter(server.sockets)).getsockname()[1]
        async with SteelClient(
            "http://steel:3010", f"ws://127.0.0.1:{port}/devtools/browser/x", capacity=5
        ) as made:
            yield made


@pytest.fixture
async def silent() -> AsyncIterator[SteelClient]:
    async for made in _chrome(lambda _: None):
        yield made


async def test_a_browser_that_never_answers_is_unavailable_within_the_deadline(
    silent: SteelClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(steel_module, "K_BROWSER_REPLY_S", 0.2)

    with pytest.raises(BrowserUnavailable):
        await asyncio.wait_for(silent.contexts(), timeout=5)


async def test_disposing_a_context_chrome_no_longer_lists_is_already_done() -> None:
    def answer(said: dict[str, object]) -> dict[str, object]:
        if said["method"] == "Target.getBrowserContexts":
            return {"result": {"browserContextIds": ["ctx-sibling"]}}
        return {"error": {"code": -32000, "message": "Failed to find context with id ctx-gone"}}

    async for made in _chrome(answer):
        await made.dispose("ctx-gone")

        with pytest.raises(BrowserUnavailable):
            await made.dispose("ctx-sibling")
