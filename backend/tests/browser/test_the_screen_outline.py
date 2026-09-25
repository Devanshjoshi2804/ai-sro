"""The screen outline, in a real Chrome: after the operator types, no typed
string is anywhere in an outline the recorder sends or the server keeps."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from sro.application.observation.redact import redact_events
from sro.config import get_settings
from sro.infrastructure.steel.capture import _recorder_script

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><html><body>
<form aria-label="Sign in">
  <h1>Verify it's you</h1>
  <label for="pw">Password</label><input id="pw" type="password">
  <button id="show" type="button"
    onclick="pw.type = pw.type === 'text' ? 'password' : 'text'">Show</button>
  <label for="code">Verify</label><input id="code" autocomplete="off">
  <div id="mirror"></div>
  <div id="said" role="status"></div>
  <div contenteditable="true" role="textbox" id="note" aria-label="Note"></div>
  <label for="memo">Memo</label><textarea id="memo"></textarea>
  <label for="dept">Department</label>
  <select id="dept"><option>Finance</option><option>Operations</option></select>
  <button id="go" type="button">Save</button>
</form>
<script>
  code.addEventListener("input", () => {
    mirror.textContent = "Code: " + code.value;
    said.textContent = "Checking " + code.value;
  });
</script>
</body></html>"""

PASSWORD = "hunter2-correct-horse"  # noqa: S105 -- not a credential
OTP = "483920"
NOTE = "call the dentist at four"
MEMO = "pallet 77 goes to dock B"


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


def _typed_everything(page: Any) -> list[dict[str, Any]]:
    page.fill("#pw", PASSWORD)
    page.click("#show")
    page.click("#code")
    page.keyboard.type(OTP)
    page.click("#note")
    page.keyboard.type(NOTE)
    page.fill("#memo", MEMO)
    page.select_option("#dept", label="Operations")
    page.click("#go")
    return _records(page)


def _sent(records: list[dict[str, Any]]) -> str:
    return json.dumps([one.get("outlines") for one in records])


def test_no_typed_value_is_in_any_outline_the_recorder_sends(page: Any) -> None:
    records = _typed_everything(page)

    sent = _sent(records)
    for typed in (PASSWORD, OTP, NOTE, MEMO):
        assert typed not in sent, f"{typed!r} left the page in an outline"
    assert "Code: " not in sent, "the mirror div is free page text and is never kept"


def test_no_typed_value_is_in_any_outline_the_server_keeps(page: Any) -> None:
    records = _typed_everything(page)
    events = [{"kind": "gesture", "tab_id": 1, "gesture": one} for one in records]

    kept = json.dumps([one["gesture"].get("outlines") for one in redact_events(events)])

    for typed in (PASSWORD, OTP, NOTE, MEMO):
        assert typed not in kept, f"{typed!r} reached the server's copy of an outline"


def test_the_outline_still_says_what_the_screen_asks_for(page: Any) -> None:
    records = _typed_everything(page)

    last = records[-1]["outlines"][-1] if records[-1]["outlines"] else None
    screen = last or next(one["outlines"][-1] for one in reversed(records) if one["outlines"])
    labels = {(one["role"], one["label"]) for one in screen["fields"]}
    assert {("textbox", "Password"), ("textbox", "Verify"), ("textbox", "Memo")} <= labels
    assert ("textbox", "Note") in labels
    dept = next(one for one in screen["fields"] if one["label"] == "Department")
    assert dept["options"] == ["Finance", "Operations"]
    assert screen["headings"] == ["Verify it's you"]
    assert "Save" in screen["buttons"]


def test_a_screen_already_sent_from_this_frame_is_not_sent_again(page: Any) -> None:
    page.click("#go")
    page.click("#go")

    records = _records(page)

    assert records[-2]["outlines"] and records[-1]["outlines"] == []


def test_a_dialog_that_appears_is_outlined_before_anyone_acts_on_it(page: Any) -> None:
    page.evaluate(
        """async () => {
          const d = document.createElement('div');
          d.setAttribute('role', 'dialog');
          d.setAttribute('aria-label', 'Confirm delete');
          d.innerHTML = '<button>Delete</button>';
          document.body.append(d);
          await new Promise((settled) => setTimeout(settled, 0));
          d.remove();
        }"""
    )
    page.click("#go")

    records = _records(page)
    seen = list(records[-1]["outlines"])
    assert any({"role": "dialog", "name": "Confirm delete"} in one["landmarks"] for one in seen)


def test_steel_reads_the_same_outline_from_the_live_page(page: Any) -> None:
    page.click("#code")
    page.keyboard.type(OTP)

    outline = page.evaluate("globalThis.sroPage.outline()")

    assert {"role": "form", "name": "Sign in"} in outline["landmarks"]
    assert [one for one in outline["fields"] if one["label"] == "Department"] == [
        {
            "role": "combobox",
            "label": "Department",
            "required": None,
            "options": ["Finance", "Operations"],
        }
    ]
    assert outline["messages"] == [], "the status only echoes the typed code"
    assert OTP not in json.dumps(outline)


def test_a_short_value_echoed_as_it_is_typed_never_leaves_the_page(page: Any) -> None:
    page.click("#code")
    page.keyboard.type("48")
    page.click("#go")

    sent = _sent(_records(page))

    assert "Checking 4" not in sent, "a status echoed the first digits of the code"


def test_text_typed_inside_a_rich_editor_is_never_a_heading(page: Any) -> None:
    page.evaluate(
        """() => document.body.insertAdjacentHTML('beforeend',
          '<div contenteditable="true" role="textbox" aria-label="Minutes">'
          + '<h2 id="topic">Plan</h2><p>Agenda</p></div>')"""
    )
    page.click("#topic")
    page.keyboard.press("End")
    page.keyboard.type(" B7")
    page.click("#go")

    sent = _sent(_records(page)) + json.dumps(page.evaluate("globalThis.sroPage.outline()"))

    assert "B7" not in sent, "a heading the operator typed left the page"


def test_a_shadow_root_a_combobox_a_partial_echo_or_a_url_never_leaves_the_page(page: Any) -> None:
    page.evaluate(
        """() => {
          customElements.define('sro-secret', class extends HTMLElement {
            constructor() {
              super();
              this.attachShadow({ mode: 'open' }).innerHTML = '<input type="password">';
            }
          });
          document.body.insertAdjacentHTML('beforeend',
            '<sro-secret id="host"></sro-secret>'
            + '<input id="who" role="combobox" aria-label="Customer">'
            + '<input id="labelled" aria-labelledby="echo"><span id="echo"></span>'
            + '<div id="hello" role="alert"></div><div id="found" role="status"></div>'
            + '<div role="status">Go on at https://sro.test/cb?access_token=live-token</div>');
          const inner = host.shadowRoot.querySelector('input');
          inner.addEventListener('input', () => { hello.textContent = 'Welcome ' + inner.value; });
          who.addEventListener('input', () => {
            found.textContent = 'No match for ' + who.value.slice(0, 9);
          });
          labelled.addEventListener('input', () => { echo.textContent = labelled.value; });
        }"""
    )
    page.click("#host")
    page.keyboard.type(PASSWORD)
    page.click("#who")
    page.keyboard.type("ACME-7731-QX")
    page.click("#labelled")
    page.keyboard.type(MEMO)
    page.click("#go")

    sent = _sent(_records(page)) + json.dumps(page.evaluate("globalThis.sroPage.outline()"))

    for typed in (PASSWORD, "ACME-7731", MEMO, "live-token"):
        assert typed not in sent, f"{typed!r} left the page in an outline"
