import asyncio
from typing import Any

import pytest
from playwright.async_api import Error as PlaywrightError

from sro.application.ports.page import SessionRef
from sro.infrastructure.steel.driver import SteelDriver, _Calls, _Tab

_DESTROYED = "Frame.evaluate: Execution context was destroyed, most likely because of a navigation"


class _Frame:
    def __init__(self, tab: _Tab, error: str, navigates: bool) -> None:
        self._tab, self._error, self._navigates = tab, error, navigates

    async def evaluate(self, *_: Any) -> Any:
        if self._navigates:
            self._tab.settled.clear()
            asyncio.get_running_loop().call_later(0.01, self._arrive)
        raise PlaywrightError(self._error)

    def _arrive(self) -> None:
        self._tab.loads += 1
        self._tab.settled.set()


class _Page:
    def is_closed(self) -> bool:
        return False


class _Driver(SteelDriver):
    def __init__(self, error: str, *, navigates: bool) -> None:
        self._page_obj: Any = _Page()
        self._tab = _Tab(None)
        self._tab.settled.set()
        self._frame_obj = _Frame(self._tab, error, navigates)
        self._tabs = {self._page_obj: self._tab}  # type: ignore[dict-item]
        self._the_calls = _Calls(0)

    async def _page(self, session: SessionRef, target_id: str) -> Any:
        return self._page_obj

    async def _frame(self, page: Any, payload: Any) -> Any:
        return self._frame_obj, ""

    async def _target_alive(self, session: SessionRef, target_id: str) -> bool:
        return True

    def _log(self, page: Any) -> _Calls:
        return self._the_calls


def _driver(error: str, *, navigates: bool) -> SteelDriver:
    return _Driver(error, navigates=navigates)


_SESSION = SessionRef("s", "c")


async def test_a_click_that_navigates_is_a_completed_action() -> None:
    answer = await _driver(_DESTROYED, navigates=True).act(_SESSION, "t", {})
    assert answer.ok


async def test_a_destroyed_context_with_no_navigation_still_raises() -> None:
    with pytest.raises(PlaywrightError):
        await _driver(_DESTROYED, navigates=False).act(_SESSION, "t", {})


async def test_another_evaluate_error_during_a_navigation_still_raises() -> None:
    with pytest.raises(PlaywrightError):
        await _driver("Frame.evaluate: boom", navigates=True).act(_SESSION, "t", {})
