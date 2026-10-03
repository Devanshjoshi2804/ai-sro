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
  <button type="button" id="clear">Clear</button>
  <button type="button" id="noop">Nothing</button>
  <button type="button" id="tell">Tell</button>
</form>
<script>
  const say = (role, text) => { const d = document.createElement('div'); d.setAttribute('role', role); d.innerText = text; document.body.appendChild(d); };
  save.onclick = () => setTimeout(() => say('status', 'Customer type ' + code.value + ' saved'), 200);
  incomplete.onclick = () => { code.setAttribute('aria-invalid', 'true'); desc.disabled = false; say('alert', 'Code is required'); };
  ask.onclick = () => { const d = document.createElement('div'); d.setAttribute('role', 'dialog'); d.innerHTML = '<h2>Delete?</h2><p>Delete this row?</p><button>Yes</button><button>No</button>'; document.body.appendChild(d); };
  go.onclick = () => { history.pushState({}, '', '/customers/42'); };
  clear.onclick = () => { const v = pw.value; pw.value = ''; say('alert', 'Invalid password ' + v); };
  tell.onclick = () => say('alert', window.__tell);
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


# The recorder keeps one observer of its own for the outline; a leaking watcher shows as more.
def _count_observers(page: Any) -> None:
    page.evaluate(
        "() => { window.__live = 0; const O = window.MutationObserver;"
        "window.MutationObserver = class extends O { constructor(f) { super(f); window.__live++; }"
        " disconnect() { window.__live--; super.disconnect(); } }; }"
    )


def test_the_observer_is_gone_once_the_effect_is_sent(page: Any) -> None:
    _count_observers(page)
    page.click("#ask")
    _effect_of(page, _last(page)["ref"])
    settled = page.evaluate("window.__live")
    page.click("#go")
    _effect_of(page, _last(page)["ref"])
    assert page.evaluate("window.__live") == settled


def test_a_password_cleared_before_the_message_still_never_leaves_the_page(page: Any) -> None:
    page.fill("#pw", "hunter2")
    page.click("#clear")
    sent = _effect_of(page, _last(page)["ref"])
    assert any(one["role"] == "alert" for one in sent["effect"]["appeared"])
    assert "hunter2" not in json.dumps(page.evaluate("window.__did"))


def test_an_iframe_alert_quoting_the_parents_password_never_leaves_the_page(page: Any) -> None:
    page.evaluate(
        "() => { const f = document.createElement('iframe'); f.id = 'f';"
        "f.srcdoc = '<button id=b>Try</button><script>b.onclick = () => { const d = document.createElement(\\'div\\');"
        " d.setAttribute(\\'role\\', \\'alert\\'); d.innerText = \\'Bad password hunter2 for user\\'; document.body.appendChild(d); };"
        "<' + '/script>'; document.body.appendChild(f); }"
    )
    page.fill("#pw", "hunter2")
    page.frame_locator("#f").locator("#b").click()
    child = next(one for one in page.frames if one != page.main_frame)
    child.wait_for_function("(window.__did || []).length > 0", timeout=5000)
    assert "hunter2" not in json.dumps(child.evaluate("window.__did"))


def test_a_cross_origin_frame_cannot_see_the_parents_secrets_so_its_text_is_dropped(
    page: Any,
) -> None:
    page.context.route(
        "http://other.test/**",
        lambda route: route.fulfill(
            content_type="text/html",
            body="<button id=b onclick=\"const d=document.createElement('div');d.setAttribute('role','alert');"
            "d.innerText='Bad password hunter2';document.body.appendChild(d)\">Try</button>",
        ),
    )
    page.evaluate(
        "() => { const f = document.createElement('iframe'); f.id = 'f'; f.src = 'http://other.test/x'; document.body.appendChild(f); }"
    )
    page.fill("#pw", "hunter2")
    page.frame_locator("#f").locator("#b").click()
    child = next(one for one in page.frames if one != page.main_frame)
    child.wait_for_function("(window.__did || []).length > 0", timeout=5000)
    sent = json.loads(child.evaluate("window.__did")[0])
    assert "hunter2" not in json.dumps(sent)
    assert all(one["text"] is None for one in sent["effect"]["appeared"])


