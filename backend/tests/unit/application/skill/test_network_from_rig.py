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
    plan = network_plan_for_gesture(GESTURE, [WRITE], target_system="wms.example", facility="SG")

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


def test_a_call_the_warehouse_rejected_does_not_declare_its_own_rejection() -> None:
    """`primary_of`'s last rung is "the first call at all", so a gesture whose
    every call FAILED still yields a plan -- and recording its 4xx as the
    expected status makes a run correct when the warehouse rejects the write and
    failed when it lands. There is one in the real store: a PUT to
    /data/WM/wm/addresses that came back 422. No expectation proves nothing; a
    wrong one proves the opposite."""
    plan = network_plan_for_gesture(
        GESTURE, [{**WRITE, "status": 422}], target_system="wms.example", facility="SG"
    )

    assert plan is not None
    assert plan.method == "POST", "still a plan -- the call is what the gesture did"
    assert plan.expected_status is None, "but it declares no success it never had"


def test_the_unreplayable_guard_can_actually_guard() -> None:
    """`NetworkPlan` refuses `replayable=False` with no reason -- an unexplained
    dead end is indistinguishable from a capture bug -- so a bare flag could
    never once fire without raising and taking the whole build with it. A guard
    that crashes instead of guarding is worse than none, because it looks like
    one."""
    for stored, expected in (
        ({"resource_type": "websocket"}, "websocket"),
        ({"failure_reason": "net::ERR_CONNECTION_RESET"}, "did not complete"),
        ({"blocked_reason": "csp"}, "blocked"),
    ):
        plan = network_plan_for_gesture(
            GESTURE, [{**WRITE, **stored}], target_system="wms.example", facility="SG"
        )
        assert plan is not None, stored
        assert plan.replayable is False, stored
        assert expected in (plan.unreplayable_reason or ""), stored


def test_a_dollar_in_a_header_value_is_not_a_parameter() -> None:
    """The third path. `_literal` covers a recorded value and `_bind` covers a
    body; a captured header value went to `Template` raw, so a `$` in one
    reported itself as a parameter the plan needs -- and a version refuses a
    step referencing one it never declared."""
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_headers": {"X-Note": "cost $40 per $unit"}}],
        target_system="wms.example",
        facility="SG",
    )

    assert plan is not None
    assert plan.placeholders == frozenset()
    assert [h.value.render({}) for h in plan.headers if h.value] == ["cost $40 per $unit"]


def test_a_header_redacted_by_shape_is_a_credential_not_a_literal() -> None:
    """`classify_header` judges by NAME; the rig also redacts by SHAPE, running
    `redact_shapes` over every header value it does not recognise. So a bearer
    token under a vendor's own header name reads semantic here while its value
    is the marker -- and replaying it puts the literal characters «redacted» on
    the wire and calls the plan replayable."""
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_headers": {"X-Acme-Ticket": "«redacted»"}}],
        target_system="wms.example",
        facility="SG",
    )

    assert plan is not None
    ticket = next(h for h in plan.headers if h.name == "X-Acme-Ticket")
    assert ticket.value is None, "the marker must not travel"
    assert ticket.credential_ref == "wms.example/SG/x-acme-ticket"


def test_a_credential_is_filed_under_the_host_the_call_went_to() -> None:
    """A vault key is scoped per system, and the jobs this project exists to
    capture cross systems -- so one target_system for a whole workflow files
    half its calls under the wrong login."""
    plan = network_plan_for_gesture(
        GESTURE,
        [
            {
                **WRITE,
                "url": "https://other.example/api/x",
                "request_headers": {"authorization": "«redacted»"},
            }
        ],
        facility="SG",
    )

    assert plan is not None
    assert [h.credential_ref for h in plan.headers] == ["other.example/SG/authorization"]


def test_a_body_kept_out_of_line_is_not_an_absent_body() -> None:
    """`body_blob_uri` exists for this. Returning None made a large POST into an
    empty POST that still called itself replayable."""
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_body": {"blob_uri": "s3://x/y", "size_bytes": 900_000}}],
        target_system="wms.example",
        facility="SG",
    )

    assert plan is not None
    assert plan.body is None
    assert plan.body_blob_uri == "s3://x/y"


def test_a_body_the_redactor_gave_up_on_is_not_posted_to_the_warehouse() -> None:
    """The rig writes a SENTENCE in place of a body it could not parse well
    enough to redact. Sending it as a payload posts that sentence."""
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_body": {"text": "«whole body: could not be parsed to redact»"}}],
        target_system="wms.example",
        facility="SG",
    )

    assert plan is not None
    assert plan.body is None and plan.body_blob_uri is None


def test_an_observed_header_with_an_empty_value_is_still_observed() -> None:
    """`build_header_plans` promises one plan per observed header and that
    nothing is dropped. Some APIs distinguish absent from blank."""
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_headers": {"X-Trace-Hint": ""}}],
        target_system="wms.example",
        facility="SG",
    )

    assert plan is not None
    assert "X-Trace-Hint" in [h.name for h in plan.headers]


def test_a_method_with_stray_whitespace_is_not_a_different_method() -> None:
    """`is_mutation` reads the method, so `"  get  "` reported a read as a
    write."""
    plan = network_plan_for_gesture(
        GESTURE, [{**WRITE, "method": "  get  "}], target_system="w", facility="SG"
    )

    assert plan is not None and plan.method == "GET"


