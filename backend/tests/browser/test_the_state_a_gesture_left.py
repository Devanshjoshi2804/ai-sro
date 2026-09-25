"""The after-state the recorder reads, in a real Chrome.

`evidence.test.mjs` checks `stateOf` against plain objects. Two leaks E5's first
cut shipped only showed up against real elements: a password field switched to
`type=text` by a "show" toggle, and a password field inside a custom element's
shadow root whose host exposes `.value`. Neither may put what was typed into
any record, and the controls that do have a state -- a checkbox, a select --
must still record it.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from sro.config import get_settings
from sro.infrastructure.steel.capture import _recorder_script

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><html><body>
<input id="pw" name="pw2" type="password">
<button id="show" onclick="document.getElementById('pw').type = 'text'">show</button>
<input id="code" name="code">
<input id="agree" type="checkbox" aria-label="Agree">
<select id="pick" aria-label="Pick"><option value="a">First</option>
<option value="b">Second choice</option></select>
<sro-secret id="host"></sro-secret>
<button id="go">Go</button>
<script>
  customElements.define('sro-secret', class extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' }).innerHTML = '<input type="password">';
    }
    get value() { return this.shadowRoot.querySelector('input').value; }
  });
</script>
</body></html>"""


@pytest.fixture
def page() -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as why:  # pragma: no cover - environment, not logic
            pytest.skip(f"no chromium here: {why}")
        try:
            context = browser.new_context()
            context.add_init_script(
                "window.__sroRecord = (j) => (window.__got = window.__got || []).push(j);"
            )
            context.add_init_script(_recorder_script())
            context.add_init_script(path=get_settings().page_code_path)
            context.route(
                "http://sro.test/**",
                lambda route: route.fulfill(body=PAGE, content_type="text/html"),
            )
            one = context.new_page()
            one.goto("http://sro.test/")
            yield one
        finally:
            browser.close()


def _records(page: Any) -> list[dict[str, Any]]:
    return [json.loads(raw) for raw in page.evaluate("window.__got || []")]


def _go(page: Any) -> dict[str, Any]:
    page.click("#go")
    return _records(page)[-1]


def test_a_password_shown_as_text_never_reaches_a_record(page: Any) -> None:
    page.fill("#pw", "hunter2-toggle")
    page.click("#show")
    page.click("#pw")
    page.press("#pw", "Tab")
    _go(page)

    assert "hunter2-toggle" not in page.evaluate("JSON.stringify(window.__got)")


def test_a_password_inside_a_shadow_root_never_reaches_a_record(page: Any) -> None:
    page.locator("#host input").fill("hunter2-shadow")
    page.click("#host")
    _go(page)

    assert "hunter2-shadow" not in page.evaluate("JSON.stringify(window.__got)")


def test_a_text_field_leaves_no_value_only_whether_it_is_there(page: Any) -> None:
    page.fill("#code", "GT2")
    page.press("#code", "Tab")
    typed = next(one for one in _records(page) if one["kind"] == "type")

    went = _go(page)

    assert typed["value"] == "GT2", "the gesture's own value is not the after-state's"
    assert went["prior"] == {"value": None, "visible": True, "enabled": True}


def test_a_checkbox_and_a_select_record_the_state_they_were_left_in(page: Any) -> None:
    page.click("#agree")
    ticked = _records(page)[-1]
    went = _go(page)
    assert went["prior_of"] == ticked["ref"]
    assert went["prior"]["value"] == "checked"

    page.click("#agree")
    assert _go(page)["prior"]["value"] == "unchecked"

    page.select_option("#pick", "b")
    assert _go(page)["prior"]["value"] == "Second choice"


def _act(page: Any, payload: dict[str, Any]) -> dict[str, Any]:
    acted: dict[str, Any] = page.evaluate("p => globalThis.sroPage.act(p)", payload)
    return acted


def _holds(page: Any, pin: str, expect: dict[str, Any]) -> Any:
    return page.evaluate("p => globalThis.sroPage.holds(p)", {"pin": pin, "expect": expect})


def test_a_checkbox_step_holds_in_the_state_the_recorder_wrote(page: Any) -> None:
    page.click("#agree")
    recorded = _go(page)["prior"]
    page.click("#agree")

    acted = _act(page, {"action": "click", "target": {"css_path": "#agree"}, "write": False})

    assert acted["ok"] and acted["state"] == recorded
    assert _holds(page, acted["pin"], recorded)
    assert not _holds(page, acted["pin"], {**recorded, "value": "unchecked"})


def test_a_select_step_holds_in_the_label_the_recorder_wrote(page: Any) -> None:
    page.select_option("#pick", "b")
    recorded = _go(page)["prior"]
    page.select_option("#pick", "a")

    acted = _act(page, {"action": "select", "value": "b", "target": {"css_path": "#pick"}})

    assert acted["ok"] and acted["state"] == recorded
    assert _holds(page, acted["pin"], recorded)
    assert _holds(page, acted["pin"], {"value": "b"}), "the value act was given also holds"
    assert not _holds(page, acted["pin"], {"value": "First"})


def test_a_gesture_the_worker_dropped_lends_nothing_to_the_next(page: Any) -> None:
    page.click("#agree")
    dropped = _records(page)[-1]["ref"]
    page.evaluate(
        "(ref) => window.dispatchEvent(new CustomEvent('sro:dropped', {detail: ref}))", dropped
    )

    went = _go(page)

    assert (went["prior"], went["prior_of"]) == (None, None)
