"""The call a mined gesture caused, as a plan a run can replay.

Measured over all 291 requests the rig stored from 170 hours of real capture:
64 gestures yield a network plan, 106 CSRF headers are minted rather than
replayed, and the only `authorization` header anywhere is on twelve
`localhost` calls -- the rig talking to its own ingest.
"""

from datetime import UTC, datetime

from sro.application.skill.network_from_rig import network_plan_for_gesture, request_from_rig
from sro.domain.recording.sensitivity import Sensitivity

AT = datetime(2026, 8, 26, 10, 40, tzinfo=UTC)
GESTURE = {"kind": "click", "at": AT.timestamp(), "url": "https://wms.example/workAreas"}

# The shape the rig actually stores, from the batch that created a work area.
WRITE = {
    "request_id": "req_1",
    "method": "POST",
    "url": "https://wms.example/data/WM/wm/workAreas?siteId=SG",
    "resource_type": "xhr",
    "started_at": "2026-08-26T10:40:05.000Z",
    "request_headers": {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "CSRF-ENCRYPT-TOKEN": "«redacted»",
    },
    "request_body": {
        "text": '{"workArea":"NEWTESTS","workAreaDescription":"testing","warehouseId":"SG"}',
        "size_bytes": 73,
        "mime_type": "application/json",
    },
    "status": 201,
    "response_headers": {},
    "redirect_chain": [],
}
BEACON = {
    "request_id": "req_0",
    "method": "POST",
    "url": "https://analytics.google.com/g/collect?v=2",
    "resource_type": "fetch",
    "started_at": "2026-08-26T10:40:04.000Z",
    "status": 0,
}

BINDINGS = {
    "workArea": frozenset({"NEWTESTS", "twoTEST"}),
    "workAreaDescription": frozenset({"testing", "testing again"}),
}


def test_the_write_is_the_call_the_gesture_is_about_not_the_beacon() -> None:
    """`primary_of` is called rather than restated, so the rule that excludes
    analytics noise is the induction path's own -- one rule, two sources."""
    plan = network_plan_for_gesture(
        GESTURE, [BEACON, WRITE], target_system="wms.example", facility="SG"
    )

    assert plan is not None
    assert plan.method == "POST"
    assert "workAreas" in plan.url.raw
    assert plan.expected_status == 201


def test_a_gesture_that_caused_only_background_traffic_has_no_plan() -> None:
    """None is the ordinary answer, not a failure. Measured on the real
    corpus: 78 of 387 gestures carry any request at all."""
    assert network_plan_for_gesture(GESTURE, [BEACON], target_system="w", facility="SG") is None
    assert network_plan_for_gesture(GESTURE, [], target_system="w", facility="SG") is None


def test_a_stale_csrf_token_is_minted_and_never_replayed() -> None:
    """The rig redacted it at its parse boundary, so the captured value is the
    marker -- and it would have been stale even unredacted. Recording that the
    call REQUIRES one is the useful part."""
    plan = network_plan_for_gesture(
        GESTURE, [WRITE], target_system="wms.example", facility="SG"
    )

    assert plan is not None
    csrf = [h for h in plan.headers if h.sensitivity is Sensitivity.CSRF]
    assert [h.name for h in csrf] == ["CSRF-ENCRYPT-TOKEN"]
    assert csrf[0].mint is True
    assert csrf[0].value is None, "the marker must not travel as a value"


def test_what_the_operator_typed_on_the_screen_lands_in_the_body() -> None:
    """The whole thesis, end to end. `workArea` and `workAreaDescription` were
    derived from two doings of a UI gesture; they are two keys of the POST that
    creates a work area, and a run can now be asked for different ones."""
    plan = network_plan_for_gesture(
        GESTURE, [WRITE], target_system="wms.example", facility="SG", bindings=BINDINGS
    )

    assert plan is not None and plan.body is not None
    assert plan.placeholders == {"workArea", "workAreaDescription"}
    assert '"warehouseId": "SG"' in plan.body.raw, "a constant of the job stays a constant"
    rendered = plan.body.render({"workArea": "THIRD", "workAreaDescription": "a third one"})
    assert '"workArea": "THIRD"' in rendered


def test_a_value_is_bound_by_its_key_and_never_by_scanning_the_text() -> None:
    """A blind replacement rewrites the same characters wherever they appear.
    Here the work area is named `SG`, which is also the warehouse id sitting
    beside it -- and the warehouse id did not vary."""
    body = '{"workArea":"SG","warehouseId":"SG"}'
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_body": {"text": body}}],
        target_system="wms.example",
        facility="SG",
        bindings={"workArea": frozenset({"SG", "OTHER"})},
    )

    assert plan is not None and plan.body is not None
    assert plan.placeholders == {"workArea"}
    assert '"warehouseId": "SG"' in plan.body.raw


def test_a_dollar_in_a_captured_body_is_not_a_parameter() -> None:
    """Template is string.Template. A price or a shell fragment in a real body
    would otherwise report itself as a parameter the plan needs."""
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_body": {"text": '{"note":"cost $40 per $unit"}'}}],
        target_system="wms.example",
        facility="SG",
        bindings=BINDINGS,
    )

    assert plan is not None and plan.body is not None
    assert plan.placeholders == frozenset()
    assert "$40" in plan.body.render({})


def test_a_body_already_holding_the_sentinel_is_left_alone() -> None:
    """It costs a binding and never a payload. The alternative is a body the
    substitution corrupted."""
    body = '{"workArea":"NEWTESTS","note":"@@SRO-PARAM-0@@"}'
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_body": {"text": body}}],
        target_system="wms.example",
        facility="SG",
        bindings=BINDINGS,
    )

    assert plan is not None and plan.body is not None
    assert plan.placeholders == frozenset(), "nothing bound"
    assert "NEWTESTS" in plan.body.raw, "and nothing lost"


def test_a_request_keeps_its_own_time_and_falls_back_to_the_gestures() -> None:
    """CapturedRequest refuses a naive datetime, and the rig writes `Z`. The
    fallback exists so real evidence is not dropped over a clock format -- but
    it is a fallback: a request that stored a readable time keeps it, which is
    what orders the ones `primary_of` cannot separate by path."""
    kept = request_from_rig(WRITE, at=AT)
    assert kept is not None
    assert kept.started_at == datetime(2026, 8, 26, 10, 40, 5, tzinfo=UTC), "its own"

    for unreadable in ("not a time", "2026-08-26T10:40:05", ""):
        fell_back = request_from_rig({**WRITE, "started_at": unreadable}, at=AT)
        assert fell_back is not None, unreadable
        assert fell_back.started_at == AT, unreadable


def test_a_stored_row_with_no_method_or_url_is_not_a_request() -> None:
    assert request_from_rig({"url": "https://wms.example/x"}, at=AT) is None
    assert request_from_rig({"method": "GET"}, at=AT) is None
