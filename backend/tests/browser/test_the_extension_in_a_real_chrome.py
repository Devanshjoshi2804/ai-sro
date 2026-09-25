"""Drive a real page with the real extension and read what it uploaded.

The assertions are on the bytes the extension actually sent, not on what it
was meant to send: `docs/10-security-and-data.md` asks for the password proof
to be made against the stored bytes rather than against intent, and until this
existed there was nowhere that could be done.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import pytest

pytestmark = pytest.mark.browser

CLIENT_CODE = "ACME-4471"
# The point of these three is that they are credentials, typed into a real page
# so the test can prove they are absent from what left the browser.
PASSWORD = "hunter2-do-not-store"  # noqa: S105
SESSION_TOKEN = "LIVE-SESSION-TOKEN"  # noqa: S105
FORM_SECRET = "SEKRIT"  # noqa: S105
URL_TOKEN = "LIVE-SSO-TOKEN"  # noqa: S105
PLAIN_SECRET = "plaintext-password-value"  # noqa: S105


def _service_worker(context: Any) -> Any:
    return (
        context.service_workers[0]
        if context.service_workers
        else context.wait_for_event("serviceworker")
    )


def _sign_in(context: Any, worker: Any, api_url: str, console_url: str = "") -> dict[str, Any]:
    """Through the extension's own message API, not by writing storage."""
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    status: dict[str, Any] = page.evaluate(
        """async ([apiUrl, consoleUrl]) => await chrome.runtime.sendMessage(
             {kind: "sign-in", apiUrl, consoleUrl, token: "test.token.here",
              label: "browser-test"})""",
        [api_url, console_url],
    )
    page.close()
    return status


def _watch(context: Any, worker: Any, page: Any) -> dict[str, Any]:
    """Say, the way an operator says it in the panel, that the work is in this tab.

    Nothing is captured from a tab nobody pointed at, so every test that
    expects evidence has to do this first -- which is the rule under test as
    much as any assertion below.

    The tab is identified by bringing it to the front and asking Chrome which
    one that is: Playwright has no tab id to hand over, and matching on the URL
    picks the wrong one the moment a test has two tabs on the same stub.
    """
    page.bring_to_front()
    tab_id = worker.evaluate(
        "async () => (await chrome.tabs.query({active: true, lastFocusedWindow: true}))[0]?.id"
    )
    assert tab_id is not None, "no active tab to watch"
    asking = context.new_page()
    asking.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    answer: dict[str, Any] = asking.evaluate(
        """async (tabId) => await chrome.runtime.sendMessage({kind: "watch-tab", tabId})""",
        tab_id,
    )
    asking.close()
    assert "error" not in answer, f"could not watch that tab: {answer}"
    return answer


def _drive(context: Any, url: str) -> Any:
    page = context.new_page()
    page.goto(url)
    _watch(context, _service_worker(context), page)
    page.fill("#client", CLIENT_CODE)
    page.fill("#pw", PASSWORD)
    page.click("#save")
    return page


def _status(context: Any, worker: Any) -> dict[str, Any]:
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    status: dict[str, Any] = page.evaluate(
        """async () => await chrome.runtime.sendMessage({kind: "status"})"""
    )
    page.close()
    return status


def _flush(context: Any, worker: Any) -> None:
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    page.evaluate("""async () => await chrome.runtime.sendMessage({kind: "flush"})""")
    page.close()


def _clicks_on(batches: list[dict[str, Any]], element_id: str) -> list[dict[str, Any]]:
    return [
        event
        for batch in batches
        for event in batch["events"]
        if event["kind"] == "gesture"
        and ((event["gesture"].get("target") or {}).get("attributes") or {}).get("id") == element_id
    ]


def _flush_until_a_click_arrives(
    context: Any,
    worker: Any,
    batches: list[dict[str, Any]],
    element_id: str,
    deadline_seconds: float = 8.0,
) -> None:
    """The same shape as `capture_fixtures.py`'s fix for I5: flush, check what
    actually arrived, and only sleep between attempts -- never instead of
    checking."""
    until = time.time() + deadline_seconds
    while True:
        _flush(context, worker)
        if _clicks_on(batches, element_id):
            return
        if time.time() >= until:
            return
        time.sleep(0.25)


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
SHOTS_PER_MINUTE = 3
"""What the stub's policy allows. Low enough for a test to reach it."""


@pytest.fixture
def captured(browser: Any, stub: Any) -> dict[str, Any]:
    """Sign in, do a task on a real page, flush, and hand back what went."""
    api_url, batches = stub
    worker = _service_worker(browser)

    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    page = _drive(browser, api_url)
    # The streaming fetch is the last thing the page awaits. If reading a body
    # blocked the page's own call, this never becomes true.
    page.wait_for_function("() => window.__done === true", timeout=15_000)

    _flush(browser, worker)
    page.close()

    assert batches, "the extension uploaded nothing at all"
    events = [event for batch in batches for event in batch["events"]]
    return {"batches": batches, "events": events, "raw": json.dumps(batches)}


def test_a_page_that_streams_does_not_hang_on_our_account(captured: dict[str, Any]) -> None:
    """The fixture's `wait_for_function` is the assertion; this names it.

    `await fetch('/api/stream')` against a body that never ends resolved only
    because the patch stopped waiting for the body before handing the response
    back. Reading it first meant the page's own promise never settled.
    """
    assert captured["events"], "capture produced nothing to judge"


def test_the_password_is_nowhere_in_what_left_the_browser(captured: dict[str, Any]) -> None:
    raw = captured["raw"]
    assert PASSWORD not in raw, "the typed password reached the evidence plane"
    assert FORM_SECRET not in raw, "a credential-named form field reached the evidence plane"
    assert SESSION_TOKEN not in raw, "a live session token reached the evidence plane"


def test_the_business_value_typed_beside_it_is_kept(captured: dict[str, Any]) -> None:
    """The other half of the rule. A redaction that eats real data is how
    people learn to switch redaction off."""
    assert CLIENT_CODE in captured["raw"], "the value the operator typed was lost"


def test_both_transports_were_captured(captured: dict[str, Any]) -> None:
    requests = [e["request"] for e in captured["events"] if e["kind"] == "request"]
    kinds = {r["resource_type"] for r in requests}
    assert "fetch" in kinds, "the fetch patch did not report"
    assert "xhr" in kinds, f"the XHR patch did not report; saw {kinds}"

    legacy = [r for r in requests if r["url"].endswith("/api/legacy")]
    assert legacy, "the responseType=json call was lost, as it was when the getter threw"


