"""`SteelDriver.opened_by` on one Steel connection that serves several
contexts at once: each waiter gets its own popup whatever order they arrive
in, and a closed popup leaves nothing behind on the connection.

The pages are stand-ins with only what `_arrived` reads from a Playwright
page, and each arrives through `_arrived`, the path Playwright's `page` event
takes."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from sro.application.ports.page import SessionRef
from sro.infrastructure.steel.driver import SteelDriver, _Link

CDP = "http://steel.test:9222"
MAIN_A, MAIN_B = "main-a", "main-b"


class _Cdp:
    def __init__(self, info: dict[str, str]) -> None:
        self._info = info

    async def send(self, method: str) -> dict[str, Any]:
        return {"targetInfo": self._info}

    async def detach(self) -> None:
        return None


class _Page:
    def __init__(self, target: str, context: str, opener: str) -> None:
        self._cdp = _Cdp({"targetId": target, "browserContextId": context, "openerId": opener})
        self.context = self
        self.main_frame = object()
        self.frames: list[object] = []
        self.on_close: list[Callable[[object], None]] = []

    async def new_cdp_session(self, page: object) -> _Cdp:
        return self._cdp

    def once(self, event: str, handler: Callable[[object], None]) -> None:
        self.on_close.append(handler)

    def on(self, event: str, handler: object) -> None:
        return None

    async def add_init_script(self, script: str) -> None:
        return None

    def close(self) -> None:
        for handler in self.on_close:
            handler(self)


def _driver(tmp_path: Path) -> tuple[SteelDriver, _Link]:
    code = tmp_path / "page.js"
    code.write_text("", encoding="utf-8")
    driver = SteelDriver(str(code))
    link = _Link(CDP, "steel.test:9222", cast(Any, None), cast(Any, None))

    async def context(session: SessionRef) -> _Link:
        return link

    driver._context = context  # type: ignore[method-assign]
    return driver, link


async def _arrive(driver: SteelDriver, link: _Link, page: _Page) -> None:
    await driver._arrived(link, cast(Any, page), whole=True)


@pytest.mark.parametrize("gap", range(6))
async def test_two_contexts_waiting_on_one_connection_each_get_their_own_popup(
    tmp_path: Path, gap: int
) -> None:
    driver, link = _driver(tmp_path)
    a = asyncio.create_task(driver.opened_by(SessionRef("ctx-a", CDP), MAIN_A, 2))
    b = asyncio.create_task(driver.opened_by(SessionRef("ctx-b", CDP), MAIN_B, 2))
    await asyncio.sleep(0)

    await _arrive(driver, link, _Page("pop-b", "ctx-b", MAIN_B))
    for _ in range(gap):
        await asyncio.sleep(0)
    await _arrive(driver, link, _Page("pop-a", "ctx-a", MAIN_A))

    assert await asyncio.wait_for(asyncio.gather(a, b), 1) == ["pop-a", "pop-b"]


async def test_a_closed_popup_leaves_nothing_on_the_connection(tmp_path: Path) -> None:
    driver, link = _driver(tmp_path)
    popup = _Page("pop-a", "ctx-a", MAIN_A)
    await _arrive(driver, link, popup)
    assert await driver.opened_by(SessionRef("ctx-a", CDP), MAIN_A, 1) == "pop-a"

    popup.close()

    assert "pop-a" not in link.handed
    assert "pop-a" not in link.pages
