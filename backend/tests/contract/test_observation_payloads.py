"""What the extension sends must be what the domain accepts.

The extension is built in `new-chrome-extension/` by somebody who does not edit
this codebase, against `docs/14-extension-protocol.md`. This is the only place
the two halves meet before they meet in production: the golden payloads that
directory captures from a real session are parsed here with the same functions
the server-side capture adapter uses, and every domain invariant is checked.

It skips itself while there are no fixtures, so an empty directory does not stop
the backend. A fixture that exists and does not parse fails the build.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from sro.application.capture.decode import epoch_to_datetime, to_ax_graph, to_input_action
from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.events import InputAction
from sro.domain.recording.network import CapturedRequest
from sro.domain.recording.state import PageEvent

FIXTURES = Path(__file__).resolve().parents[3] / "new-chrome-extension" / "fixtures"

# Files that live in the fixtures directory but are not extension output, so
# neither this suite nor the drift test in `tests/browser` may treat them as
# golden payloads.
#
#   shape-identity.json -- a JSON *array* of control-identity cases, not a
#   protocol event. It is the shared golden fixture for `target_identity`,
#   read by `tests/unit/domain/rig/test_shape.py` on the Python side and by
#   the generated twin `new-chrome-extension/src/background/shape.generated.js`
#   on the browser side. Those tests cover it; do not re-assert it here.
#
# `test_the_named_exclusions_still_exist` below stops this set outliving the
# files it names.
NOT_EXTENSION_OUTPUT = frozenset({"shape-identity.json"})

_REQUEST = TypeAdapter(CapturedRequest)
_PAGE_EVENT = TypeAdapter(PageEvent)


def _fixtures() -> list[Path]:
    if not FIXTURES.is_dir():
        return []
    return sorted(p for p in FIXTURES.glob("*.json") if p.name not in NOT_EXTENSION_OUTPUT)


def _parse_event(event: dict[str, Any]) -> InputAction | CapturedRequest | AxGraph | PageEvent:
    """The dispatch the ingest use case will do, done here against the raw file."""
    kind = event.get("kind")
    if kind == "gesture":
        gesture = event["gesture"]
        epoch_to_datetime(float(gesture["at"]))  # the recorder's float seconds, not RFC 3339
        return to_input_action(gesture)
    if kind == "request":
        return _REQUEST.validate_python(event["request"])
    if kind == "page":
        return _PAGE_EVENT.validate_python(
            {
                "at": event["at"],
                "kind": event["page_kind"],
                "url": event.get("url"),
                "detail": event.get("detail"),
            }
        )
    if kind == "snapshot":
        taken_at = datetime.fromisoformat(event["taken_at"]).astimezone(UTC)
        graph = to_ax_graph(event["snapshot"], url=event["url"], taken_at=taken_at)
        assert graph is not None, "an accessibility snapshot with no usable root"
        return graph
    raise AssertionError(f"the protocol declares no event kind {kind!r}")


@pytest.mark.skipif(not _fixtures(), reason="the extension has captured no fixtures yet")
@pytest.mark.parametrize("path", _fixtures(), ids=lambda p: p.stem)
def test_every_captured_payload_parses_into_the_domain(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if path.stem.startswith("batch"):
        assert payload["batch_id"].startswith("bat_"), "a batch id the backend cannot key on"
        assert payload["mode"] == "passive"
        assert payload["events"], "a batch worth uploading has events in it"
        for event in payload["events"]:
            _parse_event(event)
        return

    if path.stem.startswith("command-"):
        assert payload["command_id"].startswith("cmd_")
        assert isinstance(payload["ok"], bool)
        assert ("result" in payload) is payload["ok"], "a reply carries a result or an error"
        return

    _parse_event(payload)


@pytest.mark.skipif(not FIXTURES.is_dir(), reason="the extension has captured no fixtures yet")
def test_the_named_exclusions_still_exist() -> None:
    """An exclusion that outlives its file protects nothing and hides the next one.

    Without this, `NOT_EXTENSION_OUTPUT` goes on naming a deleted file forever,
    and whoever adds the next non-event fixture gets no signal that the set is
    where it belongs.
    """
    missing = sorted(name for name in NOT_EXTENSION_OUTPUT if not (FIXTURES / name).is_file())

    assert not missing, (
        f"NOT_EXTENSION_OUTPUT names {missing}, which the fixtures directory no longer holds. "
        "Drop the name from the set rather than leaving it to shadow a future fixture."
    )


@pytest.mark.skipif(
    not (FIXTURES / "gesture-secret.json").is_file(),
    reason="the extension has captured no credential field yet",
)
def test_a_credential_field_reaches_the_backend_with_nothing_in_it() -> None:
    payload = json.loads((FIXTURES / "gesture-secret.json").read_text(encoding="utf-8"))
    gesture = payload["gesture"]

    action = to_input_action(gesture)

    assert action.secret is True
    assert action.value is None
    assert gesture["target"].get("name") is None, "a credential's label may read its own value"
    assert "value" not in gesture["target"].get("attributes", {})
    assert "«redacted»" not in json.dumps(payload), (
        "the value was redacted downstream rather than never captured"
    )


@pytest.mark.skipif(
    not (FIXTURES / "batch-sign-in.json").is_file(),
    reason="the extension has captured no sign-in yet",
)
def test_a_sign_in_reaches_the_backend_as_structure_only() -> None:
    """Spec §5.6, against the bytes a real Chrome uploaded for a real OAuth flow:
    a Microsoft-shaped code box, a page echoing its code into a div and a
    button's label, and a password form.

    What was acted on, the URLs, the page marks and each call's method, URL
    and status are there -- the sign-in chain can still be learned from it.
    No typed value, no tree and no body is.
    """
    batch = json.loads((FIXTURES / "batch-sign-in.json").read_text(encoding="utf-8"))
    events = batch["events"]
    kinds = {event["kind"] for event in events}

    assert all(event.get("sign_in") is True for event in events)
    assert "snapshot" not in kinds, "a tree of a sign-in page was uploaded"
    assert {"gesture", "request", "page"} <= kinds
    for event in events:
        if event["kind"] == "gesture":
            gesture = event["gesture"]
            if gesture["kind"] != "press":
                assert gesture["value"] is None, gesture
            assert gesture["target"]["cssPath"], "what was acted on was not kept"
            assert "value" not in gesture["target"]["attributes"]
        if event["kind"] == "request":
            request = event["request"]
            assert request["request_body"] is None and request["response_body"] is None
            assert request["method"] and request["url"] and request["status"]
        if event["kind"] == "page":
            assert event["url"], "a page mark lost its URL"
    for typed in ("135791", "246802", "424242", "hunter2-not-real", "signin-user-7c1e"):
        assert typed not in json.dumps(batch)