def test_the_patch_does_not_announce_itself_to_the_page(browser: Any, stub: Any) -> None:
    """A page that can tell its `fetch` was replaced can behave differently
    when it is -- refuse, degrade, or fingerprint the operator's browser as one
    running this.

    The checks below are the ones a fingerprinting library actually runs, not
    the ones this patch happens to implement against. `fn.toString()` is the
    weakest of them and was for a while the only one asserted, which made the
    test green against a disguise that `Function.prototype.toString.call` --
    the canonical form, used precisely because own-property overrides are the
    obvious dodge -- walked straight past. `length` and the own-property list
    are here for the same reason: each is a shorter tell than the one the
    implementation set out to close.

    Read in the page's own realm (`main_world`), because that is the realm a
    site's own script runs in and the only one whose view of `fetch` matters.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    # Sign in *first*: the MAIN-world patch is registered only while capturing,
    # so without this the page's `fetch` is the untouched native one and every
    # "no tell" assertion below passes against nothing. The final upload check is
    # what proves the patch is actually installed here -- invisible, not absent.
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    page = browser.new_page()
    page.goto(api_url)
    _watch(browser, worker, page)
    # Registering the MAIN-world script is async; a page navigated in the same
    # breath as sign-in can load before injection is in place, which no real
    # operator hits (they sign in once, then browse). Reload with capture already
    # on, the way every subsequent page loads, so injection is at document_start
    # and singular -- then the tells below are read against the patch, not a race.
    page.reload()

    def in_page(expr: str) -> Any:
        return page.evaluate(f"() => {{ {expr} }}", None)

    diag = page.evaluate(
        "() => ({"
        " ft: window.fetch.toString(),"
        " names: Object.getOwnPropertyNames(window.fetch),"
        " ownToString: Object.getOwnPropertyDescriptor(window.fetch, 'toString') !== undefined,"
        " source: Function.prototype.toString.call(window.fetch).slice(0, 80),"
        "})",
        None,
    )
    # The monkey-patch test every anti-bot library runs, in both spellings.
    for name, expression in (
        ("fetch", "window.fetch"),
        ("open", "window.XMLHttpRequest.prototype.open"),
        ("send", "window.XMLHttpRequest.prototype.send"),
        ("setRequestHeader", "window.XMLHttpRequest.prototype.setRequestHeader"),
    ):
        native = f"function {name}() {{ [native code] }}"
        assert in_page(f"return {expression}.toString()") == native, diag
        assert in_page(f"return Function.prototype.toString.call({expression})") == native, diag

    # The name is not a tell either.
    assert in_page("return window.fetch.name") == "fetch"
    # Nor is the arity: `init` and `body` are optional in WebIDL, so a native
    # `fetch` reports 1 and a native `send` reports 0. A replacement that
    # declares its parameters reports 2 and 1, which is a one-token check.
    assert in_page("return window.fetch.length") == 1
    assert in_page("return window.XMLHttpRequest.prototype.send.length") == 0
    assert in_page("return window.XMLHttpRequest.prototype.open.length") == 2
    # No own property the page can find -- asserted as the whole list rather
    # than as the absence of one historical marker name, which passes against
    # native fetch, against any future marker, and against the `toString` that
    # an own-property disguise would itself have added.
    for expression in ("window.fetch", "window.XMLHttpRequest.prototype.open"):
        assert sorted(in_page(f"return Object.getOwnPropertyNames({expression})")) == [
            "length",
            "name",
        ], diag
    # The disguise survives being turned on itself.
    assert in_page("return window.fetch.toString.toString()") == (
        "function toString() { [native code] }"
    )
    # ...and does not swallow the source of a function it never patched, which
    # is how a page's own framework finds its own code.
    assert "return 1 + 1" in in_page(
        "return Function.prototype.toString.call(function probe() { return 1 + 1; })"
    )

    # The patch really was installed and really is invisible: drive the page and
    # prove its traffic reached the evidence plane. Without this the whole test
    # is vacuous -- absence of tells is trivially true when nothing was patched.
    page.click("#save")
    page.wait_for_function("() => window.__done === true", timeout=15_000)
    _flush(browser, worker)
    sent = json.dumps(batches)
    assert "/api/orders" in sent, (
        "the disguised patch captured nothing -- either it did not install or the "
        "disguise broke capture, and the tells above were asserted against native fetch"
    )
    # The XHR half needs its own positive control: `disguise` rewrote `open`,
    # `send` and `setRequestHeader` too, and every assertion above would still
    # pass against an XHR patch that had silently stopped capturing.
    assert "/api/legacy" in sent, (
        "the XHR patch reported nothing, so the XHR tells above proved nothing"
    )


def test_a_credential_in_a_url_or_a_plain_body_is_redacted(browser: Any, stub: Any) -> None:
    """Two ways a credential reached the evidence plane whole.

    A magic-link or SSO callback carries a live token in its query string, and
    `webNavigation` reports that URL to the service worker with no content
    script involved -- so the isolated world's redaction never sees it, and the
    backend redacts bodies and headers but never URLs.

    An unstructured body is the other. `user=...\npassword=...` is JSON to no
    parser, XML to no parser, and not form-urlencoded either, so it fell
    through every branch and was stored verbatim with an empty
    `redacted_fields` -- which reads as a body that was checked and found
    clean.

    Both halves are asserted together with the business data beside them,
    because a redaction that eats real data is how people learn to turn
    redaction off.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    page = browser.new_page()
    page.goto(f"{api_url}/auth/callback?token={URL_TOKEN}&order={CLIENT_CODE}")
    _watch(browser, worker, page)
    # With capture already on, so the navigation is seen the way every
    # subsequent one is rather than racing the registration.
    page.reload()
    page.evaluate(
        """async ([secret, code]) => {
             await fetch('/api/plain', {
               method: 'POST',
               headers: {'content-type': 'text/plain'},
               body: `user=alice\npassword=${secret}\nclientCode=${code}\n`,
             });
           }""",
        [PLAIN_SECRET, CLIENT_CODE],
    )
    _flush(browser, worker)
    page.close()

    sent = json.dumps(batches)
    assert URL_TOKEN not in sent, "a live token in a navigation URL reached the evidence plane"
    assert PLAIN_SECRET not in sent, (
        "a credential in an unstructured body reached the evidence plane"
    )
    # The other half of the rule: everything that is not a credential survived.
    assert "/auth/callback" in sent, "the navigation itself was lost, not just its token"
    assert CLIENT_CODE in sent, "redaction ate the business data beside the credential"
    assert "alice" in sent, "redaction ate the non-credential field beside the credential"


def test_a_body_carried_on_a_request_object_is_still_captured(captured: dict[str, Any]) -> None:
    """`fetch(new Request(url, {body}))` reports its body on the Request, and
    reading it means consuming a clone. It used to be reported as no body at
    all -- and a request body is most of what a skill's parameters come from."""
    wrapped = [
        e["request"]
        for e in captured["events"]
        if e["kind"] == "request" and e["request"]["url"].endswith("/api/wrapped")
    ]
    assert wrapped, "the Request-object call was not captured at all"
    body = wrapped[0]["request_body"]
    assert body is not None and body["text"], "the body on the Request was reported as absent"
    assert CLIENT_CODE in body["text"], "the business value in it was lost"
    assert body["redacted_fields"] == ["secret"], f"unexpected redaction: {body}"
    assert PASSWORD not in body["text"]


def test_a_credential_header_keeps_its_name_and_loses_its_value(captured: dict[str, Any]) -> None:
    posts = [
        e["request"]
        for e in captured["events"]
        if e["kind"] == "request" and e["request"]["url"].endswith("/api/orders")
    ]
    assert posts, "the POST was not captured"
    headers = {k.lower(): v for k, v in posts[0]["request_headers"].items()}
    assert headers.get("authorization") == "«redacted»"
    assert headers.get("content-type") == "application/json", "a semantic header was kept"


def test_gestures_came_through_the_page_realm_recorder(captured: dict[str, Any]) -> None:
    """The recorder only reports at all if it ran where it can see the page.

    Registered in the isolated world it still loaded and still listened, so
    nothing failed -- it simply described every control as though the page had
    no framework at all.
    """
    gestures = [e["gesture"] for e in captured["events"] if e["kind"] == "gesture"]
    assert gestures, "no gesture was captured from a real click and a real keystroke"
    assert {"click", "type"} & {g["kind"] for g in gestures}

    typed = [g for g in gestures if g["kind"] == "type"]
    assert any(g.get("value") == CLIENT_CODE for g in typed), "the typed value was not captured"
    secret = [g for g in typed if g.get("secret")]
    assert secret, "the password field was not recognised as one"
    assert all(g.get("value") is None for g in secret), "a credential kept its value"


def test_the_recorder_can_see_the_page_s_own_framework(captured: dict[str, Any]) -> None:
    """The whole reason the recorder had to move realms.

    `component` is the only locator this WMS has that survives a reload -- its
    DOM ids are assigned in render order. Registered in the isolated world the
    recorder looked for `window.Ext`, found the isolated world's window, and
    reported `component: null` for every control, silently, forever. This
    fails if it is ever moved back.
    """
    gestures = [e["gesture"] for e in captured["events"] if e["kind"] == "gesture"]
    described = [g for g in gestures if g.get("target", {}).get("component")]
    assert described, "every gesture reported component: null -- the page realm is not visible"

    components = {g["target"]["component"]["itemId"] for g in described}
    assert components & {"clientCode", "saveButton"}, f"unrecognised components: {components}"

    one = next(g["target"]["component"] for g in described)
    assert one["framework"] == "extjs"
    assert one["query"], "no component query was built to find this control again"


def test_every_event_carries_the_tab_it_came_from(captured: dict[str, Any]) -> None:
    """`sender.tab.id` is only readable in the worker, so this is the one place
    it can be checked at all."""
    for event in captured["events"]:
        if event["kind"] in ("gesture", "request"):
            assert isinstance(event["tab_id"], int), f"no tab on {event['kind']}"


def test_the_batch_is_shaped_the_way_the_protocol_says(captured: dict[str, Any]) -> None:
    for batch in captured["batches"]:
        assert batch["batch_id"].startswith("bat_")
        assert batch["device_id"] == "dev_browsertest"
        assert batch["mode"] == "passive"
        assert batch["started_at"] <= batch["ended_at"]


