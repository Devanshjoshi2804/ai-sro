"""Ported from `new_agent_arch/tests/test_correlate.py`. `correlate` now hands
back domain `Call`/`PageMark` values rather than the wire `Request`/`PageEvent`
events it read (see `sro.application.observation.correlate.as_call` /
`as_mark`), so a few assertions read a field off the domain type instead of
the wire one.
"""

import copy
from datetime import UTC, datetime
from typing import Any, cast

from sro.application.capture.rig_wire import Batch
from sro.application.observation.correlate import ATTRIBUTION_SECONDS, correlate, system_of
from sro.domain.observation.gesture import Outline, OutlineField
from sro.domain.observation.outline import last_outline
from sro.infrastructure.db.evidence import _gesture_to_row, _row_to_gesture
from tests.unit.domain.rig.conftest import BATCH

TENANT = "new"

_EVENTS = cast("list[dict[str, Any]]", BATCH["events"])
GESTURE_TYPE: dict[str, Any] = _EVENTS[2]
PAGE_NAVIGATED: dict[str, Any] = _EVENTS[0]
REQUEST_POST: dict[str, Any] = _EVENTS[10]
SNAPSHOT: dict[str, object] = {"kind": "snapshot"}


def _rfc3339(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace("+00:00", "Z")


def _batch(events: list[dict[str, Any]]) -> Batch:
    return Batch.model_validate({**copy.deepcopy(BATCH), "events": copy.deepcopy(events)})


def _request(started_at: str, request_id: str, tab_id: int | None) -> dict[str, Any]:
    event = copy.deepcopy(REQUEST_POST)
    event["request"]["started_at"] = started_at
    event["request"]["request_id"] = request_id
    # The url carries the sequence too, so a test telling two calls apart can
    # read either `.request_id` or `.url` off the resulting `Call`.
    event["request"]["url"] = f"{REQUEST_POST['request']['url']}?seq={request_id}"
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
    assert orphans[0].url == f"{REQUEST_POST['request']['url']}?seq=r1"


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


def test_a_navigation_in_another_tab_is_not_evidence_for_this_gesture() -> None:
    """`_owner`'s tab rule has a named test; `_nearest_owner`'s sibling on the
    page path had none -- the eighth instance of that shape here.

    With the check bypassed, the operator's own mail tab loads 100ms after they
    click in the WMS, and that navigation attaches to the WMS gesture and goes
    to the model as evidence for it.

    The rig's own test goes on to check `trim(gestures[0])["page"] == []` --
    the half of this that reaches the model. `trim` is not ported by this
    task (see the task report's "Left for plan 3"), so that half is dropped
    here; the attribution behaviour itself is not.
    """
    at = GESTURE_TYPE["gesture"]["at"]
    mail = copy.deepcopy(PAGE_NAVIGATED)
    mail["at"] = _rfc3339(at + 0.1)
    mail["url"] = "https://mail.example/inbox"
    mail["page_kind"] = "navigated"
    mail["tab_id"] = GESTURE_TYPE["tab_id"] + 1

    gestures, _, orphan_pages, _ = correlate(_batch([GESTURE_TYPE, mail]), TENANT)

    assert gestures[0].page_events == []
    assert [page.url for page in orphan_pages] == ["https://mail.example/inbox"]


def test_the_calls_a_gesture_caused_are_kept_in_the_order_they_were_made() -> None:
    """`sorted(requests, key=...)`. The batch is whatever order the extension
    flushed its queues in; the list of calls the model is shown as `calls` is a
    sequence it is asked to reason about, and out of order it reads as the
    operator having saved before they searched."""
    at = GESTURE_TYPE["gesture"]["at"]
    first = _request(_rfc3339(at + 0.1), "r_first", GESTURE_TYPE["tab_id"])
    second = _request(_rfc3339(at + 0.2), "r_second", GESTURE_TYPE["tab_id"])
    third = _request(_rfc3339(at + 0.3), "r_third", GESTURE_TYPE["tab_id"])

    gestures, orphans, _, _ = correlate(_batch([GESTURE_TYPE, third, first, second]), TENANT)

    assert orphans == []
    assert [call.url for call in gestures[0].requests] == [
        f"{REQUEST_POST['request']['url']}?seq=r_first",
        f"{REQUEST_POST['request']['url']}?seq=r_second",
        f"{REQUEST_POST['request']['url']}?seq=r_third",
    ]


def test_what_the_page_said_about_a_required_field_survives_the_wire() -> None:
    """The recorder had been reading `aria-required` for an hour and every
    stored gesture had none.

    Measured on the deployment 2026-09-22 at 07:17. `decode` -- the other
    ingest path -- carried it from the day it was added; this one, which is
    the path an extension's gestures actually take, did not name the field, so
    it was dropped between a faithful capture and the store. The same shape as
    `fire` dropping `unasked` on the panel side: two ends agreeing and nothing
    carrying it between them.
    """
    batch = copy.deepcopy(BATCH)
    events = cast("list[dict[str, Any]]", batch["events"])
    said = next(one for one in events if one.get("kind") == "gesture")["gesture"]["target"]
    said["required"] = True
    said["component"]["required"] = True

    gestures, _, _, _ = correlate(Batch.model_validate(batch), "acme")

    target = gestures[0].action.target
    assert target is not None
    assert target.required is True, "the page said the field was required and the store has none"
    assert target.component is not None
    assert target.component.required is True


def test_a_page_that_said_nothing_about_a_field_stores_nothing() -> None:
    """Three states kept as three. `None` is a page that said nothing and
    `False` is a page saying the field is optional, and coercing the first to
    the second would be this system claiming a form said something it never
    said."""
    gestures, _, _, _ = correlate(Batch.model_validate(copy.deepcopy(BATCH)), "acme")

    target = gestures[0].action.target
    assert target is not None and target.required is None


def _select(ref: str, hop: int = 0) -> dict[str, Any]:
    event = copy.deepcopy(GESTURE_TYPE)
    event["gesture"].update(kind="select", value="b", ref=ref)
    event["gesture"]["target"].update(tag="select", role="combobox")
    event["gesture"]["frame_path"] = [{"index": hop, "url": "https://wms.example/screen"}]
    return event


def _next(
    before: dict[str, Any], ref: str, prior_of: str | None, value: str | None
) -> dict[str, Any]:
    event = copy.deepcopy(before)
    event["gesture"].update(
        kind="click",
        at=before["gesture"]["at"] + 2,
        ref=ref,
        prior_of=prior_of,
        prior={"value": value, "visible": True, "enabled": True},
    )
    return event


def test_a_gesture_gets_the_state_its_target_was_in_when_the_next_one_came() -> None:
    first = _select("r.1")
    second = _next(first, "r.2", "r.1", "Second choice")

    gestures, _, _, _ = correlate(_batch([first, second]), TENANT)

    after = gestures[0].action.after
    assert after is not None
    assert (after.value, after.visible, after.enabled) == ("Second choice", True, True)
    assert gestures[1].action.after is None


def test_a_state_read_off_a_gesture_the_worker_dropped_joins_nothing() -> None:
    # Paused between them: r.2 was typed and dropped, so r.3's prior is r.2's
    # target, and r.1 -- the previous gesture that WAS kept -- is not it.
    first = _select("r.1")
    after_the_pause = _next(first, "r.3", "r.2", "Second choice")

    gestures, _, _, _ = correlate(_batch([first, after_the_pause]), TENANT)

    assert [one.action.after for one in gestures] == [None, None]


def test_two_frames_on_the_same_url_never_hand_each_other_a_state() -> None:
    in_one = _select("r.1", hop=0)
    in_the_other = _next(_select("r.1", hop=1), "r.2", "r.1", "OTHER-FRAME")
    assert in_one["frame_url"] == in_the_other["frame_url"]

    gestures, _, _, _ = correlate(_batch([in_one, in_the_other]), TENANT)

    assert [one.action.after for one in gestures] == [None, None]


def test_a_popup_mark_keeps_the_tab_that_opened_it() -> None:
    popup = {**copy.deepcopy(PAGE_NAVIGATED), "page_kind": "popup_opened", "opener_tab_id": 7}

    _, _, marks, _ = correlate(_batch([popup]), TENANT)

    assert marks[0].opener_tab_id == 7


def test_every_captured_detail_of_the_control_is_kept_and_stored() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    target = event["gesture"]["target"]
    target["bounds"] = {"x": 10.0, "y": 20.0, "width": 80.0, "height": 24.0}
    target["attributes"] = {"name": "clientCode", "autocomplete": "off"}
    target["component"] = {
        "xtype": "textfield",
        "itemId": "clientCode",
        "query": "panel#clients textfield#clientCode",
        "chain": ["panel#clients", "textfield#clientCode"],
    }
    target["landmarks"] = [{"role": "dialog", "name": "New Customer"}]
    event["gesture"]["modifiers"] = ["shift"]
    event["gesture"]["frame_path"] = [{"index": 1, "url": "https://wms.example/shell"}]
    event["gesture"]["detail"] = 0
    event["gesture"]["trusted"] = False
    event["gesture"]["ref"] = "r.1"
    chosen = _select("r.2", hop=1)
    chosen["gesture"]["frame_path"] = event["gesture"]["frame_path"]
    chosen["gesture"]["prior_of"] = "r.1"
    chosen["gesture"]["prior"] = {"value": None, "visible": True, "enabled": False}
    chosen["gesture"]["at"] = event["gesture"]["at"] + 2
    last = _next(chosen, "r.3", "r.2", "Second choice")

    gestures, _, _, _ = correlate(_batch([event, chosen, last]), TENANT)
    stored = _row_to_gesture(_gesture_to_row(gestures[0]))
    selected = _row_to_gesture(_gesture_to_row(gestures[1])).action.after

    action = stored.action
    assert action.target is not None and action.target.component is not None
    assert action.target.bounds == {"x": 10.0, "y": 20.0, "width": 80.0, "height": 24.0}
    assert action.target.attributes == {"name": "clientCode", "autocomplete": "off"}
    assert action.target.component.chain == ("panel#clients", "textfield#clientCode")
    assert [(one.role, one.name) for one in action.target.landmarks] == [("dialog", "New Customer")]
    assert action.modifiers == ("shift",)
    assert action.frame_path is not None
    assert [(hop.index, hop.url) for hop in action.frame_path] == [(1, "https://wms.example/shell")]
    assert action.detail == 0
    assert action.trusted is False
    assert action.after is not None
    assert (action.after.value, action.after.visible, action.after.enabled) == (None, True, False)
    assert selected is not None
    assert (selected.value, selected.visible, selected.enabled) == ("Second choice", True, True)
    assert hash(action)


def test_the_labelled_ancestors_reach_the_stored_target() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    event["gesture"]["target"]["landmarks"] = [{"role": "dialog", "name": "New Customer"}]

    gestures, _, _, _ = correlate(_batch([event]), TENANT)

    target = gestures[0].action.target
    assert target is not None
    assert [(one.role, one.name) for one in target.landmarks] == [("dialog", "New Customer")]


def test_the_frame_path_reaches_the_stored_action() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    event["gesture"]["frame_path"] = [{"index": 1, "url": "https://wms.example/shell"}]

    gestures, _, _, _ = correlate(_batch([event]), TENANT)

    hop = gestures[0].action.frame_path[0]
    assert (hop.index, hop.url) == (1, "https://wms.example/shell")


def test_evidence_recorded_before_frame_identity_stores_no_frame_path() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    assert "frame_path" not in event["gesture"]

    gestures, _, _, _ = correlate(_batch([event]), TENANT)

    assert gestures[0].action.frame_path is None


def test_a_gesture_on_the_top_document_stores_an_empty_frame_path() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    event["gesture"]["frame_path"] = []

    gestures, _, _, _ = correlate(_batch([event]), TENANT)

    assert gestures[0].action.frame_path == ()


def test_the_screen_a_gesture_was_made_on_is_stored_with_it() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    event["gesture"]["outlines"] = [
        {
            "headings": ["New Customer Type"],
            "fields": [{"role": "combobox", "label": "Department", "options": ["Finance"]}],
            "buttons": ["Save"],
        }
    ]

    gestures, _, _, _ = correlate(_batch([event]), TENANT)

    (outline,) = gestures[0].action.outlines
    assert outline.headings == ("New Customer Type",)
    assert outline.fields[0] == OutlineField("combobox", "Department", None, ("Finance",))


def test_a_gesture_without_an_outline_was_made_on_the_last_outlined_screen() -> None:
    first, second, elsewhere = (copy.deepcopy(GESTURE_TYPE) for _ in range(3))
    first["gesture"]["outlines"] = [{"buttons": ["Save"]}]
    second["gesture"]["at"] = first["gesture"]["at"] + 1
    elsewhere["gesture"]["at"] = first["gesture"]["at"] + 2
    elsewhere["gesture"]["frame_path"] = [{"index": 0, "url": "https://wms.example/other"}]

    gestures, _, _, _ = correlate(_batch([first, second, elsewhere]), TENANT)

    assert last_outline(gestures[1], gestures[:1]) == Outline(buttons=("Save",))
    assert last_outline(gestures[2], gestures[:2]) is None


def test_a_screen_from_another_document_in_the_same_frame_is_not_this_one() -> None:
    first, second = (copy.deepcopy(GESTURE_TYPE) for _ in range(2))
    first["gesture"]["outlines"] = [{"buttons": ["Save"]}]
    first["gesture"]["url"] = "https://wms.example/customers?id=1"
    second["gesture"]["url"] = "https://wms.example/orders?id=1"
    second["gesture"]["at"] = first["gesture"]["at"] + 1

    gestures, _, _, _ = correlate(_batch([first, second]), TENANT)

    assert last_outline(gestures[1], gestures[:1]) is None


def test_a_page_event_carries_its_cookies_and_mail_thread_to_the_mark() -> None:
    from sro.domain.observation.gesture import CookieSeen

    mark = {
        **PAGE_NAVIGATED,
        "page_kind": "cookies_set",
        "cookies": [{"name": "JSESSIONID", "expires_at": 1_790_003_600.0}],
        "mail_thread": "FMfcgzQZTxyzAbcDefGh",
    }
    _, _, orphan_pages, _ = correlate(_batch([mark]), TENANT)
    (page,) = orphan_pages
    assert page.cookies == (CookieSeen("JSESSIONID", 1_790_003_600.0),)
    assert page.mail_thread == "FMfcgzQZTxyzAbcDefGh"
