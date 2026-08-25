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

_REQUEST = TypeAdapter(CapturedRequest)
_PAGE_EVENT = TypeAdapter(PageEvent)


def _fixtures() -> list[Path]:
    return sorted(FIXTURES.glob("*.json")) if FIXTURES.is_dir() else []


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
        assert payload["mode"] in ("passive", "teaching")
        assert payload["events"], "a batch worth uploading has events in it"
        # The one rule that makes teaching evidence evidence: it names the
        # demonstration it belongs to, and ordinary browsing does not. Either
        # one wearing the other's clothes is refused at ingest, and a fixture
        # that got it wrong would be a fixture proving the wrong contract.
        teaching = payload["mode"] == "teaching"
        assert bool(payload.get("recording_id")) is teaching, (
            f"a {payload['mode']} batch with recording_id={payload.get('recording_id')!r}"
        )
        for event in payload["events"]:
            _parse_event(event)
        return

    if path.stem.startswith("command-"):
        assert payload["command_id"].startswith("cmd_")
        assert isinstance(payload["ok"], bool)
        assert ("result" in payload) is payload["ok"], "a reply carries a result or an error"
        return

    _parse_event(payload)


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