def test_a_click_that_changes_nothing_sends_no_effect(page: Any) -> None:
    _count_observers(page)
    page.evaluate(
        "() => { for (let i = 0; i < 200; i++) document.getElementById('noop').click(); }"
    )
    assert len(page.evaluate("window.__got")) == 200
    page.wait_for_function("window.__live <= 1", timeout=8000)
    assert (page.evaluate("window.__did") or []) == []


def test_the_watcher_costs_little_on_a_big_busy_page(page: Any) -> None:
    page.evaluate(
        "() => { const h = document.createElement('div'); for (let i = 0; i < 3000; i++) { const x = document.createElement('input'); x.id = 'i' + i; h.appendChild(x); }"
        "document.body.appendChild(h);"
        "window.__ms = 0; const O = window.MutationObserver;"
        "window.MutationObserver = class extends O { constructor(f) { super((...a) => { const t = performance.now(); try { return f(...a); } finally { window.__ms += performance.now() - t; } }); } };"
        "window.__live = 0; const D = window.MutationObserver; window.MutationObserver = class extends D { constructor(f) { super(f); window.__live++; } disconnect() { window.__live--; super.disconnect(); } };"
        "setInterval(() => { const d = document.createElement('div'); d.className = 'tick'; document.body.appendChild(d); if (document.body.children.length > 50) document.body.lastChild.remove(); }, 5); }"
    )
    page.click("#noop")
    page.wait_for_function("window.__live <= 1", timeout=8000)
    spent = page.evaluate("window.__ms")
    assert spent < 100  # was 850 ms before the callback stopped scanning the page


def test_a_shortcut_typed_in_a_secret_field_is_not_recorded(page: Any) -> None:
    page.click("#pw")
    page.keyboard.press("Control+Alt+s")
    page.click("#ask")
    _effect_of(page, _last(page)["ref"])
    assert "ctrl+alt+s" not in json.dumps(page.evaluate("window.__did"))


def _told(page: Any, text: str) -> Any:
    """What the recorder sends when the page says `text` in an alert after a click."""
    page.evaluate("(t) => { window.__tell = t; }", text)
    page.click("#tell")
    sent = _effect_of(page, _last(page)["ref"])
    return sent["effect"]["appeared"][0]["text"]


def _typed_then_gone(page: Any, secret: str, *then: str) -> None:
    page.fill("#pw", secret)
    for value in then:
        page.fill("#pw", value)


def test_a_secret_cleared_and_replaced_before_the_click_is_still_never_sent(page: Any) -> None:
    _typed_then_gone(page, "hunter2", "", "other99")
    assert _told(page, "Invalid password hunter2") is None


def test_a_secret_cleared_by_one_click_is_still_never_sent_by_the_next(page: Any) -> None:
    page.fill("#pw", "hunter2")
    page.click("#clear")
    _effect_of(page, _last(page)["ref"])
    assert _told(page, "Bad password hunter2") is None


@pytest.mark.parametrize(
    ("secret", "said"),
    [
        ("my  pass  word", "Bad my pass word"),
        ("hunter2 ", "Bad hunter2"),
        ("hun\tter2", "Bad hun ter2"),
        ("HunTer2", "Bad hunter2"),
    ],
)
def test_whitespace_and_case_variants_of_a_gone_secret_are_never_sent(
    page: Any, secret: str, said: str
) -> None:
    _typed_then_gone(page, secret, "", "x1")
    assert _told(page, said) is None


def test_typing_a_secret_does_not_poison_every_text_with_its_letters(page: Any) -> None:
    page.click("#pw")
    page.keyboard.type("hunter2")
    assert _told(page, "Saved changes here") == "Saved changes here"


def test_two_hundred_thousand_inputs_keep_the_page_quick_and_the_latest_secret_known(
    page: Any,
) -> None:
    took = page.evaluate(
        "() => { const t = performance.now(); const el = document.getElementById('pw');"
        "for (let i = 0; i < 200000; i++) { el.value = 's' + ((i * 7919) % 1000003) + 'q';"
        "el.dispatchEvent(new Event('input', { bubbles: true })); }"
        "el.value = ''; el.dispatchEvent(new Event('input', { bubbles: true }));"
        "return performance.now() - t; }"
    )
    assert took < 5000
    last = f"s{(199999 * 7919) % 1000003}q"
    assert _told(page, f"Bad {last}") is None
    assert _told(page, "Saved changes here") == "Saved changes here"


