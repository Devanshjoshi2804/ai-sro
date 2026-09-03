"""The offer that arrives because somebody landed on a page, in a real Chrome.

A nudge is the one thing this product says without being asked, and everything
that could make it a nuisance needs a browser to prove. That a pill appears in
somebody else's application at all, over their own markup and their own
z-index. That it appears on the page a task starts on and not merely the host.
That leaving takes it away. None of that can be shown against a fake document:
they are questions about injection into a real page and about what the platform
does with a tab.

`nudge.test.mjs` holds the other half -- when it fires, and the three ways it
ends -- because those are arithmetic over a clock and deserve a test that runs
in milliseconds rather than one that drives a browser.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

pytestmark = pytest.mark.browser

PILL = "#sro-nudge"


def _service_worker(context: Any) -> Any:
    return (
        context.service_workers[0]
        if context.service_workers
        else context.wait_for_event("serviceworker")
    )


def _extension_page(context: Any, worker: Any) -> Any:
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    return page


def _sign_in(context: Any, worker: Any, api_url: str) -> dict[str, Any]:
    page = _extension_page(context, worker)
    status: dict[str, Any] = page.evaluate(
        """async (apiUrl) => await chrome.runtime.sendMessage(
             {kind: "sign-in", apiUrl, consoleUrl: "", token: "test.token.here",
              label: "browser-test"})""",
        api_url,
    )
    page.close()
    return status


def _watch(context: Any, worker: Any, page: Any) -> dict[str, Any]:
    """Say, the way an operator says it in the panel, that the work is in this tab.

    Nothing is offered about a tab nobody pointed at, which is as much the rule
    under test as anything asserted below.
    """
    page.bring_to_front()
    tab_id = worker.evaluate(
        "async () => (await chrome.tabs.query({active: true, lastFocusedWindow: true}))[0]?.id"
    )
    assert tab_id is not None, "no active tab to watch"
    asking = _extension_page(context, worker)
    answer: dict[str, Any] = asking.evaluate(
        """async (tabId) => await chrome.runtime.sendMessage({kind: "watch-tab", tabId})""",
        tab_id,
    )
    asking.close()
    assert "error" not in answer, f"could not watch that tab: {answer}"
    return answer


def _held(context: Any, worker: Any) -> list[dict[str, Any]]:
    """The prompts this browser is holding, off its own status."""
    page = _extension_page(context, worker)
    status: dict[str, Any] = page.evaluate(
        """async () => await chrome.runtime.sendMessage({kind: "status"})"""
    )
    page.close()
    nudges: list[dict[str, Any]] = status.get("nudges") or []
    return nudges


def _wait_for_pill(page: Any, timeout: float = 10.0) -> bool:
    """The pill is put up by the worker after the navigation it heard about, so
    a test that looked once would be racing the platform rather than the code."""
    until = time.time() + timeout
    while time.time() < until:
        if page.locator(PILL).count():
            return True
        time.sleep(0.2)
    return False


@pytest.fixture
def signed_in(browser: Any, stub: Any) -> Any:
    api_url, _ = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start: {status}"
    return worker


def test_landing_where_a_task_starts_puts_a_pill_on_the_page(
    browser: Any, stub: Any, signed_in: Any
) -> None:
    """The whole point: the operator is on the page, about to do the thing, and
    that is the moment worth speaking.

    The pill and not only the panel, because the panel may be closed -- which is
    exactly when this matters.
    """
    api_url, _ = stub
    worker = signed_in
    page = browser.new_page()
    page.goto(api_url)
    _watch(browser, worker, page)
    # The watch lands after the navigation that opened the tab, so the offer is
    # made on the next one -- which is the same page, arrived at deliberately.
    page.goto(api_url)

    assert _wait_for_pill(page), "nothing was offered on the page the task starts on"

    held = _held(browser, worker)
    assert len(held) == 1, f"expected one prompt, got {held}"
    assert held[0]["state"] == "open"
    assert held[0]["title"] == "Adjust an LPN quantity"


def test_a_different_page_on_the_same_host_says_nothing(
    browser: Any, stub: Any, signed_in: Any
) -> None:
    """A task starts on a page, not on an application. Offering to do it on
    every screen of the system is the nagging this design exists to avoid."""
    api_url, _ = stub
    worker = signed_in
    page = browser.new_page()
    page.goto(f"{api_url}/elsewhere")
    _watch(browser, worker, page)
    page.goto(f"{api_url}/elsewhere")

    time.sleep(2.0)
    assert page.locator(PILL).count() == 0, "it offered on a page the task does not start on"
    assert _held(browser, worker) == []


def test_walking_away_takes_the_pill_with_it(browser: Any, stub: Any, signed_in: Any) -> None:
    """One of the three ways a nudge ends. A prompt still up on a page it is not
    about is one somebody learns to ignore, and then ignores the useful one."""
    api_url, _ = stub
    worker = signed_in
    page = browser.new_page()
    page.goto(api_url)
    _watch(browser, worker, page)
    page.goto(api_url)
    assert _wait_for_pill(page), "nothing was offered to walk away from"

    page.goto(f"{api_url}/elsewhere")

    until = time.time() + 10.0
    while time.time() < until and page.locator(PILL).count():
        time.sleep(0.2)
    assert page.locator(PILL).count() == 0, "the prompt outlived the page it was about"
    assert [n["state"] for n in _held(browser, worker)] == ["expired"]


def test_a_tab_nobody_pointed_at_is_never_offered_anything(
    browser: Any, stub: Any, signed_in: Any
) -> None:
    """Watching is what makes a tab evidence, and it is what makes it worth
    speaking about. A browser that offered on any tab would be one that had read
    a page nobody agreed to."""
    api_url, _ = stub
    page = browser.new_page()
    page.goto(api_url)

    time.sleep(2.0)
    assert page.locator(PILL).count() == 0, "it offered about a tab nobody is watching"
