"""The rig's protocol arrives whole: a batch parses, one bad event does not
cost the batch, and the correlator hands the domain what the arithmetic reads."""

from typing import cast

from sro.application.capture.rig_wire import parse_batch
from sro.application.observation.correlate import correlate, system_of
from tests.unit.domain.rig.conftest import BATCH

# BATCH is typed `dict[str, object]` so its bytes can hold any event shape a
# test wants to throw at it; `events` is always the list it looks like.
_events = cast("list[object]", BATCH["events"])


def test_the_measured_batch_parses_and_correlates() -> None:
    batch, rejected = parse_batch(BATCH)
    assert rejected == ()
    gestures, _requests, _pages, _dropped = correlate(batch, "acme")
    assert len(gestures) == 7
    assert {g.action.kind for g in gestures} == {"type", "select", "upload", "click", "press"}
    typed = next(g for g in gestures if g.action.value == "ACME-4471")
    assert typed.action.target and typed.action.target.name == "Client Code"
    assert typed.system == "http://127.0.0.1:63319"


def test_one_unparseable_event_does_not_cost_the_batch() -> None:
    raw = dict(BATCH, events=[*_events, {"kind": "gesture", "gesture": {"kind": "wave"}}])
    batch, rejected = parse_batch(raw)
    assert len(rejected) == 1 and rejected[0].index == len(_events)
    assert len(batch.events) == len(_events)


def test_system_of_is_the_origin() -> None:
    assert system_of("https://wms.example:8443/a/b?c=1") == "https://wms.example:8443"
    assert system_of(None) is None
    assert system_of("about:blank") is None
