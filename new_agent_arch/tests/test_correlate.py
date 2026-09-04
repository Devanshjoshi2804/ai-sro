import copy
from datetime import UTC, datetime

from rig.correlate import ATTRIBUTION_SECONDS, correlate, system_of
from rig.wire import Batch
from tests.fixtures import BATCH, GESTURE_TYPE, PAGE_NAVIGATED, REQUEST_POST, SNAPSHOT

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
    gestures, orphans, _, _ = correlate(Batch.model_validate(BATCH), TENANT)

    assert len(gestures) == 7
    assert sum(len(g.requests) for g in gestures) + len(orphans) == 5


def test_a_call_belongs_to_the_gesture_that_caused_it() -> None:
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    call = _request(_rfc3339(at + 0.2), "r1", tab)

    gestures, orphans, _, _ = correlate(_batch([GESTURE_TYPE, call]), TENANT)

    assert len(gestures[0].requests) == 1
    assert orphans == []


def test_a_call_before_any_gesture_is_an_orphan_and_is_kept() -> None:
    """Orphans are stored, never dropped: a background poll is evidence."""
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    early = _request(_rfc3339(at - 60), "r1", tab)

    gestures, orphans, _, _ = correlate(_batch([early, GESTURE_TYPE]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_long_after_a_gesture_is_not_attributed_to_it() -> None:
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    late = _request(_rfc3339(at + ATTRIBUTION_SECONDS + 1), "r1", tab)

    gestures, orphans, _, _ = correlate(_batch([GESTURE_TYPE, late]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_never_crosses_into_another_tab() -> None:
    """The request event carries its own tab; nothing is guessed from the host."""
    at = GESTURE_TYPE["gesture"]["at"]
    other_tab = _request(_rfc3339(at + 0.2), "r1", GESTURE_TYPE["tab_id"] + 1)

    gestures, orphans, _, _ = correlate(_batch([GESTURE_TYPE, other_tab]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_goes_to_the_most_recent_gesture_in_its_tab() -> None:
    tab = GESTURE_TYPE["tab_id"]
    first = copy.deepcopy(GESTURE_TYPE)
    first["gesture"]["at"] = 1000.0
    second = copy.deepcopy(GESTURE_TYPE)
    second["gesture"]["at"] = 1002.0
    call = _request(_rfc3339(1004.0), "r1", tab)

    gestures, _, _, _ = correlate(_batch([first, second, call]), TENANT)
    owned = {g.at: len(g.requests) for g in gestures}

    assert owned[1002.0] == 1
    assert owned[1000.0] == 0


def test_events_need_not_arrive_sorted() -> None:
    """`_owner` walks `gestures` in list order and breaks at the first one
    later than the call, so an unsorted list hands a call to the wrong gesture.

    With a single gesture in it, this asserted nothing: the sort it is named
    for was a no-op, and deleting `gestures.sort(...)` left it green.
    """
    tab = GESTURE_TYPE["tab_id"]
    early = copy.deepcopy(GESTURE_TYPE)
    early["gesture"]["at"] = 1000.0
    late = copy.deepcopy(GESTURE_TYPE)
    late["gesture"]["at"] = 1002.0
    call = _request(_rfc3339(1002.5), "r1", tab)

    gestures, orphans, _, _ = correlate(_batch([call, late, early]), TENANT)

    assert [gesture.at for gesture in gestures] == [1000.0, 1002.0]
    assert {gesture.at: len(gesture.requests) for gesture in gestures} == {1000.0: 0, 1002.0: 1}
    assert orphans == []


def test_the_system_is_the_scheme_and_host() -> None:
    assert system_of("https://wms.example/data/WM/wm/suppliers") == "https://wms.example"
    assert system_of("http://127.0.0.1:63319/") == "http://127.0.0.1:63319"
    assert system_of(None) is None


def test_the_pages_in_the_committed_batch_are_not_lost() -> None:
    """Both real page events precede the first gesture by 30ms. A page always
    loads before the operator acts on it, so losing those loses every navigation."""
    gestures, _, orphan_pages, _ = correlate(Batch.model_validate(BATCH), TENANT)

    kept = sum(len(g.page_events) for g in gestures)

    assert kept + len(orphan_pages) == 2
    assert kept == 2


def test_a_navigation_belongs_to_the_gesture_it_precedes() -> None:
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), TENANT)
    first = min(gestures, key=lambda g: g.at)

    assert [e.page_kind for e in first.page_events] == ["navigated", "loaded"]


def test_a_page_event_nobody_can_own_is_returned_not_dropped() -> None:
    lonely = copy.deepcopy(PAGE_NAVIGATED)
    lonely["at"] = _rfc3339(GESTURE_TYPE["gesture"]["at"] + 3600)

    gestures, _, orphan_pages, _ = correlate(_batch([GESTURE_TYPE, lonely]), TENANT)

    assert sum(len(g.page_events) for g in gestures) == 0
    assert len(orphan_pages) == 1


def test_a_request_with_no_tab_is_orphaned_not_guessed_at() -> None:
    """Missing evidence means "I cannot prove this belongs there", not
    "attach it to whatever is nearest"."""
    at = GESTURE_TYPE["gesture"]["at"]
    tabless = _request(_rfc3339(at + 0.2), "r1", GESTURE_TYPE["tab_id"])
    tabless["tab_id"] = None

    gestures, orphans, _, _ = correlate(_batch([GESTURE_TYPE, tabless]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1
    assert orphans[0].tab_id is None


def test_an_orphaned_request_keeps_the_tab_it_came_from() -> None:
    at = GESTURE_TYPE["gesture"]["at"]
    late = _request(_rfc3339(at + ATTRIBUTION_SECONDS + 1), "r1", 4242)

    _, orphans, _, _ = correlate(_batch([GESTURE_TYPE, late]), TENANT)

    assert orphans[0].tab_id == 4242


def test_a_snapshot_is_counted_ignored_not_silently_dropped() -> None:
    """Accessibility trees are out of scope for this plan, but a batch of them
    must not answer accepted: 0, rejected: 0 -- which reads as nothing arrived.
    The count is the only way to tell they were there and ignored."""
    gestures, orphans, orphan_pages, snapshots_ignored = correlate(
        _batch([GESTURE_TYPE, SNAPSHOT, SNAPSHOT]), TENANT
    )

    assert snapshots_ignored == 2
    assert len(gestures) == 1
    assert orphans == []
    assert orphan_pages == []
