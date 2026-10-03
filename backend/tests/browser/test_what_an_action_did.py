"""The effect the recorder sends after each gesture, in a real Chrome."""
# ruff: noqa: E501

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from sro.config import get_settings
from sro.infrastructure.steel.capture import _recorder_script

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><html><body>
<form aria-label="New Customer Type">
  <label for="code">Code</label><input id="code" aria-required="true">
  <label for="desc">Description</label><input id="desc" disabled>
  <input id="pw" type="password" aria-label="Password">
  <button type="button" id="save">Save</button>
  <button type="button" id="incomplete">Submit empty</button>
  <button type="button" id="ask">Delete</button>
  <button type="button" id="go">Go</button>
  <button type="button" id="boom">Boom</button>
</form>
<script>
  const say = (role, text) => { const d = document.createElement('div'); d.setAttribute('role', role); d.innerText = text; document.body.appendChild(d); };
  save.onclick = () => setTimeout(() => say('status', 'Customer type ' + code.value + ' saved'), 200);
  incomplete.onclick = () => { code.setAttribute('aria-invalid', 'true'); desc.disabled = false; say('alert', 'Code is required'); };
  ask.onclick = () => { const d = document.createElement('div'); d.setAttribute('role', 'dialog'); d.innerHTML = '<h2>Delete?</h2><p>Delete this row?</p><button>Yes</button><button>No</button>'; document.body.appendChild(d); };
  go.onclick = () => { history.pushState({}, '', '/customers/42'); };
  boom.onclick = () => setTimeout(() => { throw new Error('x is undefined at https://wms.example/app.js:1:2'); }, 10);
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
                "window.__sroEffect = (j) => (window.__did = window.__did || []).push(j);"
            )
            context.add_init_script(_recorder_script())
            context.add_init_script(path=get_settings().page_code_path)
            context.route(
                "http://sro.test/**",
                lambda route: route.fulfill(body=PAGE, content_type="text/html"),
            )
            one = context.new_page()
            one.goto("http://sro.test/customers")
            yield one
        finally:
            browser.close()


def _last(page: Any) -> dict[str, Any]:
    return json.loads(page.evaluate("window.__got[window.__got.length - 1]"))


def _effect_of(page: Any, ref: str) -> dict[str, Any]:
    page.wait_for_function(
        f"(window.__did || []).some((j) => JSON.parse(j).of === {json.dumps(ref)})", timeout=5000
    )
    return next(
        json.loads(raw) for raw in page.evaluate("window.__did") if json.loads(raw)["of"] == ref
    )


def test_a_save_that_shows_a_toast_yields_the_toast(page: Any) -> None:
    page.fill("#code", "ABC")
    page.click("#save")
    last = _last(page)
    sent = _effect_of(page, last["ref"])
    assert sent["of_at"] == last["at"]
    assert any(
        one["role"] == "status" and one["text"] == "Customer type ABC saved"
        for one in sent["effect"]["appeared"]
    )
    assert sent["effect"]["ended"] in ("quiet", "max")


def test_a_click_that_opens_a_dialog_yields_its_title_and_buttons(page: Any) -> None:
    page.click("#ask")
    sent = _effect_of(page, _last(page)["ref"])
    dialog = next(one for one in sent["effect"]["appeared"] if one["role"] == "dialog")
    assert (dialog["title"], dialog["buttons"]) == ("Delete?", ["Yes", "No"])


def test_an_incomplete_submit_yields_the_invalid_field_and_the_one_it_enabled(page: Any) -> None:
    page.click("#incomplete")
    effect = _effect_of(page, _last(page)["ref"])["effect"]
    assert {"label": "Code", "change": "invalid"} in effect["fields"]
    assert {"label": "Description", "change": "enabled"} in effect["fields"]
    assert any(
        one["role"] == "alert" and one["text"] == "Code is required" for one in effect["appeared"]
    )


def test_a_route_change_yields_before_and_after(page: Any) -> None:
    page.click("#go")
    effect = _effect_of(page, _last(page)["ref"])["effect"]
    assert (effect["route_before"], effect["route_after"]) == ("/customers", "/customers/42")


def test_an_uncaught_error_is_recorded_as_text(page: Any) -> None:
    page.click("#boom")
    effect = _effect_of(page, _last(page)["ref"])["effect"]
    assert any("x is undefined" in one for one in effect["errors"])


def test_the_next_gesture_ends_the_previous_effect(page: Any) -> None:
    page.click("#ask")
    first = _last(page)["ref"]
    page.click("#go")
    assert _effect_of(page, first)["effect"]["ended"] == "next"


def test_a_shortcut_is_recorded_on_the_open_effect(page: Any) -> None:
    page.click("#code")
    page.keyboard.press("Control+s")
    effect = _effect_of(page, _last(page)["ref"])["effect"]
    assert "ctrl+s" in effect["shortcuts"]


def test_no_effect_ever_carries_what_was_typed_in_a_secret(page: Any) -> None:
    page.fill("#pw", "hunter2")
    page.click("#save")
    _effect_of(page, _last(page)["ref"])
    assert "hunter2" not in json.dumps(page.evaluate("window.__did"))


def test_a_secret_field_s_validation_text_is_never_captured(page: Any) -> None:
    page.evaluate(
        "document.getElementById('pw').addEventListener('click', () => {"
        "pw.setAttribute('aria-invalid','true');"
        "const d = document.createElement('div'); d.className = 'x-form-error-msg'; d.innerText = 'Password hunter2 is wrong'; document.body.appendChild(d); });"
    )
    page.fill("#pw", "hunter2")
    page.click("#pw")
    sent = _effect_of(page, _last(page)["ref"])
    assert "hunter2" not in json.dumps(sent)
    assert not any(one["label"] == "Password" for one in sent["effect"]["fields"])


def test_the_observer_is_gone_once_the_effect_is_sent(page: Any) -> None:
    page.evaluate(
        "() => { window.__live = 0; const O = window.MutationObserver;"
        "window.MutationObserver = class extends O { constructor(f) { super(f); window.__live++; }"
        " disconnect() { window.__live--; super.disconnect(); } }; }"
    )
    page.click("#code")
    _effect_of(page, _last(page)["ref"])
    settled = page.evaluate("window.__live")
    page.click("#ask")
    _effect_of(page, _last(page)["ref"])
    assert page.evaluate("window.__live") == settled
