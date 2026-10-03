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
<h2>Token a=b</h2>
<input id="pin" role="combobox" aria-label="PIN code" aria-controls="lb">
<ul id="lb" role="listbox"><li role="option" id="pin1">1234</li><li role="option">5678</li></ul>
<input id="pin2" role="combobox" aria-label="PIN code" aria-owns="lb2">
<ul id="lb2" class="x-boundlist"><li class="x-boundlist-item" id="pin3">4321</li></ul>
<input id="pw2" type="password" aria-labelledby="pwl"><span id="pwl">Account password</span>
<ul id="long" role="listbox"></ul>
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


def test_a_secret_combos_options_and_choice_are_never_recorded(page: Any) -> None:
    page.click("#pin1")
    assert _all(page)[-1]["choice"] is None
    page.click("#pin3")
    last = _all(page)[-1]
    assert last["choice"] is None
    assert "1234" not in json.dumps(_all(page)) and "4321" not in json.dumps(_all(page))


def test_a_place_carries_no_field_value(page: Any) -> None:
    page.fill("#code", "VALUE-9941")
    page.click("#b")
    assert "VALUE-9941" not in json.dumps([one["place"] for one in _all(page)])


def test_a_secret_field_named_by_aria_labelledby_records_no_name(page: Any) -> None:
    page.fill("#pw2", "hunter2")
    page.click("#a")
    typed = next(one for one in _all(page) if one["kind"] == "type" and one["target"]["secret"])
    assert typed["target"]["fullName"] is None and typed["target"]["labelText"] is None
    secrets = [one["target"] for one in _all(page) if one["target"]["secret"]]
    assert "Account password" not in json.dumps(secrets)


def test_page_text_that_is_not_vocabulary_stays_in_the_page(page: Any) -> None:
    page.click("#b")
    assert "a=b" not in json.dumps(_all(page)[-1]["place"])


def test_an_option_past_the_cut_list_has_no_index(page: Any) -> None:
    page.evaluate(
        "document.getElementById('long').innerHTML = Array.from({length: 60}, (_, i) =>"
        " `<li role=option id=o${i}>Row ${i}</li>`).join('')"
    )
    page.click("#o59")
    choice = _all(page)[-1]["choice"]
    assert choice["chosen"] == "Row 59" and choice["index"] is None and len(choice["options"]) == 50
    page.click("#o3")
    assert _all(page)[-1]["choice"]["index"] == 3
