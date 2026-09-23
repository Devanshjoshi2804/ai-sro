"""The stored-credential sign-in loop, against a page that does exactly what it is told.

The browser tests prove the loop against a real Chromium; these pin the rules
that a real browser only hits by timing. A probe that meets a page in the middle
of a navigation is retried, deterministically, not just when a race happens to
go that way. A password never reaches a log line or a failure message, even
though Playwright writes the value it was filling into its own error text. And
credentials are typed once: a form that comes back empty after they were
submitted refused them, and typing them again is how an account gets locked.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pytest
from playwright.async_api import Error as PlaywrightError

from sro.application.ports.sign_in import SignInFailed
from sro.infrastructure.steel import sign_in as driver

SECRET = "hunter2-not-real"  # noqa: S105 -- a fake page's field
HOST = "wms.test"
SYSTEM = f"https://{HOST}/"
PROVIDER = "https://idp.test/login"


@dataclass
class _Element:
    visible: bool = True
    value: str = ""
    text: str = ""
    on_fill: Any = None
    on_click: Any = None

    async def is_visible(self) -> bool:
        return self.visible

    async def input_value(self, **_: Any) -> str:
        return self.value

    async def fill(self, value: str, **_: Any) -> None:
        if self.on_fill is not None:
            self.on_fill(value)
        self.value = value

    async def click(self, **_: Any) -> None:
        if self.on_click is not None:
            self.on_click()

    async def inner_text(self) -> str:
        return self.text

    async def get_attribute(self, _: str) -> str | None:
        return None


@dataclass
class _Keyboard:
    pressed: list[str] = field(default_factory=list)

    async def press(self, key: str, **_: Any) -> None:
        self.pressed.append(key)


@dataclass
class _Page:
    url: str = PROVIDER
    elements: dict[str, list[_Element]] = field(default_factory=dict)
    fail_query_once: bool = False
    keyboard: _Keyboard = field(default_factory=_Keyboard)
    text: str = ""

    async def goto(self, url: str, **_: Any) -> None:
        return

    async def wait_for_load_state(self, *_: Any, **__: Any) -> None:
        return

    def is_closed(self) -> bool:
        return False

    def on(self, *_: Any) -> None:
        return

    @property
    def main_frame(self) -> object:
        return self

    async def query_selector(self, selector: str) -> _Element | None:
        if self.fail_query_once:
            self.fail_query_once = False
            raise PlaywrightError(
                "Page.query_selector: Execution context was destroyed, "
                "most likely because of a navigation"
            )
        found = self.elements.get(selector, [])
        return found[0] if found else None

    async def query_selector_all(self, selector: str) -> list[_Element]:
        return list(self.elements.get(selector, []))

    async def inner_text(self, *_: Any, **__: Any) -> str:
        return self.text


@pytest.fixture(autouse=True)
def _quick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(driver, "_PROBE_S", 0.001)


async def _drive(page: _Page, timeout_s: float = 5.0) -> Any:
    return await driver._drive(
        page,
        url=SYSTEM,
        username="operator",
        password=SECRET,
        choose=(),
        timeout_s=timeout_s,
    )


async def test_a_probe_that_meets_a_navigation_is_retried_not_raised() -> None:
    page = _Page(url=SYSTEM, fail_query_once=True)

    result = await _drive(page)

    assert result.landed_at == SYSTEM
    assert not page.fail_query_once


async def test_a_password_in_playwrights_call_log_never_reaches_a_log_or_a_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`fill` racing a navigation is exactly what the retry exists for, and
    Playwright appends a call log naming the value it was filling."""

    def racing(value: str) -> None:
        raise PlaywrightError(
            "ElementHandle.fill: Execution context was destroyed\n"
            f'Call log:\n  - fill("{value}")\n  - waiting for element'
        )

    page = _Page(elements={driver._PASSWORD: [_Element(on_fill=racing)]})
    caplog.set_level(logging.DEBUG)

    with pytest.raises(SignInFailed) as failed:
        await _drive(page, timeout_s=0.3)

    assert SECRET not in str(failed.value)
    assert SECRET not in caplog.text
    assert "Execution context was destroyed" in str(failed.value)
    assert all(record.exc_info is None for record in caplog.records)


async def test_a_page_that_does_not_move_is_a_dead_end_not_a_hand_over() -> None:
    page = _Page(text="Your account has been disabled. Contact support.")

    with pytest.raises(SignInFailed) as failed:
        await _drive(page, timeout_s=30.0)

    assert "account has been disabled" in str(failed.value)


async def test_credentials_the_form_refused_are_never_typed_again() -> None:
    typed: list[str] = []
    page = _Page(text="Invalid username or password.")
    password = _Element(on_fill=typed.append)

    def refused() -> None:
        password.value = ""

    page.elements[driver._PASSWORD] = [password]
    page.elements[driver._SUBMIT] = [_Element(on_click=refused)]

    with pytest.raises(SignInFailed, match="refused") as failed:
        await _drive(page)

    assert typed == [SECRET]
    assert "Invalid username or password" in str(failed.value)
    assert SECRET not in str(failed.value)


async def test_an_error_that_escapes_the_loop_carries_no_password() -> None:
    """Whatever ends the attempt is re-raised as the driver's own failure, with
    only the first line of Playwright's message and no chained original."""

    class _Closing(_Page):
        def is_closed(self) -> bool:
            return True

    def racing(value: str) -> None:
        raise PlaywrightError(f'ElementHandle.fill: Target closed\nCall log:\n  - fill("{value}")')

    page = _Closing(elements={driver._PASSWORD: [_Element(on_fill=racing)]})

    with pytest.raises(SignInFailed) as failed:
        await _drive(page)

    assert SECRET not in str(failed.value)
    assert "Target closed" in str(failed.value)
    assert failed.value.__cause__ is None
    assert failed.value.__suppress_context__