@pytest.mark.parametrize(
    "said",
    [
        "Card ****1234 declined",
        "Bad hun***r2",
        "Card xxxx1234 declined",
        "Bad \u2022\u2022\u2022\u2022er2",
    ],
)
def test_text_with_a_partial_mask_is_never_kept(page: Any, said: str) -> None:
    assert _told(page, said) is None


def test_benign_text_with_one_asterisk_or_few_x_is_kept(page: Any) -> None:
    assert _told(page, "Required *") == "Required *"
    assert _told(page, "Max 5 items") == "Max 5 items"


def test_benign_text_with_x_or_stars_that_is_not_a_mask_is_kept(page: Any) -> None:
    for said in ("Size XXXL", "Mexxxico", "XXL size", "Box xx-12", "Max 12 xxx", "Fox xxx"):
        assert _told(page, said) == said
    assert _told(page, "Wildcard *** matches") == "Wildcard *** matches"


@pytest.mark.parametrize("said", ["Total: $5xxx", "Card xxxx1234 declined", "Bad 12xxx"])
def test_x_run_next_to_digits_is_a_mask(page: Any, said: str) -> None:
    assert _told(page, said) is None


def _add(page: Any, html: str) -> None:
    page.evaluate("(h) => document.body.insertAdjacentHTML('beforeend', h)", html)


def test_a_secret_in_a_field_the_click_unmounts_is_never_sent(page: Any) -> None:
    _add(page, "<button id=swap>Swap</button>")
    page.evaluate(
        "() => { swap.onclick = () => { document.forms[0].remove();"
        " const d = document.createElement('div'); d.setAttribute('role', 'alert');"
        " d.innerText = 'Invalid password hunter2'; document.body.appendChild(d); }; }"
    )
    page.fill("#pw", "hunter2")
    page.click("#swap")
    sent = _effect_of(page, _last(page)["ref"])
    assert any(one["role"] == "alert" for one in sent["effect"]["appeared"])
    assert "hunter2" not in json.dumps(page.evaluate("window.__did"))


def test_a_secret_whose_field_is_removed_after_a_gesture_is_never_sent_later(page: Any) -> None:
    page.fill("#pw", "hunter2")
    page.click("#noop")
    page.evaluate("() => document.getElementById('pw').remove()")
    assert _told(page, "Invalid password hunter2") is None


def test_a_secret_checked_again_stays_known_while_older_ones_are_evicted(page: Any) -> None:
    page.evaluate(
        "() => { window.__fill = (n) => { const el = document.getElementById('pw');"
        "el.value = 'kq' + String(n).padStart(4, '0') + 'z'; el.dispatchEvent(new Event('input', { bubbles: true })); }; }"
    )
    for n in range(300):
        page.evaluate("(n) => window.__fill(n)", n)
        if n % 50 == 49:
            assert _told(page, "Bad kq0000z") is None
    assert _told(page, "Bad kq0000z") is None


@pytest.mark.parametrize(
    "field",
    [
        "<div id=f contenteditable=true aria-label='Password'></div>",
        "<input id=f type=text data-ref='pwd'>",
        "<input id=f type=text aria-label='Login code' style='-webkit-text-security: disc'>",
        "<input id=f type=text style='-webkit-text-security: disc'>",
    ],
)
def test_a_field_that_is_secret_by_how_it_looks_or_is_named_is_never_sent(
    page: Any, field: str
) -> None:
    _add(page, field)
    page.fill("#f", "hunter2")
    page.evaluate(
        "() => { const el = document.getElementById('f'); if ('value' in el) el.value = ''; else el.textContent = ''; }"
    )
    assert _told(page, "Bad hunter2") is None
    page.fill("#f", "hunter3")
    assert _told(page, "Bad hunter3") is None


@pytest.mark.parametrize("name", ["Customer type code", "Postal code", "Code"])
def test_a_job_field_that_ends_in_code_is_still_captured(page: Any, name: str) -> None:
    _add(page, f"<input id=f type=text aria-label='{name}'>")
    page.fill("#f", "VIP77")
    assert _told(page, "Saved VIP77") == "Saved VIP77"
