"""A watch, evaluated in a real Chrome against a real mail on a real page.

Everything about a watch that could go quietly wrong needs a browser to prove:
that a content script registered on a mailbox is registered on *that* host and
no other, that a policy change arriving on a heartbeat does not take it down
with the recorder, and that what leaves the machine when a mail matches is the
values and nothing else. None of those can be shown in a vm sandbox -- they are
questions about Chrome's registration and about the bytes on the wire.

`watch.test.mjs` holds the other half: that the browser's matcher decides the
same way `Watch.matches` does, on the cases the domain's own tests use.
"""

from __future__ import annotations

import json
import time
from typing import Any

import pytest

pytestmark = pytest.mark.browser

SENDER = "dispatch@supplier.test"
SUBJECT = "Short shipment on PO 4471"
SHIPMENT = "SH-4471"

WATCH = {
    "host": "127.0.0.1",
    "terms": [
        {"field": "sender", "contains": SENDER},
        # Lower case, against a subject that is not: an operator does not type
        # a subject the way it was written.
        {"field": "subject", "contains": "short ship"},
    ],
    "values": [
        {
            "name": "shipment_id",
            "where": {
                "strategy": "css_path",
                "query": "span.shipment-ref",
                "within": "div.mail-body",
                "visible_only": True,
            },
        }
    ],
    "sender_at": {
        "strategy": "css_path",
        "query": "span.from-address",
        "within": None,
        "visible_only": True,
    },
    "subject_at": {
        "strategy": "css_path",
        "query": "h1.subject",
        "within": None,
        "visible_only": True,
    },
}

TRIGGER = {
    "id": "trg-short-ship",
    "skill_id": "skl-short-ship",
    "kind": "watch",
    "cron": None,
    "timezone": "UTC",
    "parameters": {},
    "from_message": ["shipment_id"],
    "watch": WATCH,
    "device_id": "dev_browsertest",
    "medium": "extension",
    "enabled": True,
    "writes": False,
    "authorized_by": None,
    "requires_confirmation": True,
    "may_take_focus": False,
    "created_by": "lena",
    "created_at": "2026-08-29T09:00:00+00:00",
    "last_fired_at": None,
    "last_run_id": None,
    "disabled_reason": None,
    "inbound_token": None,
}


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


def _registered(context: Any, worker: Any) -> list[dict[str, Any]]:
    page = _extension_page(context, worker)
    scripts: list[dict[str, Any]] = page.evaluate(
        "async () => await chrome.scripting.getRegisteredContentScripts()"
    )
    page.close()
    return scripts


def _watch_script(context: Any, worker: Any) -> dict[str, Any] | None:
    return next((s for s in _registered(context, worker) if s["id"] == "sro-watch"), None)


def _wait_for(what: list[Any], timeout: float = 15.0) -> list[Any]:
    until = time.time() + timeout
    while time.time() < until and not what:
        time.sleep(0.2)
    return what


@pytest.fixture
def armed(browser: Any, stub: Any, watching: Any) -> Any:
    """A browser signed in, holding one watch on the stub's own host."""
    api_url, _ = stub
    watching([TRIGGER])
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start: {status}"
    return worker


def test_a_mail_that_matches_puts_up_the_values_and_nothing_else(
    browser: Any, stub: Any, armed: Any, matched: list[dict[str, Any]]
) -> None:
    """The one request a match makes, judged on the bytes it sent.

    The subject and the sender were read, compared and forgotten in the page.
    They are what decided this, and they are absent from what left the machine
    -- which is the whole promise a watch makes about a mailbox nobody agreed
    to have observed.
    """
    api_url, batches = stub
    page = browser.new_page()
    page.goto(f"{api_url}/mail")

    _wait_for(matched)
    page.close()

    assert matched, "the browser never recognised the mail in front of it"
    [offer] = matched
    assert offer["values"] == {"shipment_id": SHIPMENT}
    assert offer["path"] == "/v1/agents/dev_browsertest/watches/trg-short-ship/matched"
    assert SENDER not in offer["raw"], offer["raw"]
    assert "Short shipment" not in offer["raw"], offer["raw"]
    # And nothing was captured either: a mail host is excluded from observation
    # on purpose and a watch is not a way around that.
    assert not [event for batch in batches for event in batch["events"]], batches