def test_the_page_cannot_forge_an_exchange_into_the_evidence_plane(browser: Any, stub: Any) -> None:
    """The two realms talk over an event the page can dispatch too.

    A fabricated exchange is not a harmless lie: episodes are mined out of this
    evidence and become candidate skills an operator is offered. The page-realm
    patch and the isolated relay agree on a secret at `document_start`, before
    any page script exists to overhear it or to get in first.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    page = browser.new_page()
    page.goto(api_url)
    _watch(browser, worker, page)
    page.evaluate(
        """() => window.dispatchEvent(new CustomEvent("sro:request", {detail: JSON.stringify({
             request_id: "req_forged", method: "DELETE",
             url: "https://wms.example.test/api/everything",
             resource_type: "xhr", started_at: "2026-08-24T09:00:00.000Z",
             request_headers: {}, response_headers: {},
             request_body_text: null, response_body_text: null,
             status: 200, duration_ms: 1, failure_reason: null,
           })}))"""
    )
    # And the obvious way to try to learn the secret after the fact.
    page.evaluate("""() => window.dispatchEvent(new CustomEvent("sro:need-hello"))""")
    heard = page.evaluate(
        """() => new Promise((resolve) => {
             window.addEventListener("sro:hello", (e) => resolve(e.detail), {once: true});
             window.dispatchEvent(new CustomEvent("sro:need-hello"));
             setTimeout(() => resolve(null), 250);
           })"""
    )
    assert heard is None, "the page was told the secret after document_start"

    page.click("#save")
    page.wait_for_function("() => window.__done === true", timeout=15_000)

    options = browser.new_page()
    options.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    options.evaluate("""async () => await chrome.runtime.sendMessage({kind: "flush"})""")

    uploaded = json.dumps(batches)
    assert "req_forged" not in uploaded, "a page-fabricated exchange reached the evidence plane"
    assert "api/everything" not in uploaded
    # The genuine traffic from the same page still went, so this is not simply
    # a test of capture being broken.
    assert "/api/orders" in uploaded, "real capture stopped working"


# --- the two privacy claims, made against a real browser rather than intent ---


def test_pause_stops_capture_on_a_tab_that_is_already_open(browser: Any, stub: Any) -> None:
    """The hole the audit found, checked where it actually lived.

    Withdrawing a content-script registration does nothing to a document that
    already has the scripts. The tab is opened *first* and paused after, which
    is the only ordering that would have caught this: pause with no tab open
    looks fine either way.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    page = browser.new_page()
    page.goto(api_url)  # injected while capture is on
    _watch(browser, worker, page)

    options = browser.new_page()
    options.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    status = options.evaluate(
        """async () => await chrome.runtime.sendMessage({kind: "set-paused", paused: true})"""
    )
    assert status["capturing"] is False, "the extension did not report itself paused"

    page.fill("#client", CLIENT_CODE)
    page.click("#save")
    page.wait_for_function("() => window.__done === true", timeout=15_000)

    # Un-pause *before* flushing, and this is the whole point. While paused,
    # flushing uploads nothing whatever the queue holds, so a test that flushed
    # here would pass even if every keystroke had been queued -- it would only
    # be proving that a paused device does not upload. What has to be true is
    # that nothing was captured at all, and the way to see that is to lift the
    # pause and give the queue every chance to send.
    status = options.evaluate(
        """async () => await chrome.runtime.sendMessage({kind: "set-paused", paused: false})"""
    )
    assert status["capturing"] is True, "the extension did not resume"
    options.evaluate("""async () => await chrome.runtime.sendMessage({kind: "flush"})""")

    uploaded = json.dumps(batches)
    assert CLIENT_CODE not in uploaded, "work done while paused was queued and sent on resume"
    typed = [
        event
        for batch in batches
        for event in batch["events"]
        if event["kind"] == "gesture" and event["gesture"].get("value") == CLIENT_CODE
    ]
    assert not typed, f"{len(typed)} gestures survived the pause"


def test_an_excluded_host_produces_nothing_at_all(browser: Any, stub: Any) -> None:
    """ADR 008: an excluded page is not filtered afterwards, it is untouched.

    Both names reach the same server, so the only difference between the two
    halves of this test is the tenant's policy.
    """
    api_url, batches = stub
    port = api_url.rsplit(":", 1)[1]
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    excluded = browser.new_page()
    excluded.goto(f"http://localhost:{port}/")
    # Nothing of ours should be running here at all.
    assert excluded.evaluate("() => typeof window.__sroRecord") == "undefined", (
        "the recorder was injected into an excluded host"
    )
    assert excluded.evaluate("() => window.fetch.__sro === undefined") is True, (
        "the network patch was installed on an excluded host"
    )
    excluded.fill("#client", CLIENT_CODE)
    excluded.click("#save")
    excluded.wait_for_function("() => window.__done === true", timeout=15_000)

    options = browser.new_page()
    options.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    options.evaluate("""async () => await chrome.runtime.sendMessage({kind: "flush"})""")

    events = [event for batch in batches for event in batch["events"]]
    assert not events, f"an excluded host produced {len(events)} events"
    assert CLIENT_CODE not in json.dumps(batches)


def test_a_host_the_operator_granted_is_recorded_despite_the_exclusion(
    browser: Any, stub: Any
) -> None:
    """Pressing "watch this host anyway" has to actually record something.

    The grant is the operator's own decision to observe a host the tenant
    excludes by default -- a mailbox they want a task learned from. It was
    honoured where the content scripts are registered and dropped at the one
    gate every captured event passes through, so the panel said "everything you
    do here is evidence" while the worker discarded every gesture and every
    call as an excluded host. A surface claiming to observe, and no evidence,
    is the failure this file exists to catch.
    """
    api_url, batches = stub
    port = api_url.rsplit(":", 1)[1]
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    # No storage poking: `_watch` on an excluded host asks the backend for the
    # grant itself, which is exactly what the operator's press does.
    granted = browser.new_page()
    granted.goto(f"http://localhost:{port}/")  # excluded by the tenant policy
    _watch(browser, worker, granted)
    granted.fill("#client", CLIENT_CODE)
    granted.click("#save")
    granted.wait_for_function("() => window.__done === true", timeout=15_000)
    _flush(browser, worker)
    granted.close()

    events = [event for batch in batches for event in batch["events"]]
    assert events, "a granted host recorded nothing at all"
    assert any(
        event["kind"] == "gesture" and event["gesture"].get("value") == CLIENT_CODE
        for event in events
    ), "the grant admitted no gesture"
    assert any(
        event["kind"] == "request" and "/api/orders" in event["request"]["url"] for event in events
    ), "the grant admitted no calls"


def test_a_gesture_is_illustrated_by_a_screenshot_of_the_page(
    captured: dict[str, Any], artifacts: list[dict[str, Any]]
) -> None:
    """The picture is a real PNG, filed against the batch that carries the
    gesture it follows, and named by which gesture that is.

    Asserted against the multipart the extension actually sent, because the
    key the backend writes is built from these fields and nothing else: a
    `frame_index` that named no gesture would file the picture where no miner
    reading the batch would look for it.
    """
    assert artifacts, "no screenshot was uploaded for a page full of clicking"

    batch_ids = {batch["batch_id"] for batch in captured["batches"]}
    gestures_in = {
        batch["batch_id"]: sum(1 for e in batch["events"] if e["kind"] == "gesture")
        for batch in captured["batches"]
    }

    for shot in artifacts:
        assert shot["kind"] == "screenshot", shot["kind"]
        assert shot["device_id"] == "dev_browsertest"
        assert shot["batch_id"] in batch_ids, "a screenshot filed against no batch that was sent"
        assert shot["file"].startswith(PNG_MAGIC), "what was uploaded is not a PNG"
        frame = int(shot["frame_index"])
        assert 0 <= frame < gestures_in[shot["batch_id"]], (
            f"frame {frame} names no gesture in a batch of {gestures_in[shot['batch_id']]}"
        )

    assert len({(s["batch_id"], s["frame_index"]) for s in artifacts}) == len(artifacts), (
        "two screenshots claim the same frame, so one overwrites the other"
    )


