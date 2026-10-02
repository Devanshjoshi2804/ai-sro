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
        self._the_tab = _Tab(None)
        self._the_tab.settled.set()
        self._frame_obj: Any = _Frame(self._the_tab, error, navigates)
        self._tabs = {self._page_obj: self._the_tab}  # type: ignore[dict-item]
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


class _Settled(_Frame):
    """A navigation that finished before the error surfaced: the tab is settled, its loads moved."""

    async def evaluate(self, *_: Any) -> Any:
        self._tab.loads += 1
        raise PlaywrightError(self._error)


async def test_a_navigation_that_finished_before_the_error_surfaced_is_a_completed_action() -> None:
    driver = _driver(_DESTROYED, navigates=False)
    driver._frame_obj = _Settled(driver._the_tab, _DESTROYED, False)
    assert (await driver.act(_SESSION, "t", {})).ok


class _DiesWhileLoading(_Frame):
    """The context is gone while the page is still loading; once it has loaded, the act works."""

    def __init__(self, tab: _Tab) -> None:
        super().__init__(tab, _DESTROYED, False)
        self.evaluated = 0

    async def evaluate(self, *_: Any) -> Any:
        self.evaluated += 1
        if not self._tab.settled.is_set():
            raise PlaywrightError(self._error)
        return {"ok": True, "matched_by": "attributes"}


async def test_a_navigation_already_in_flight_is_waited_out_and_the_step_still_runs() -> None:
    driver = _driver(_DESTROYED, navigates=False)
    tab = driver._the_tab
    frame = _DiesWhileLoading(tab)
    driver._frame_obj = frame
    tab.settled.clear()
    asyncio.get_running_loop().call_later(0.01, frame._arrive)

    answer = await driver.act(_SESSION, "t", {})

    assert answer.matched_by == "attributes" and frame.evaluated == 1
