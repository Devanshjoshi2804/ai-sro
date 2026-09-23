from __future__ import annotations

import asyncio
import base64
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Any

from playwright.async_api import Browser, Page, async_playwright

logger = logging.getLogger(__name__)

_QUEUE = 2


async def stream_frames(
    debugger_url: str, *, width: int = 1280, quality: int = 60
) -> AsyncIterator[bytes]:
    frames: asyncio.Queue[bytes] = asyncio.Queue(maxsize=_QUEUE)
    acks: set[asyncio.Task[Any]] = set()

    async with async_playwright() as driver:
        browser = await driver.chromium.connect_over_cdp(debugger_url)
        try:
            page = _visible_page(browser)
            cdp = await page.context.new_cdp_session(page)

            def _on_frame(event: dict[str, Any]) -> None:
                with contextlib.suppress(asyncio.QueueFull):
                    frames.put_nowait(base64.b64decode(event["data"]))
                task = asyncio.create_task(
                    cdp.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
                )
                acks.add(task)
                task.add_done_callback(acks.discard)

            cdp.on("Page.screencastFrame", _on_frame)
            await cdp.send(
                "Page.startScreencast",
                {"format": "jpeg", "quality": quality, "maxWidth": width, "everyNthFrame": 1},
            )
            while True:
                yield await frames.get()
        finally:
            for task in tuple(acks):
                task.cancel()
            with contextlib.suppress(Exception):
                await browser.close()


def _visible_page(browser: Browser) -> Page:
    pages = [page for context in browser.contexts for page in context.pages]
    if not pages:
        raise RuntimeError("the attached browser has no page open")
    return pages[-1]