def test_the_screenshots_stop_at_the_tenant_s_cap(
    browser: Any, stub: Any, artifacts: list[dict[str, Any]]
) -> None:
    """A picture per gesture is the expensive thing this extension can do.

    The cap is the tenant's, delivered on the policy, and it is enforced here
    rather than by the backend -- so if this does not hold it, nothing does.
    Ten deliberate clicks against a cap of three.
    """
    api_url, _ = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    page = browser.new_page()
    page.goto(api_url)
    _watch(browser, worker, page)
    page.reload()
    # Paced past Chrome's own limit, which is not the one under test: it
    # refuses more than two `captureVisibleTab` calls a second, so ten clicks
    # in a tight loop are answered by two pictures whatever the tenant's cap
    # says. Spaced out, every attempt is allowed to reach the cap, and the cap
    # is the only thing deciding how many are taken.
    for _ in range(10):
        page.click("#save")
        page.wait_for_timeout(200)
    page.wait_for_function("() => window.__done === true", timeout=15_000)
    _flush(browser, worker)
    page.close()

    # Exactly the cap, not merely under it. Ten clicks with no cap in force
    # send ten; a cap that spent a slot on a capture Chrome had refused would
    # send fewer, and "fewer" is what an assertion of "at most three" cannot
    # tell from a cap that works.
    assert len(artifacts) == SHOTS_PER_MINUTE, (
        f"{len(artifacts)} screenshots went for a cap of {SHOTS_PER_MINUTE} a minute"
    )


def test_a_screenshot_the_backend_fumbles_is_retried_on_the_next_tick(
    browser: Any,
    stub: Any,
    artifacts: list[dict[str, Any]],
    fumble_artifacts: Any,
) -> None:
    """A picture outlives the batch it belongs to.

    It used to be given up the moment its upload failed, because the only
    alternative on offer was holding evidence the backend had already stored
    in the queue and re-sending the whole batch to carry one PNG. Staged
    against the batch that has been accepted, it can simply be tried again --
    and the batch, which is the expensive half, is not sent a second time.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    fumble_artifacts(1)
    page = _drive(browser, api_url)
    page.wait_for_function("() => window.__done === true", timeout=15_000)

    _flush(browser, worker)
    assert batches, "the events did not go, so there is no batch for a screenshot to wait on"
    assert not artifacts, "the stub was told to refuse the first screenshot and did not"
    sent_batches = len(batches)

    _flush(browser, worker)
    page.close()

    assert artifacts, "the refused screenshot was given up rather than tried again"
    assert len(batches) == sent_batches, (
        "the batch was uploaded a second time to carry a screenshot, which is what "
        "staging them separately exists to avoid"
    )
    assert artifacts[0]["file"].startswith(PNG_MAGIC)
    assert artifacts[0]["batch_id"] == batches[0]["batch_id"], (
        "the retry filed the picture against a different batch than the one it illustrates"
    )


def test_a_screenshot_the_backend_keeps_refusing_is_eventually_given_up(
    browser: Any,
    stub: Any,
    artifacts: list[dict[str, Any]],
    fumble_artifacts: Any,
) -> None:
    """Retrying has to have a floor, or one unlucky picture is retried on
    every alarm for as long as the browser is open -- holding its bytes on the
    device the whole time. Three attempts, then it is dropped and said out
    loud, and the pictures behind it are not held up by it.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    fumble_artifacts(3)
    page = _drive(browser, api_url)
    page.wait_for_function("() => window.__done === true", timeout=15_000)

    for _ in range(3):
        _flush(browser, worker)
    assert not artifacts, "the stub was told to refuse three uploads and did not"

    trouble = _status(browser, worker)["lastError"]
    assert "given up after 3 attempts" in trouble, f"the operator was not told: {trouble!r}"

    # The one that was given up does not take the rest of the queue with it.
    _flush(browser, worker)
    page.close()
    assert artifacts, "the pictures behind the one that was dropped never went"
    assert batches, "the events went, whatever happened to the pictures"


def _dial(browser: Any, stub: Any, channel: Any) -> tuple[Any, Any]:
    """Sign in, wait for the socket, and hand back the channel and a page."""
    api_url, _ = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"
    open_channel = channel()
    page = browser.new_page()
    page.goto(api_url)
    _watch(browser, worker, page)
    page.reload()
    return open_channel, page


def test_the_extension_dials_in_and_says_what_it_is(browser: Any, stub: Any, channel: Any) -> None:
    """No endpoint drives a device; the browser has to dial out, or there is no
    way in at all. `hello` is how the backend learns which build answered."""
    open_channel, page = _dial(browser, stub, channel)
    page.close()

    hello = open_channel.saw("hello")
    assert hello["extension_version"], "the extension did not name its version"
    assert hello["tabs"] >= 1


