# backend/tests/browser/test_what_a_gesture_saw.py
"""What a gesture records about where the person was, in a real Chrome."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from sro.config import get_settings
from sro.infrastructure.steel.capture import _recorder_script

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><html><head><title>Customer Types</title>
<meta name="version" content="7.4.2"></head><body>
<h1>Customer Types</h1>
<div role="tablist"><span role="tab" aria-selected="true">General</span>
<span role="tab">Other</span></div>
<form aria-label="New Customer Type">
  <label for="code">Customer code *</label><input id="code" name="code">
  <input id="pw" type="password" aria-label="Password">
  <button type="button" id="a">Add</button><button type="button" id="b">Save</button>
</form>
<ul role="listbox"><li role="option">Bulk</li><li role="option">Pallet</li>
<li role="option" id="retail">Retail</li></ul>
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
            one.goto("http://sro.test/customers#!/types")
            yield one
        finally:
            browser.close()


def _all(page: Any) -> list[dict[str, Any]]:
    return [json.loads(raw) for raw in page.evaluate("window.__got || []")]


def test_a_click_says_where_the_person_was(page: Any) -> None:
    page.click("#b")
    place = _all(page)[-1]["place"]
    assert place["route"] == "/customers#!/types"
    assert place["title"] == "Customer Types"
    assert place["headings"] == ["Customer Types"]
    assert place["tabs"] == ["General"]
    assert "New Customer Type" in place["landmarks"]
    assert place["version"] == "7.4.2"


def test_a_field_records_its_label_its_full_name_and_its_position(page: Any) -> None:
    page.fill("#code", "C-1")
    page.click("#a")
    typed = next(one for one in _all(page) if one["kind"] == "type")
    assert typed["target"]["labelText"] == "Customer code *"
    assert typed["target"]["fullName"] == "Customer code *"
    clicked = _all(page)[-1]
    assert (clicked["target"]["siblingIndex"], clicked["target"]["siblingCount"]) == (0, 2)


def test_a_secret_field_records_no_label_and_no_name(page: Any) -> None:
    page.fill("#pw", "hunter2")
    page.click("#a")
    typed = next(one for one in _all(page) if one["kind"] == "type" and one["target"]["secret"])
    assert typed["target"]["labelText"] is None and typed["target"]["fullName"] is None
    assert "hunter2" not in json.dumps(_all(page))


def test_a_click_on_an_option_records_the_list_and_the_choice(page: Any) -> None:
    page.click("#retail")
    assert _all(page)[-1]["choice"] == {
        "chosen": "Retail",
        "index": 2,
        "options": ["Bulk", "Pallet", "Retail"],
    }


def test_a_click_that_is_not_an_option_records_no_choice(page: Any) -> None:
    page.click("#b")
    assert _all(page)[-1]["choice"] is None