def test_a_mail_open_on_screen_is_offered_once_rather_than_once_a_second(
    browser: Any, stub: Any, armed: Any, matched: list[dict[str, Any]]
) -> None:
    """A mail client mutates its DOM constantly and the rule is re-evaluated
    every time the page settles. Somebody reading a mail for a minute is one
    offer, not sixty."""
    api_url, _ = stub
    page = browser.new_page()
    page.goto(f"{api_url}/mail")
    _wait_for(matched)

    for _ in range(5):
        page.evaluate("() => document.querySelector('div.mail-body').append(' ')")
        time.sleep(0.3)
    time.sleep(1.0)
    page.close()

    assert len(matched) == 1, matched


def test_a_page_on_a_host_with_no_watch_is_untouched(
    browser: Any, stub: Any, armed: Any, matched: list[dict[str, Any]]
) -> None:
    """The same mail, at the same stub, on a hostname no watch names.

    Registration is the enforcement, as it is for capture: the script is not
    put on that page at all, so there is nothing there to filter afterwards.
    """
    api_url, _ = stub
    script = _watch_script(browser, armed)

    assert script is not None, "the watch was never registered anywhere"
    # Chrome hands the patterns back in its own order, so this is the set.
    assert set(script["matches"]) == {"*://127.0.0.1/*", "*://*.127.0.0.1/*"}

    elsewhere = browser.new_page()
    elsewhere.goto(f"{api_url.replace('127.0.0.1', 'localhost')}/mail")
    time.sleep(2.0)
    elsewhere.close()

    assert matched == [], "a mail was read on a host that has no watch on it"


def test_a_policy_change_does_not_quietly_stop_the_watching(
    browser: Any, stub: Any, armed: Any, matched: list[dict[str, Any]]
) -> None:
    """The bug this shape is built to avoid.

    A policy arrives on a heartbeat and the recorder's registration is torn
    down and rebuilt for it. The watch script is a third id and must survive
    that: withdrawing it here would stop the watching with nothing said -- the
    panel still lists the watch, the mails simply stop matching, and the first
    person to notice is whoever was waiting for a mail to be acted on.
    """
    api_url, _ = stub
    page = _extension_page(browser, armed)
    # A new policy, and then the path that applies one. `settle` is what
    # re-registers the recorder, and it is the only thing that ever withdraws
    # a registration outside sign-out.
    page.evaluate(
        """async (policy) => {
             await chrome.storage.local.set({"sro.policy": policy});
             await chrome.runtime.sendMessage({kind: "set-paused", paused: false});
           }""",
        {
            "version": 2,
            "capture_enabled": True,
            "exclude_hosts": ["localhost", "mail.google.com"],
            "include_hosts": [],
            "capture_screenshots": True,
            "screenshot_max_per_minute": 3,
            "capture_response_bodies": True,
            "max_body_bytes": 262144,
            "daily_budget_bytes": 524288000,
            "retention_days": 30,
        },
    )
    page.close()

    assert _watch_script(browser, armed) is not None, (
        "a policy change took the watch script down with the recorder"
    )
    mail = browser.new_page()
    mail.goto(f"{api_url}/mail")
    _wait_for(matched)
    mail.close()

    assert [offer["values"] for offer in matched] == [{"shipment_id": SHIPMENT}]


def test_signing_out_stops_the_watching(
    browser: Any, stub: Any, armed: Any, matched: list[dict[str, Any]]
) -> None:
    """The other direction, which the same split has to keep working: the
    operator leaves, and their mail rules leave the machine with them."""
    api_url, _ = stub
    page = _extension_page(browser, armed)
    page.evaluate("""async () => await chrome.runtime.sendMessage({kind: "sign-out"})""")
    held = page.evaluate("""async () => await chrome.storage.local.get("sro.watches")""")
    page.close()

    assert _watch_script(browser, armed) is None, "a signed-out browser is still in a mailbox"
    assert held == {}, held

    mail = browser.new_page()
    mail.goto(f"{api_url}/mail")
    time.sleep(2.0)
    mail.close()

    assert matched == [], json.dumps(matched)
