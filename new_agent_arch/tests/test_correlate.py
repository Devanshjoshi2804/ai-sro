import copy
from datetime import UTC, datetime

from rig.correlate import ATTRIBUTION_SECONDS, correlate, system_of
from rig.wire import Batch
from tests.fixtures import BATCH, GESTURE_TYPE, REQUEST_POST

TENANT = "new"


def _rfc3339(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace("+00:00", "Z")


def _batch(events: list[dict]) -> Batch:
    return Batch.model_validate({**copy.deepcopy(BATCH), "events": copy.deepcopy(events)})


def _request(started_at: str, request_id: str, tab_id: int) -> dict:
    event = copy.deepcopy(REQUEST_POST)
    event["request"]["started_at"] = started_at
    event["request"]["request_id"] = request_id
    event["tab_id"] = tab_id
    return event


def test_the_whole_committed_batch_correlates() -> None:
    gestures, orphans = correlate(Batch.model_validate(BATCH), TENANT)

    assert len(gestures) == 7
    assert sum(len(g.requests) for g in gestures) + len(orphans) == 5


def test_a_call_belongs_to_the_gesture_that_caused_it() -> None:
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    call = _request(_rfc3339(at + 0.2), "r1", tab)

    gestures, orphans = correlate(_batch([GESTURE_TYPE, call]), TENANT)

    assert len(gestures[0].requests) == 1
    assert orphans == []


def test_a_call_before_any_gesture_is_an_orphan_and_is_kept() -> None:
    """Orphans are stored, never dropped: a background poll is evidence."""
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    early = _request(_rfc3339(at - 60), "r1", tab)

    gestures, orphans = correlate(_batch([early, GESTURE_TYPE]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_long_after_a_gesture_is_not_attributed_to_it() -> None:
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    late = _request(_rfc3339(at + ATTRIBUTION_SECONDS + 1), "r1", tab)

    gestures, orphans = correlate(_batch([GESTURE_TYPE, late]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_never_crosses_into_another_tab() -> None:
    """The request event carries its own tab; nothing is guessed from the host."""
    at = GESTURE_TYPE["gesture"]["at"]
    other_tab = _request(_rfc3339(at + 0.2), "r1", GESTURE_TYPE["tab_id"] + 1)

    gestures, orphans = correlate(_batch([GESTURE_TYPE, other_tab]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_goes_to_the_most_recent_gesture_in_its_tab() -> None:
    tab = GESTURE_TYPE["tab_id"]
    first = copy.deepcopy(GESTURE_TYPE)
    first["gesture"]["at"] = 1000.0
    second = copy.deepcopy(GESTURE_TYPE)
    second["gesture"]["at"] = 1002.0
    call = _request(_rfc3339(1004.0), "r1", tab)

    gestures, _ = correlate(_batch([first, second, call]), TENANT)
    owned = {g.at: len(g.requests) for g in gestures}

    assert owned[1002.0] == 1
    assert owned[1000.0] == 0


def test_events_need_not_arrive_sorted() -> None:
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    call = _request(_rfc3339(at + 0.2), "r1", tab)

    gestures, _ = correlate(_batch([call, GESTURE_TYPE]), TENANT)

    assert len(gestures[0].requests) == 1


def test_the_system_is_the_scheme_and_host() -> None:
    assert system_of("https://wms.example/data/WM/wm/suppliers") == "https://wms.example"
    assert system_of("http://127.0.0.1:63319/") == "http://127.0.0.1:63319"
    assert system_of(None) is None