def test_a_control_is_found_by_the_page_s_own_component_query(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The locator ladder, in the order it is given, answering with the rung
    that worked.

    `matched_by` is not a diagnostic nicety: a step that only ever matches on
    the last fallback is a step about to break, and the backend records that.
    """
    open_channel, page = _dial(browser, stub, channel)

    open_channel.command(
        "cmd_type",
        "ui.perform",
        {
            "action": "type",
            "value": CLIENT_CODE,
            "locators": [
                {
                    "strategy": "component",
                    "query": "panel#clients textfield#clientCode",
                    "within": None,
                    "visible_only": True,
                },
                {"strategy": "css_path", "query": "#client", "within": None, "visible_only": True},
            ],
        },
    )
    answer = open_channel.answer("cmd_type")
    assert answer["ok"] is True, answer
    assert answer["result"]["matched_by"] == "component", (
        "the component query was skipped, so the ladder fell to a weaker rung"
    )
    assert answer["result"]["performed"] is True

    # The value really is in the field: an answer of "performed" against a form
    # nobody filled is the exact failure this rung exists to avoid.
    assert page.input_value("#client") == CLIENT_CODE
    page.close()


def test_a_control_that_is_not_there_is_said_to_be_not_there(
    browser: Any, stub: Any, channel: Any
) -> None:
    """`control_not_found` is a fact about the page, and the backend counts it
    against the skill. It must not be answered for anything else."""
    open_channel, page = _dial(browser, stub, channel)

    open_channel.command(
        "cmd_missing",
        "ui.perform",
        {
            "action": "click",
            "value": None,
            "locators": [
                {
                    "strategy": "test_id",
                    "query": "nothing-here",
                    "within": None,
                    "visible_only": True,
                }
            ],
        },
    )
    answer = open_channel.answer("cmd_missing")
    page.close()

    assert answer["ok"] is False
    assert answer["error"]["kind"] == "control_not_found", answer
    assert "test_id=nothing-here" in answer["error"]["detail"], (
        "the answer does not say what it tried"
    )


def test_the_vision_rung_gets_a_screen_it_can_answer_in(
    browser: Any, stub: Any, channel: Any
) -> None:
    """A picture, the names of the controls on it, and the space both are
    measured in.

    The size reported is the CSS viewport rather than the picture's own pixels,
    because the coordinates the model answers with are fed straight back as
    `ui.perform_at`. On a retina display the two differ by the scale factor,
    which is a click a quarter of the way up the page.
    """
    open_channel, page = _dial(browser, stub, channel)
    open_channel.command("cmd_shot", "screenshot", {"inline": True}, deadline_ms=30_000)
    answer = open_channel.answer("cmd_shot", timeout=40.0)

    viewport = page.evaluate("() => [window.innerWidth, window.innerHeight]")
    page.close()

    assert answer["ok"] is True, answer
    result = answer["result"]
    assert base64.b64decode(result["image_base64"]).startswith(PNG_MAGIC)
    assert result["mime_type"] == "image/png"
    assert [result["width"], result["height"]] == viewport, (
        "the screen was measured in a different space than the one clicks land in"
    )
    assert "Client Code" in result["text_digest"], "the controls' own names were not read"


def test_a_click_at_a_point_lands_where_it_was_aimed(browser: Any, stub: Any, channel: Any) -> None:
    """The other half of the vision rung: a coordinate is not a control the
    demonstration identified, so it is a separate command."""
    open_channel, page = _dial(browser, stub, channel)
    box = page.evaluate(
        """() => {
             const r = document.getElementById('save').getBoundingClientRect();
             return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
           }"""
    )

    open_channel.command(
        "cmd_at", "ui.perform_at", {"action": "click", "x": box[0], "y": box[1], "value": None}
    )
    answer = open_channel.answer("cmd_at")
    assert answer["ok"] is True, answer

    # The page's own handler ran, which is the only proof the click was real.
    page.wait_for_function("() => window.__done === true", timeout=15_000)
    page.close()


def test_a_request_is_sent_with_the_operator_s_own_session(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The whole reason execution reaches into somebody's browser: the call
    carries their cookies, so a skill can be replayed against a system this
    deployment holds no credentials for."""
    open_channel, page = _dial(browser, stub, channel)
    page.evaluate("() => { document.cookie = 'wms_session=abc123; path=/'; }")

    api_url, _ = stub
    open_channel.command(
        "cmd_http",
        "http.send",
        {
            "method": "POST",
            "url": f"{api_url}/api/echo",
            "headers": {"content-type": "application/json"},
            "body": '{"code":"TESTSRO"}',
        },
    )
    answer = open_channel.answer("cmd_http")
    page.close()

    assert answer["ok"] is True, answer
    assert answer["result"]["status"] == 200
    body = json.loads(answer["result"]["body"])
    assert body["cookie"] == "wms_session=abc123", (
        "the request went without the page's session, which is the point of sending it from here"
    )
    assert body["body"] == '{"code":"TESTSRO"}'


def test_a_request_with_no_tab_open_goes_out_from_the_worker_itself(
    browser: Any, stub: Any, channel: Any
) -> None:
    """No page on the origin, no `live_headers` -- so `httpSend` runs
    `sroPage.send` in the worker's own realm rather than a page's.

    A service worker cannot `eval` a fetched string (no `unsafe-eval` in its
    default CSP) or dynamically `import()` (disallowed for a
    `ServiceWorkerGlobalScope` by spec), so the only way `globalThis.sroPage`
    can exist here at all is the static `import "../page/page-code.js"` at
    the top of `commands.js` having run when the worker started. This is the
    one path in the whole extension that proves that happened.
    """
    api_url, _ = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"
    open_channel = channel()

    open_channel.command(
        "cmd_no_tab",
        "http.send",
        {
            "method": "POST",
            "url": f"{api_url}/api/echo",
            "headers": {"content-type": "application/json"},
            "body": '{"code":"NOTAB"}',
        },
    )
    answer = open_channel.answer("cmd_no_tab")

    assert answer["ok"] is True, answer
    assert answer["result"]["status"] == 200
    assert json.loads(answer["result"]["body"])["body"] == '{"code":"NOTAB"}'


def test_a_session_the_backend_supplies_is_not_what_goes_out(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The tab's own session, and only ever that.

    `Cookie` is a forbidden header name for `fetch`: the browser drops whatever
    the caller set and sends the tab's own. So a run in somebody's browser is
    authenticated by their session whether or not the deployment holds one --
    and a resolved cookie travelling with the command is a value that reaches
    nothing, while the executor refuses to send the step without it.
    """
    open_channel, page = _dial(browser, stub, channel)
    api_url, _ = stub
    page.evaluate("() => { document.cookie = 'wms_session=the-operator; path=/'; }")

    open_channel.command(
        "cmd_forged",
        "http.send",
        {
            "method": "POST",
            "url": f"{api_url}/api/echo",
            "headers": {"cookie": "wms_session=from-the-vault"},
            "body": "{}",
        },
    )
    answer = open_channel.answer("cmd_forged")
    page.close()

    assert answer["ok"] is True, answer
    assert json.loads(answer["result"]["body"])["cookie"] == "wms_session=the-operator", (
        "the header the executor resolved reached the wire; it is supposed to be dropped"
    )


def test_each_half_of_a_workflow_is_sent_from_its_own_system_s_tab(
    browser: Any, stub: Any, channel: Any
) -> None:
    """A workflow is one skill whose steps call two systems.

    Both halves going out of one tab is the failure that has two faces: the ERP
    call arrives carrying the WMS's session -- one customer system's credentials
    handed to another -- and it arrives unauthenticated for the system it is
    actually addressed to. The tab is picked per call, from the call's own URL,
    which is the only thing that makes both halves right at once.
    """
    open_channel, page = _dial(browser, stub, channel)
    api_url, _ = stub
    page.evaluate("() => { document.cookie = 'wms_session=warehouse; path=/'; }")

    # A second system, as far as a browser is concerned: the same stub answers
    # on `localhost` as on `127.0.0.1`, and cookies do not cross between them.
    other_url = api_url.replace("127.0.0.1", "localhost")
    other = browser.new_page()
    other.goto(other_url)
    other.evaluate("() => { document.cookie = 'erp_session=finance; path=/'; }")

    sent = {}
    for name, url in (("cmd_wms", api_url), ("cmd_erp", other_url)):
        open_channel.command(
            name,
            "http.send",
            {
                "method": "POST",
                "url": f"{url}/api/echo",
                "headers": {"content-type": "application/json"},
                "body": "{}",
            },
        )
        answer = open_channel.answer(name)
        assert answer["ok"] is True, answer
        sent[name] = json.loads(answer["result"]["body"])["cookie"]

    other.close()
    page.close()

    assert sent["cmd_wms"] == "wms_session=warehouse"
    assert sent["cmd_erp"] == "erp_session=finance", (
        "the second half went out of the first half's tab, carrying its session"
    )


def test_navigating_the_tab_the_operator_is_watching_is_refused(
    browser: Any, stub: Any, channel: Any
) -> None:
    """Refused, not done quietly. A run started by a cron or a mail relay may
    not take the screen out from under somebody who is working on it."""
    open_channel, page = _dial(browser, stub, channel)
    api_url, _ = stub

    open_channel.command("cmd_nav", "navigate", {"url": f"{api_url}/somewhere-else"})
    answer = open_channel.answer("cmd_nav")
    page.close()

    assert answer["ok"] is False
    assert answer["error"]["kind"] == "focus_not_permitted", answer


def test_an_aborted_run_is_refused_rather_than_performed(
    browser: Any, stub: Any, channel: Any
) -> None:
    open_channel, page = _dial(browser, stub, channel)

    open_channel.command("cmd_abort", "abort", {"run_id": "run_1"})
    assert open_channel.answer("cmd_abort")["ok"] is True

    open_channel.command(
        "cmd_after",
        "ui.perform",
        {
            "action": "click",
            "value": None,
            "locators": [
                {"strategy": "css_path", "query": "#save", "within": None, "visible_only": True}
            ],
        },
        run_id="run_1",
    )
    answer = open_channel.answer("cmd_after")
    page.close()

    assert answer["ok"] is False
    assert answer["error"]["kind"] == "aborted", answer


def test_a_replay_does_not_arrive_as_something_the_operator_did(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The evidence plane must not fill up with a robot imitating a person.

    A replayed click fires the page's listeners like any other, so the recorder
    sees it and the patched fetch reports its traffic. Mined, that is the system
    learning a task from its own replay of that task, and then offering it back
    as something worth automating.
    """
    _, batches = stub
    worker = _service_worker(browser)
    open_channel, page = _dial(browser, stub, channel)

    open_channel.command(
        "cmd_drive",
        "ui.perform",
        {
            "action": "click",
            "value": None,
            "locators": [
                {
                    "strategy": "component",
                    "query": "panel#clients button#saveButton",
                    "within": None,
                    "visible_only": True,
                }
            ],
        },
    )
    assert open_channel.answer("cmd_drive")["ok"] is True
    page.wait_for_function("() => window.__done === true", timeout=15_000)

    _flush(browser, worker)
    page.close()

    sent = json.dumps(batches)
    assert "/api/orders" not in sent, "a replayed request was captured as the operator's own"
    gestures = [e for b in batches for e in b["events"] if e["kind"] == "gesture"]
    assert not gestures, f"a replayed click was captured as a gesture: {gestures}"


def test_navigation_the_trigger_allows_is_performed_and_reported(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The other side of the focus rule, and `ui.url` proving it happened.

    `allow_focus` is the run's trigger saying the operator is watching this and
    asked for it. Without a case that goes through, the refusal above is the
    only path anything exercises and `navigate` could be broken outright.
    """
    open_channel, page = _dial(browser, stub, channel)
    api_url, _ = stub

    open_channel.command("cmd_go", "navigate", {"url": f"{api_url}/orders", "allow_focus": True})
    assert open_channel.answer("cmd_go") == {
        "command_id": "cmd_go",
        "ok": True,
        "result": {"navigated": True},
    }
    page.wait_for_url(f"{api_url}/orders", timeout=15_000)

    open_channel.command("cmd_where", "ui.url", {})
    answer = open_channel.answer("cmd_where")
    page.close()

    assert answer["ok"] is True, answer
    assert answer["result"]["url"] == f"{api_url}/orders", (
        "the browser reported a different page than the one it is on"
    )


def test_the_browser_says_when_its_operator_is_working(
    browser: Any, stub: Any, channel: Any
) -> None:
    """Sent from the operator's own gestures, so the backend can queue rather
    than act.

    Typed into a real field, because the point is that a person at a keyboard
    produces it: a page's own background traffic is not somebody working, and a
    device that called every XHR "busy" would delay every run it was given.
    """
    open_channel, page = _dial(browser, stub, channel)
    page.fill("#client", CLIENT_CODE)
    # Clicked away from the field, because a value typed into an input is
    # reported when it is committed rather than per keystroke -- the same
    # reason the recorder waits for `change`.
    page.click("h1")

    busy = open_channel.saw("busy")
    page.close()

    assert busy["reason"], "the operator was not told what made the browser busy"
    assert 0 < busy["for_ms"] <= 30_000, (
        f"a busy window of {busy['for_ms']}ms is not something the backend can bound"
    )


def test_typing_at_a_point_puts_the_value_in_the_field_under_it(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The vision rung types where it looked, not where focus happened to be.

    A synthetic click does not move focus -- only a trusted one does -- so
    reading `document.activeElement` after dispatching one found whatever the
    operator had last focused, or `<body>`. The keystrokes went into the wrong
    field or nowhere at all, and the command still answered `performed: true`,
    which the run then verified against a form nobody had filled.
    """
    open_channel, page = _dial(browser, stub, channel)
    # Focus somewhere else first, so "wherever focus already was" and "under
    # the point" are different answers and the test can tell them apart.
    page.click("#pw")
    box = page.evaluate(
        """() => {
             const r = document.getElementById('client').getBoundingClientRect();
             return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
           }"""
    )

    open_channel.command(
        "cmd_type_at",
        "ui.perform_at",
        {"action": "type", "x": box[0], "y": box[1], "value": CLIENT_CODE},
    )
    answer = open_channel.answer("cmd_type_at")
    assert answer["ok"] is True, answer

    typed = page.input_value("#client")
    other = page.input_value("#pw")
    page.close()

    assert typed == CLIENT_CODE, f"the field under the point holds {typed!r}"
    assert other == "", "the value went into the field that happened to have focus"


def test_a_screen_is_refused_rather_than_stitched_from_two_pages(
    browser: Any, stub: Any, channel: Any
) -> None:
    """`captureVisibleTab` photographs whatever is active in the window, not
    the tab it is handed.

    So when the page to be driven is not the visible one, the picture and the
    `width`/`height`/`text_digest` beside it would come from different
    documents -- and the coordinates a model answers with are fed back as
    `ui.perform_at`, which acts on the second.

    This is the guessing path: no origin, so the driven page is whatever http
    tab was last touched. Refused with `focus_not_permitted`, which says the
    truth -- the browser could photograph that page, but not without taking the
    operator's screen, and this run was not given permission to.
    """
    open_channel, page = _dial(browser, stub, channel)
    # A blank tab in front, so the driven page is the newest *http* tab while
    # not being the one on screen.
    blank = browser.new_page()
    blank.goto("about:blank")

    open_channel.command("cmd_split", "screenshot", {"inline": True}, deadline_ms=20_000)
    answer = open_channel.answer("cmd_split")
    blank.close()
    page.close()

    assert answer["ok"] is False, "a screen was answered from two different pages"
    # The kind matters: `focus_not_permitted` and `no_tab_for_system` are both
    # "no browser to act in" as far as the promotion ladder is concerned, but
    # only one of them tells the operator that permission is the missing piece.
    assert answer["error"]["kind"] == "focus_not_permitted", answer
    # And the detail, because Chrome refuses to photograph a blank tab on its
    # own -- asserting a kind alone would pass against an extension with no
    # such check in it at all.
    assert "not the visible one" in answer["error"]["detail"], (
        "the refusal came from Chrome declining the capture, not from the check under test"
    )


def test_a_screenshot_that_fails_does_not_take_the_gesture_with_it(
    browser: Any, stub: Any, channel: Any
) -> None:
    """A gesture is the one event this system never drops.

    Capturing the picture that illustrates it reads and writes
    `chrome.storage`, and either can reject. Unguarded, that exception left
    `queue.enqueue` unreached and the gesture gone -- a failed photograph
    deleting the thing it was a photograph of.
    """
    _, batches = stub
    worker = _service_worker(browser)
    _dial(browser, stub, channel)
    page = browser.new_page()
    page.goto(stub[0])
    page.reload()
    _watch(browser, worker, page)

    # Break the write the per-minute count goes through, in the worker itself.
    worker.evaluate(
        """() => {
             globalThis.__realSet = chrome.storage.local.set;
             chrome.storage.local.set = () => Promise.reject(new Error("storage is full"));
           }"""
    )
    page.click("h1")
    page.wait_for_timeout(500)
    worker.evaluate("""() => { chrome.storage.local.set = globalThis.__realSet; }""")

    _flush(browser, worker)
    page.close()

    gestures = [e for b in batches for e in b["events"] if e["kind"] == "gesture"]
    assert gestures, "the gesture was lost because its screenshot could not be taken"


def test_the_run_names_the_page_rather_than_taking_whatever_is_in_front(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The tab is chosen by the system the skill was taught on.

    Two pages are open and the wrong one is in front. A command that guesses
    acts on the page the operator happens to be looking at, which in a real
    browser is as likely to be their inbox as the WMS -- so the origin the run
    carries decides, and the visible page is left alone.
    """
    open_channel, page = _dial(browser, stub, channel)
    api_url, _ = stub

    # The page that is *not* the system, and it is the one in front: the same
    # stub answers on `localhost` as on `127.0.0.1`, and those are two origins
    # as far as a browser is concerned -- a real second system, with no DNS and
    # no second server.
    elsewhere = browser.new_page()
    elsewhere.goto(api_url.replace("127.0.0.1", "localhost"))

    open_channel.command(
        "cmd_named",
        "ui.perform",
        {
            "action": "type",
            "value": CLIENT_CODE,
            "origin": api_url,
            "locators": [
                {"strategy": "css_path", "query": "#client", "within": None, "visible_only": True}
            ],
        },
    )
    answer = open_channel.answer("cmd_named")
    assert answer["ok"] is True, answer

    driven = page.input_value("#client")
    untouched = elsewhere.input_value("#client")
    elsewhere.close()
    page.close()

    assert driven == CLIENT_CODE, "the page the run named was not the one driven"
    assert untouched == "", "the run typed into the page that happened to be in front"


def test_a_run_whose_system_is_not_open_is_told_where_it_is(
    browser: Any, stub: Any, channel: Any
) -> None:
    """Not on the system, and told so by being told where it IS.

    This used to answer `no_tab_for_system`, and the run built a look with no
    url at all and reported "the browser is on None" -- measured on the
    deployment 2026-09-19, run `run_fdc7e7ff`, with the operator looking at a
    sign-in page the whole time. A sign-in page is on another origin by
    definition, so the one case this refusal was written for is the case it
    was wrong about.

    Reading is not driving: nothing is performed in that tab. `url` stays null,
    which is what the step is judged on -- the run still fails, because it is
    not on the screen it was demonstrated on -- and `elsewhere` is what makes
    the failure say something.
    """
    open_channel, page = _dial(browser, stub, channel)

    open_channel.command(
        "cmd_absent",
        "ui.url",
        {"origin": "https://wms.nowhere.example"},
    )
    answer = open_channel.answer("cmd_absent")
    here = page.url
    page.close()

    assert answer["ok"] is True, answer
    assert answer["result"]["url"] is None, "the run was told it was on the system it asked for"
    assert answer["result"]["elsewhere"] == here, answer
    assert "wms.nowhere.example" not in str(answer["result"]["elsewhere"]), answer


def test_a_run_that_may_not_take_the_screen_is_refused_rather_than_taking_it(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The page to be photographed is behind the one the operator is working
    in. Somebody typing at 3pm while a schedule fires behind them must not have
    their tab change under their hands, so the command is refused."""
    open_channel, page = _dial(browser, stub, channel)
    api_url, _ = stub
    inbox = browser.new_page()
    inbox.goto(api_url.replace("127.0.0.1", "localhost"))

    open_channel.command("cmd_hidden", "screenshot", {"inline": True, "origin": api_url})
    answer = open_channel.answer("cmd_hidden", timeout=30.0)
    inbox.close()
    page.close()

    assert answer["ok"] is False
    assert answer["error"]["kind"] == "focus_not_permitted", answer


def test_a_run_the_operator_is_watching_brings_its_page_forward(
    browser: Any, stub: Any, channel: Any
) -> None:
    """The other side of the same decision.

    With `allow_focus`, the tab on the run's origin is brought to the front and
    photographed -- which is the only way the rung that looks can work at all
    when the operator has since clicked somewhere else. The picture and the
    coordinates beside it come from that page, not from whatever was in front.
    """
    open_channel, page = _dial(browser, stub, channel)
    api_url, _ = stub
    inbox = browser.new_page()
    inbox.goto(api_url.replace("127.0.0.1", "localhost"))

    open_channel.command(
        "cmd_forward",
        "screenshot",
        {"inline": True, "origin": api_url, "allow_focus": True},
        deadline_ms=30_000,
    )
    answer = open_channel.answer("cmd_forward", timeout=40.0)
    inbox.close()
    page.close()

    assert answer["ok"] is True, answer
    assert base64.b64decode(answer["result"]["image_base64"]).startswith(PNG_MAGIC)
    assert "Client Code" in answer["result"]["text_digest"], (
        "the digest came from a page other than the one brought forward"
    )


def test_the_operator_can_delete_the_last_hour_from_their_own_screen(
    browser: Any, stub: Any, purges: list[str]
) -> None:
    """The control `docs/10` and ADR 008 promise, on the screen it was promised
    on, doing both halves of what it says.

    Both halves matter. The server forgets the hour, and the queue on this
    device is emptied -- what is sitting here has not reached the server yet, so
    deleting it there and leaving it here would upload the deleted hour on the
    next tick.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    page = _drive(browser, api_url)
    page.wait_for_function("() => window.__done === true", timeout=15_000)

    options = browser.new_page()
    options.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    # Twice, because deleting an hour of somebody's work is not one stray click.
    options.click("#purge")
    assert "Really" in options.text_content("#purge"), "the button deleted without asking"
    options.click("#purge")
    options.wait_for_function(
        """() => document.getElementById('purged').textContent.includes('deleted')""",
        timeout=15_000,
    )

    said = options.text_content("#purged")
    options.close()

    assert purges, "the button said it deleted and asked the backend for nothing"
    assert "since=" in purges[0], f"a purge with no window would delete everything: {purges[0]}"
    assert "34 events" in said and "5 screenshots" in said, (
        f"the operator was not told what went: {said!r}"
    )

    # The hour it deleted does not arrive a minute later.
    _flush(browser, worker)
    page.close()
    assert not batches, "the queue survived the purge and uploaded the deleted hour"


def _panel(context: Any, worker: Any) -> Any:
    """The side panel, opened as a page. Chrome docks it beside a tab in real
    use; a test cannot dock it, and the panel is written to find the ordinary
    page in its window either way."""
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/panel/panel.html")
    return page


def test_the_panel_trades_the_operators_tab_for_the_console(browser: Any, stub: Any) -> None:
    """The console used to be framed inside the panel, behind a credential
    handshake (`sro.ready` / `sro.credential` / `sro.credential.ok`) needed
    because Chrome partitions storage for framed contexts and the console
    could not otherwise see its own token. That frame is gone -- a 360-pixel
    console behind a handshake, for a screen that is a full-width application
    -- and `service-worker.js`'s `panel-console` handler says why in its own
    comment: "the token no longer leaves this worker for the panel at all".

    So there is no credential left to prove arrived. What is left of the
    contract is that pressing the menu item really trades a real tab for the
    console's real address, through the extension's own sign-in and a real
    `chrome.tabs` call -- `panel.test.mjs`'s "Open the console here puts the
    console in this tab, and Console ↗ in a new one" already proves the press
    dispatches the right action against a double for `chrome.tabs`; this is
    the other half, that Chrome actually obeys it.
    """
    api_url, _ = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url, console_url=api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    system = browser.new_page()
    system.goto(api_url)

    panel = _panel(browser, worker)
    panel.locator(".disc").click()
    panel.get_by_role("button", name="Open the console here").click()

    system.wait_for_url(f"{api_url}/console", timeout=15_000)
    assert system.locator("h1").text_content() == "Console", (
        "the tab beside the panel was not traded for the console"
    )
    panel.close()
    system.close()


def test_the_panel_opens_the_console_in_a_new_tab_when_asked_there(browser: Any, stub: Any) -> None:
    """The other half of the same menu: "Console ↗" leaves the operator's tab
    alone and opens a tab of its own, real `chrome.tabs.create` and all.
    """
    api_url, _ = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url, console_url=api_url)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    system = browser.new_page()
    system.goto(api_url)

    panel = _panel(browser, worker)
    panel.locator(".disc").click()
    with browser.expect_page(timeout=15_000) as opened:
        panel.get_by_role("button", name="Console ↗").click()
    console_tab = opened.value
    console_tab.wait_for_url(f"{api_url}/console", timeout=15_000)

    assert console_tab.locator("h1").text_content() == "Console", (
        "Console ↗ did not open the console in a new tab"
    )
    assert system.url.rstrip("/") == api_url, "the operator's own tab was navigated away from"
    console_tab.close()
    panel.close()
    system.close()


def test_the_panel_can_stop_a_run_that_is_driving_this_browser(
    browser: Any, stub: Any, channel: Any
) -> None:
    """A run performing in somebody's own browser has to be stoppable while it
    happens. What is already inside the page finishes — nothing can recall it —
    so this stops the next step, which is what the button says."""
    open_channel, page = _dial(browser, stub, channel)
    panel = _panel(browser, worker := _service_worker(browser))
    assert worker is not None

    open_channel.command("cmd_first", "ui.url", {}, run_id="run_stoppable")
    assert open_channel.answer("cmd_first")["ok"] is True

    performing = panel.evaluate(
        """async () => (await chrome.runtime.sendMessage({kind: "status"})).performing"""
    )
    assert performing and performing["runId"] == "run_stoppable", (
        f"the panel could not see the run it is supposed to stop: {performing}"
    )

    panel.evaluate(
        """async () => await chrome.runtime.sendMessage(
             {kind: "abort-run", runId: "run_stoppable"})"""
    )

    open_channel.command("cmd_after", "ui.url", {}, run_id="run_stoppable")
    answer = open_channel.answer("cmd_after")
    panel.close()
    page.close()

    assert answer["ok"] is False
    assert answer["error"]["kind"] == "aborted", answer


def test_the_panel_offers_the_job_that_starts_on_the_system_in_front_of_it(
    browser: Any, stub: Any, shape_queries: list[str]
) -> None:
    """ "Jobs you keep doing *here*" is a different question from "jobs you keep
    doing", and it is the only one the console cannot ask.

    **Rewritten 2026-09-19, and the rewrite is the finding.** This asked the
    same question of `#candidates li` -- the mining pipeline's list, which the
    panel dropped along with the offers behind it (`candidatesFor`: "Dropped
    where it is read"). Nothing served `/v1/shapes` in this stub, so no offer
    could arrive in a real Chrome at all, and six tests here had been failing
    ever since without anybody reading them.
    """
    api_url, _ = stub
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    system = browser.new_page()
    system.goto(api_url)
    _watch(browser, worker, system)
    system.goto(api_url)
    panel = _panel(browser, worker)

    # `#cards`, which is Home. An offer is the truest thing on Home and was
    # moved there from the conversation on 2026-09-16, when splitting the panel
    # in two left the card a person was waiting to press behind the other tab.
    card = panel.locator("#cards li[data-kind='nudge']").first
    card.wait_for(timeout=15_000)
    shown = panel.locator("#cards li[data-kind='nudge']").all_text_contents()
    panel.close()
    system.close()

    assert shape_queries, f"the panel asked for no jobs at all: {shape_queries}"
    assert len(shown) == 1, f"something else was offered here too: {shown}"
    assert "Adjust an LPN quantity" in shown[0]
    # And what one press would write, which is what item 6 put on this card:
    # a person pressing yes is agreeing to a record being made in a warehouse.
    assert "create an orders record" in shown[0], shown[0]


def test_pressing_yes_on_the_card_starts_the_run_the_card_described(
    browser: Any, stub: Any, rig_presses: list[dict[str, Any]]
) -> None:
    """The one press this product is for: a person reads a card and a warehouse
    is written to.

    Nothing in this suite watched it happen. The chain test that used to --
    `test_offering_to_do_the_work.py` -- pressed the mining pipeline's card,
    and that card and the whole pipeline behind it are gone; deleting it on
    2026-09-19 left the gap this fills. Every half is tested elsewhere (the
    card in `panel.test.mjs`, the body in `offering-worker.test.mjs`, the
    refusals in `test_start_workflow_run.py`) and none of them presses a real
    button in a real `chrome.runtime.sendMessage` round trip.
    """
    api_url, _ = stub
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    system = browser.new_page()
    system.goto(api_url)
    _watch(browser, worker, system)
    system.goto(api_url)
    panel = _panel(browser, worker)

    card = panel.locator("#cards li[data-kind='nudge']").first
    card.wait_for(timeout=15_000)
    card.get_by_role("button", name="Yes, do it").click()

    until = time.time() + 15.0
    while time.time() < until and not rig_presses:
        time.sleep(0.2)
    panel.close()
    system.close()

    assert rig_presses, "the press started nothing"
    [press] = rig_presses
    assert press["workflow_id"] == "wfl_lpn"
    # Live, and watched: the press came from an open panel, so the run does the
    # job on the screen rather than replaying the call the demonstration made.
    assert press["live"] is True
    assert press["watched"] is True
    assert press["device_id"] == "dev_browsertest", press
    # `matched`, and never `from_step`: `k` counts shape entries and a step is
    # several of them. Sent as a step count it marked steps done that nobody
    # did.
    assert "from_step" not in press, press
    assert press["matched"] == 0, press
    # Who authorised it is read off the credential. A body that says so is a
    # signature nobody checked.
    assert "started_by" not in press, press


def test_the_screen_a_step_carries_is_the_page_the_operator_acted_on(
    browser: Any, stub: Any
) -> None:
    """The screen outline rides on the gesture record it was taken for, read
    in the capture phase before the click does anything -- so it has to be
    the screen the operator was looking at when they decided to act.

    Taken after the click, a step that navigates would carry the
    *destination* page, and a field would be looked for on a page where it
    does not exist. Through the real extension, so the worker's queue and
    upload carry `outlines` unchanged; no debugger is involved.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    page = browser.new_page()
    page.goto(api_url)
    page.reload()
    page.evaluate(
        """([url]) => {
             const link = document.createElement('a');
             link.id = 'go';
             link.href = url;
             link.textContent = 'Go elsewhere';
             document.body.append(link);
           }""",
        [f"{api_url}/elsewhere"],
    )
    _watch(browser, worker, page)

    page.click("#client")
    page.click("#go")
    page.wait_for_url(f"{api_url}/elsewhere", timeout=15_000)
    _flush_until_a_click_arrives(browser, worker, batches, "go")
    page.close()

    gestures = [
        event["gesture"]
        for batch in batches
        for event in batch["events"]
        if event["kind"] == "gesture"
    ]
    (go,) = _clicks_on(batches, "go")
    upto = gestures[: gestures.index(go["gesture"]) + 1]
    outlines = [screen for gesture in upto for screen in gesture.get("outlines") or []]
    assert outlines, "the passive path carried no screen outline at all"
    assert outlines[-1]["headings"] == ["Depot"], (
        "the screen a click was made on is the page the operator clicked on"
    )
    assert "Save" in outlines[-1]["buttons"]
    assert "Only here" not in json.dumps(outlines), "the destination page was sent as the screen"


def test_a_tab_nobody_pointed_at_is_not_evidence(browser: Any, stub: Any) -> None:
    """Capture begins where the operator says it does, and nowhere else.

    Before this, capture was decided by the tenant's host list, which cannot
    tell the tab somebody is working in from the console tab polling this
    backend beside it -- and on a real day the console won: 97% of what was
    stored was this system watching itself, mined into tasks like "Create
    finish on localhost".

    Both halves matter. Silence in an unwatched tab is only worth something if
    the same actions in the same tab, once pointed at, do produce evidence.
    """
    api_url, batches = stub
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    page = browser.new_page()
    page.goto(api_url)
    page.fill("#client", CLIENT_CODE)
    page.click("#save")
    page.wait_for_function("() => window.__done === true", timeout=15_000)
    _flush(browser, worker)

    assert not [event for batch in batches for event in batch["events"]], (
        "a tab nobody asked to be watched produced evidence"
    )

    _watch(browser, worker, page)
    page.reload()
    page.fill("#client", CLIENT_CODE)
    page.click("#save")
    page.wait_for_function("() => window.__done === true", timeout=15_000)
    _flush(browser, worker)
    page.close()

    events = [event for batch in batches for event in batch["events"]]
    assert events, "the tab the operator pointed at produced nothing"
    assert CLIENT_CODE in json.dumps(batches), "the work in a watched tab was not captured"


def test_the_panel_watches_the_tab_it_is_docked_beside(browser: Any, stub: Any) -> None:
    """The panel is the surface that can answer "which tab": it is docked
    beside the one being asked about. Pressing the button there is the whole
    act -- no host is typed, and nothing is inferred from what is open."""
    api_url, _ = stub
    worker = _service_worker(browser)
    _sign_in(browser, worker, api_url)

    work = browser.new_page()
    work.goto(f"{api_url}/work")
    work.bring_to_front()
    beside = worker.evaluate(
        "async () => (await chrome.tabs.query({active: true, lastFocusedWindow: true}))[0]?.id"
    )

    panel = _panel(browser, worker)
    before = panel.evaluate("""async () => await chrome.runtime.sendMessage({kind: "status"})""")
    after = panel.evaluate(
        """async (tabId) => {
             await chrome.runtime.sendMessage({kind: "watch-tab", tabId});
             return await chrome.runtime.sendMessage({kind: "status"});
           }""",
        beside,
    )
    stopped = panel.evaluate(
        """async (tabId) => {
             await chrome.runtime.sendMessage({kind: "unwatch-tab", tabId});
             return await chrome.runtime.sendMessage({kind: "status"});
           }""",
        beside,
    )
    panel.close()
    work.close()

    assert before["watched"] == [], "something was being watched before anybody said so"
    assert [entry["tabId"] for entry in after["watched"]] == [beside], (
        f"the panel watched something other than the tab beside it: {after['watched']}"
    )
    assert stopped["watched"] == [], "stopping did not stop"


def test_watching_a_tab_that_was_already_open_needs_no_reload(browser: Any, stub: Any) -> None:
    """Pressing "watch this tab" has to work on the tab in front of you.

    Registration only injects on the *next* navigation, so a tab opened before
    the extension had scripts for it -- before sign-in, or before the extension
    was last reloaded -- runs nothing of ours. The panel said "watching this
    tab" and nothing whatever was recorded, which is the worst of both: a
    surface claiming to observe, and no evidence.

    The page is opened before sign-in here, which is the same condition as a
    tab that outlived an extension reload, and it is never reloaded: an
    operator halfway through a form does not get to lose it.
    """
    api_url, batches = stub
    worker = _service_worker(browser)

    page = browser.new_page()
    page.goto(api_url)  # no registration exists yet: nothing of ours is in here

    _sign_in(browser, worker, api_url)
    _watch(browser, worker, page)

    page.fill("#client", CLIENT_CODE)
    page.click("#save")
    page.wait_for_function("() => window.__done === true", timeout=15_000)
    _flush(browser, worker)
    page.close()

    typed = [
        event
        for batch in batches
        for event in batch["events"]
        if event["kind"] == "gesture" and event["gesture"].get("value") == CLIENT_CODE
    ]
    assert typed, "watching an already-open tab recorded nothing"
    assert len(typed) == 1, f"the gesture was recorded {len(typed)} times"
    assert any(
        event["kind"] == "request" and "/api/orders" in event["request"]["url"]
        for batch in batches
        for event in batch["events"]
    ), "the page's own calls were not captured in a tab injected after the fact"

    # And pressing it twice, which an operator does the moment they are not
    # sure it took. Each press injects; without a guard in the frame that is
    # two relays, two copies of every gesture, two of every call.
    batches.clear()
    second = browser.new_page()
    second.goto(f"{api_url}/again")
    _watch(browser, worker, second)
    _watch(browser, worker, second)
    second.fill("#client", CLIENT_CODE)
    second.click("#save")
    second.wait_for_function("() => window.__done === true", timeout=15_000)
    _flush(browser, worker)
    second.close()

    again = [
        event
        for batch in batches
        for event in batch["events"]
        if event["kind"] == "gesture" and event["gesture"].get("value") == CLIENT_CODE
    ]
    assert len(again) == 1, f"watching twice recorded the same gesture {len(again)} times"

    # And the calls, which is the half the gesture assertion above never
    # covered: a second relay in the frame forwards the *same* page-realm
    # record a second time, so the duplicate carries an identical request_id
    # rather than looking like a second call the page made.
    ids = [
        event["request"]["request_id"]
        for batch in batches
        for event in batch["events"]
        if event["kind"] == "request"
    ]
    assert len(ids) == len(set(ids)), "watching twice recorded the same call twice"