def test_the_content_type_is_found_whatever_its_casing() -> None:
    """HTTP/2 lowercases and HTTP/1.1 does not. Two hand-rolled casings covered
    the two the store happens to hold; `CapturedRequest.header` exists for it."""
    plan = network_plan_for_gesture(
        GESTURE,
        [{**WRITE, "request_headers": {"Content-type": "application/json"}}],
        target_system="w",
        facility="SG",
    )

    assert plan is not None and plan.content_type == "application/json"


FULL_REQUEST = {
    "request_id": "req_abc",
    "method": "POST",
    "url": "https://wms.example/data/WM/wm/workAreas",
    "resource_type": "fetch",
    "started_at": "2026-08-26T10:40:05.000Z",
    "request_headers": {"Accept": "application/json"},
    "request_body": {
        "text": '{"workArea":"NEWTESTS"}',
        "blob_uri": None,
        "size_bytes": 23,
        "mime_type": "application/json",
        "encoding": "utf8",
    },
    "status": 201,
    "status_text": "Created",
    "response_headers": {"Content-Type": "application/json"},
    "response_body": {"text": '{"ok":true}', "size_bytes": 11, "mime_type": "application/json"},
    "redirect_chain": [{"url": "https://wms.example/old", "status": 302, "location": "/new"}],
    "duration_ms": 86,
    "from_cache": True,
    "failure_reason": "net::ERR_ABORTED",
    "blocked_reason": "csp",
}


def test_every_field_the_rig_stored_reaches_the_captured_request() -> None:
    """Field by field, because each is one dictionary key away from vanishing.

    Everything here is read out of untrusted JSON by name, and a Python dict is
    case-sensitive -- `stored.get("STATUS_TEXT")` returns None and the field is
    simply gone, with no error and a perfectly valid request built around the
    hole. A mutation sweep found fifteen such fields with nothing asserting any
    of them.
    """
    found = request_from_rig(FULL_REQUEST, at=AT)

    assert found is not None
    assert found.request_id == "req_abc"
    assert found.method == "POST"
    assert found.url == "https://wms.example/data/WM/wm/workAreas"
    assert found.resource_type == "fetch"
    assert found.started_at == datetime(2026, 8, 26, 10, 40, 5, tzinfo=UTC)
    assert found.request_headers == {"Accept": "application/json"}
    assert found.status == 201
    assert found.status_text == "Created"
    assert found.response_headers == {"Content-Type": "application/json"}
    assert found.duration_ms == 86
    assert found.from_cache is True
    assert found.failure_reason == "net::ERR_ABORTED"
    assert found.blocked_reason == "csp"


def test_a_body_keeps_the_metadata_the_rig_recorded_beside_it() -> None:
    """`Body` carries what the payload WAS as well as what it said. A dropped
    mime type or size is what a reviewer reads to decide whether a plan is
    replaying the thing that was captured."""
    found = request_from_rig(FULL_REQUEST, at=AT)

    assert found is not None and found.request_body is not None
    body = found.request_body
    assert body.text == '{"workArea":"NEWTESTS"}'
    assert body.size_bytes == 23
    assert body.mime_type == "application/json"
    assert body.encoding == "utf8"
    assert found.response_body is not None and found.response_body.text == '{"ok":true}'


def test_a_body_with_no_size_recorded_is_measured_rather_than_left_at_zero() -> None:
    """The fallback exists because a size of 0 beside a real payload reads as an
    empty body to anything downstream."""
    found = request_from_rig({**FULL_REQUEST, "request_body": {"text": "abcdefghij"}}, at=AT)

    assert found is not None and found.request_body is not None
    assert found.request_body.size_bytes == 10


def test_the_redirect_chain_survives_with_every_hop_intact() -> None:
    """A redirect hop is where a credential ends up when a login bounces, and
    `redact.py` walks these. A chain that quietly emptied would take the thing
    a reviewer most wants to look at with it."""
    found = request_from_rig(FULL_REQUEST, at=AT)

    assert found is not None
    assert len(found.redirect_chain) == 1
    hop = found.redirect_chain[0]
    assert (hop.url, hop.status, hop.location) == ("https://wms.example/old", 302, "/new")


def test_a_hop_that_is_not_a_mapping_is_skipped_and_the_rest_are_kept() -> None:
    """`and` rather than `or` in that guard: a string in the chain would be
    asked for `.get` and raise."""
    found = request_from_rig(
        {**FULL_REQUEST, "redirect_chain": ["nonsense", {"url": "https://a/", "status": 301}]},
        at=AT,
    )

    assert found is not None
    assert [hop.url for hop in found.redirect_chain] == ["https://a/"]


def test_a_header_with_a_name_but_no_string_value_is_not_a_header() -> None:
    """`and` rather than `or`: a name alone is not a header, and `HeaderPlan`
    would be asked to carry a value that is not one."""
    found = request_from_rig(
        {**FULL_REQUEST, "request_headers": {"A": "keep", "B": None, "": "no name", "C": 7}},
        at=AT,
    )

    assert found is not None
    assert dict(found.request_headers) == {"A": "keep"}


def test_a_gesture_with_no_clock_still_yields_a_plan_from_its_calls() -> None:
    """The gesture's own time is only ever a FALLBACK for a request that stored
    none, so a gesture with no readable clock costs nothing as long as its
    requests have theirs. Refusing on a missing `at` threw away every call it
    caused over a field none of them needed."""
    plan = network_plan_for_gesture(
        {"kind": "click", "url": "https://wms.example/x"},
        [FULL_REQUEST],
        target_system="wms.example",
        facility="SG",
    )

    assert plan is not None and plan.method == "POST"
