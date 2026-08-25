"""Drive a real page with the real extension and read what it uploaded.

The assertions are on the bytes the extension actually sent, not on what it
was meant to send: `docs/10-security-and-data.md` asks for the password proof
to be made against the stored bytes rather than against intent, and until this
existed there was nowhere that could be done.
"""

from __future__ import annotations

import base64
import json
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


def _sign_in(context: Any, worker: Any, api_url: str) -> dict[str, Any]:
    """Through the extension's own message API, not by writing storage."""
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    status: dict[str, Any] = page.evaluate(
        """async ([apiUrl]) => await chrome.runtime.sendMessage(
             {kind: "sign-in", apiUrl, token: "test-token", label: "browser-test"})""",
        [api_url],
    )
    page.close()
    return status


def _drive(context: Any, url: str) -> Any:
    page = context.new_page()
    page.goto(url)
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
