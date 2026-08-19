"""The session's own screen, as frames, straight off CDP.

Steel's viewer is a single page for the whole deployment: self-hosted, every
session reports the same ``debugUrl`` -- ``/v1/sessions/debug``, with no session
in it -- and that page shows "Session connecting..." forever once the browser it
means is gone. What an operator needs is this session's screen, so this takes it
from the only place that has it: Chrome's own screencast.

``Page.startScreencast`` sends a JPEG whenever the page changes, and it sends
the next one only after the last has been acknowledged. A viewer that forgets to
ack gets about three frames and then a still image, which is the failure this is
most likely to be blamed for.
"""

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
"""Frames held for a viewer that is behind. A live view that buffers is not a
live view: better to drop what the operator has already missed and show them
the screen as it is now."""


async def stream_frames(
    debugger_url: str, *, width: int = 1280, quality: int = 60
) -> AsyncIterator[bytes]:
    """JPEG frames until the caller stops reading or the browser goes away."""
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
                # Acked whether or not the frame was kept: Chrome sends the next
                # one only after this, so a dropped frame must not stop the feed.
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
    """The page the operator is looking at.

    The last page rather than the first: a sign-in that opened a tab leaves the
    original behind, and screencasting that one shows a screen nobody is on.
    """
    pages = [page for context in browser.contexts for page in context.pages]
    if not pages:
        raise RuntimeError("the attached browser has no page open")
    return pages[-1]
