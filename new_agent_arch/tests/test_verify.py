import json

from rig.channel import Answer as Reply
from rig.channel import FakeChannel
from rig.correlate import correlate
from rig.models import Answer, FakeAsker
from rig.planner import Look
from rig.verify import confirming_read, expected_statuses, verify
from rig.wire import REDACTED, Batch, Request
from rig.workflows import Step
from tests.fixtures import BATCH


def _saver():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return next(g for g in gestures if g.requests)


def _step(g):
    return Step(order=0, says="save", system=None, cites=[g.id])


def _read(body, status=200):
    return FakeChannel({"http.send": [Reply(ok=True, result={"status": status, "body": body})]})


async def _verified(saver, *, channel, values, sent_kind="ui.perform", answer=None, asker=None):
    """One UI step verified against a scripted confirming read."""
    return await verify(
        step=_step(saver),
        sent_kind=sent_kind,
        answer=answer or Reply(ok=True, result={"performed": True}),
        cited=[saver],
        values=values,
        look_before=Look(None, None, ""),
        look_after=Look(None, None, ""),
        channel=channel,
        device_id="dev_test",
        run_id="run_1",
        origin="http://127.0.0.1:63319",
        asker=asker or FakeAsker(),
        model="m",
    )


async def test_a_call_that_returned_the_status_the_evidence_expects_is_held_by_status() -> None:
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    post.status = 201
    asker = FakeAsker()

    verdict = await verify(
        step=_step(saver),
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 201, "body": "{}"}),
        cited=[saver],
        values={},
        look_before=Look(None, None, ""),
        look_after=Look(None, None, ""),
        channel=FakeChannel(),
        device_id="dev_test",
        run_id="run_1",
        origin=None,
        asker=asker,
        model="m",
    )

    assert (verdict.state, verdict.by) == ("held", "status")
    assert asker.asked == [], "no model was asked when the state already said"


async def test_a_call_the_warehouse_rejected_is_failed_by_status() -> None:
    saver = _saver()
    verdict = await verify(
        step=_step(saver),
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 422, "body": "no"}),
        cited=[saver],
        values={},
        look_before=Look(None, None, ""),
        look_after=Look(None, None, ""),
        channel=FakeChannel(),
        device_id="dev_test",
        run_id="run_1",
        origin=None,
        asker=FakeAsker(),
        model="m",
    )
    assert (verdict.state, verdict.by) == ("failed", "status") and "422" in verdict.reason


async def test_a_ui_step_is_confirmed_by_the_read_the_evidence_shows_the_page_makes() -> None:
    """Hidden state before visible state: the read comes back with the value
    the run supplied, and no screenshot is looked at.

    The probe is the first read after the write that CAME BACK. The capture
    has a GET to a dead host one millisecond after the POST; asking it again
    would prove nothing, so it is not the one chosen.
    """
    saver = _saver()
    channel = _read('{"workArea":"THIRD"}')

    verdict = await _verified(saver, channel=channel, values={"workArea": "THIRD"})

    assert (verdict.state, verdict.by) == ("held", "read")
    asked = channel.sent[0]["payload"]["url"]
    assert asked == "http://127.0.0.1:63319/api/stream"
    assert asked != "http://127.0.0.1:1/never", "a read that never completed is not a confirmation"


async def test_a_read_that_did_not_come_back_2xx_decides_nothing() -> None:
    """A 503 answers ok=True with a body that matches nothing, and marking a
    correct write failed on that is worse than not deciding."""
    saver = _saver()
    verdict = await _verified(
        saver, channel=_read("service unavailable", status=503), values={"workArea": "THIRD"}
    )
    assert verdict.by != "read"


async def test_the_read_matches_a_whole_value_not_a_substring_of_one() -> None:
    saver = _saver()
    inside = await _verified(saver, channel=_read('{"orders":[{"id":"ORD-1"}]}'), values={"n": "1"})
    assert (inside.state, inside.by) == ("failed", "read"), "ORD-1 is not the value 1"

    whole = await _verified(
        _saver(), channel=_read('{"code":"THIRD"}'), values={"clientCode": "THIRD"}
    )
    assert (whole.state, whole.by) == ("held", "read")


async def test_the_probe_never_carries_a_header_the_boundary_struck_out() -> None:
    saver = _saver()
    stream = next(r for r in saver.requests if r.url.endswith("/api/stream"))
    saver.requests[saver.requests.index(stream)] = stream.model_copy(
        update={"request_headers": {"X-CSRF": REDACTED, "Accept": "application/json"}}
    )
    channel = _read('{"workArea":"THIRD"}')

    await _verified(saver, channel=channel, values={"workArea": "THIRD"})

    assert channel.sent[0]["payload"]["headers"] == {"Accept": "application/json"}


async def test_a_status_that_already_decided_is_not_second_guessed_by_a_read() -> None:
    """Belt order, not belt availability: the read would have confirmed too,
    and it is never sent."""
    saver = _saver()
    channel = _read('{"workArea":"THIRD"}')

    verdict = await _verified(
        saver,
        channel=channel,
        values={"workArea": "THIRD"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
    )

    assert (verdict.state, verdict.by) == ("held", "status")
    assert channel.sent == [], "the state already said; nothing else was asked"


async def test_a_status_the_operator_also_got_is_still_a_refusal() -> None:
    """A demonstration that recorded a 409 does not make 409 mean success."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    post.status = 409

    verdict = await _verified(
        saver,
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 409, "body": "conflict"}),
    )
    assert (verdict.state, verdict.by) == ("failed", "status")


async def test_the_screenshot_is_last_and_least() -> None:
    saver = _saver()
    saver.requests = []  # nothing to read, nothing to confirm by
    asker = FakeAsker(
        Answer(data={"held": True, "why": "the form shows the saved record"}, cost_usd=0.0002)
    )

    verdict = await verify(
        step=_step(saver),
        sent_kind="ui.perform",
        answer=Reply(ok=True, result={"performed": True}),
        cited=[saver],
        values={},
        look_before=Look("u", b"before", "Save"),
        look_after=Look("u", b"after", "Saved"),
        channel=FakeChannel(),
        device_id="dev_test",
        run_id="run_1",
        origin=None,
        asker=asker,
        model="m",
    )

    assert (verdict.state, verdict.by) == ("held", "screen")
    assert asker.asked[0]["image"] == b"after"
    # Nothing else off the browser's answer: for an http.send that dict is the
    # response body and headers, and no trim rule stands between it and here.
    shown = json.loads(asker.asked[0]["evidence"])
    assert shown["browser_answered"] == {"ok": True, "status": None}
    assert verdict.answer is not None and verdict.answer.cost_usd == 0.0002


async def test_no_screenshot_and_no_state_is_unclear_not_held() -> None:
    saver = _saver()
    saver.requests = []
    verdict = await verify(
        step=_step(saver),
        sent_kind="ui.perform",
        answer=Reply(ok=True, result={"performed": True}),
        cited=[saver],
        values={},
        look_before=Look(None, None, ""),
        look_after=Look(None, None, ""),
        channel=FakeChannel(),
        device_id="dev_test",
        run_id="run_1",
        origin=None,
        asker=FakeAsker(),
        model="m",
    )
    assert verdict.state == "unclear" and verdict.by == "none"


async def test_a_command_the_browser_refused_is_failed_before_anything_is_verified() -> None:
    saver = _saver()
    verdict = await verify(
        step=_step(saver),
        sent_kind="ui.perform",
        answer=Reply(ok=False, error_kind="control_not_found", error_detail="no visible match"),
        cited=[saver],
        values={},
        look_before=Look(None, None, ""),
        look_after=Look(None, None, ""),
        channel=FakeChannel(),
        device_id="dev_test",
        run_id="run_1",
        origin=None,
        asker=FakeAsker(),
        model="m",
    )
    assert verdict.state == "failed" and verdict.reason == "control_not_found: no visible match"
    assert verdict.by == "none", "nothing looked at anything; the browser refused"


def test_expected_statuses_and_the_confirming_read_come_from_the_evidence() -> None:
    saver = _saver()
    by_id = {saver.id: saver}
    assert expected_statuses(_step(saver), by_id) == {
        r.status for r in saver.requests if r.method == "POST" and r.status
    }
    read = confirming_read(_step(saver), by_id)
    assert read is not None and read.method == "GET"


async def test_a_confirming_read_whose_url_carries_a_marker_is_never_sent() -> None:
    saver = _saver()
    read = confirming_read(_step(saver), {saver.id: saver})
    assert read is not None
    struck = read.model_copy(update={"url": f"{read.url}?token={REDACTED}"})
    saver.requests[saver.requests.index(read)] = struck
    channel = _read('{"code": "THIRD"}')

    verdict = await _verified(saver, channel=channel, values={"clientCode": "THIRD"})

    assert channel.sent == [], "a probe carrying the marker asks nothing about the state"
    assert verdict.by != "read"


def _get(url="http://127.0.0.1:63319/api/after", started_at="2026-08-31T08:40:04.900Z", **over):
    return Request.model_validate(
        {
            "request_id": "probe",
            "method": "GET",
            "url": url,
            "started_at": started_at,
            "status": 200,
            **over,
        }
    )


async def test_the_call_that_returned_exactly_400_is_a_refusal_not_a_success() -> None:
    """The boundary itself: 400 is the first status that is a refusal, and a
    run that read it as anything else would go on to the next step."""
    saver = _saver()
    verdict = await _verified(
        saver,
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 400, "body": "bad request"}),
    )
    assert (verdict.state, verdict.by) == ("failed", "status")


async def test_a_2xx_the_evidence_never_saw_does_not_hold_by_status() -> None:
    """The evidence recorded a 201. A 200 is not that, so the status belt has
    nothing to say and the run falls through to the belts that look."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    post.status = 201
    saver.requests = [post]

    verdict = await _verified(
        saver,
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
    )
    assert verdict.by != "status"


async def test_with_no_status_in_the_evidence_only_a_2xx_holds() -> None:
    """Nothing recorded, so 2xx and only 2xx is success. 300 is a redirect
    nobody followed, not a record that was written."""
    for status, held in ((200, True), (299, True), (300, False)):
        saver = _saver()
        saver.requests = []
        verdict = await _verified(
            saver,
            channel=FakeChannel(),
            values={},
            sent_kind="http.send",
            answer=Reply(ok=True, result={"status": status, "body": "{}"}),
        )
        assert ((verdict.state, verdict.by) == ("held", "status")) is held, status


def test_a_read_the_evidence_made_is_never_an_expected_write_status() -> None:
    """`expected_statuses` is what the mutation came back with. A GET's 204
    counted there would teach the verifier that 204 means the write landed."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    post.status = 201
    saver.requests = [
        post,
        _get(status=204),
        _get(request_id="head", method="HEAD", status=205),
        _get(request_id="pre", method="OPTIONS", status=206),
    ]

    assert expected_statuses(_step(saver), {saver.id: saver}) == {201}


def test_a_call_that_never_returned_names_no_status_the_warehouse_gave() -> None:
    saver = _saver()
    dead = next(r for r in saver.requests if r.method == "POST").model_copy(
        update={"status": 502, "failure_reason": "Failed to fetch"}
    )
    saver.requests = [dead]

    assert expected_statuses(_step(saver), {saver.id: saver}) == set()


def test_a_cited_gesture_the_store_lost_does_not_hide_the_evidence_behind_it() -> None:
    saver = _saver()
    step = Step(order=0, says="save", system=None, cites=["ges_gone", saver.id])
    by_id = {saver.id: saver}

    assert expected_statuses(step, by_id) == {200}
    read = confirming_read(step, by_id)
    assert read is not None and read.url.endswith("/api/stream")


def test_the_confirming_read_comes_after_the_write_and_came_back() -> None:
    """Same instant is not after: a read that raced the write saw the state
    before it. And a read that never returned confirms nothing."""
    saver = _saver()
    call = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [
        call,
        _get(request_id="same", started_at=call.started_at),
        # A status on a call that reports a failure is not a status the
        # warehouse gave back -- the same reading `expected_statuses` makes.
        _get(request_id="dead", status=502, failure_reason="Failed to fetch"),
    ]

    assert confirming_read(_step(saver), {saver.id: saver}) is None


def test_a_step_whose_recorded_call_is_itself_a_read_has_nothing_to_confirm() -> None:
    """`confirming_read` answers "the read this page makes after its write".
    A step that never wrote has no after -- however that read is spelled."""
    for method in ("GET", "HEAD", "OPTIONS"):
        saver = _saver()
        saver.requests = [
            _get(request_id="first", method=method),
            _get(request_id="later", started_at="2026-08-31T08:40:05.900Z"),
        ]

        assert confirming_read(_step(saver), {saver.id: saver}) is None, method


async def test_the_probe_is_a_bodiless_get_sent_to_this_run_and_this_browser() -> None:
    saver = _saver()
    channel = _read('{"workArea":"THIRD"}')

    verdict = await _verified(saver, channel=channel, values={"workArea": "THIRD"})

    [sent] = channel.sent
    assert sent["device_id"] == "dev_test" and sent["run_id"] == "run_1"
    assert sent["payload"]["method"] == "GET" and sent["payload"]["body"] is None
    assert "http://127.0.0.1:63319/api/stream" in verdict.reason, "the record says what was read"


async def test_a_read_that_did_not_show_the_value_says_which_read_it_was() -> None:
    saver = _saver()
    verdict = await _verified(
        saver, channel=_read('{"workArea":"FIRST"}'), values={"workArea": "THIRD"}
    )
    assert (verdict.state, verdict.by) == ("failed", "read")
    assert "http://127.0.0.1:63319/api/stream" in verdict.reason


async def test_a_read_that_came_back_300_is_not_a_read_that_came_back() -> None:
    saver = _saver()
    verdict = await _verified(
        saver, channel=_read('{"workArea":"THIRD"}', status=300), values={"workArea": "THIRD"}
    )
    assert verdict.by != "read"


async def test_a_value_nested_inside_the_read_is_still_a_value_the_read_shows() -> None:
    """Leaves, at any depth: the confirming read of a created record answers
    the record, not a flat dictionary of it."""
    saver = _saver()
    verdict = await _verified(
        saver,
        channel=_read('{"data":{"order":{"workArea":"THIRD"}}}'),
        values={"workArea": "THIRD"},
    )
    assert (verdict.state, verdict.by) == ("held", "read")


async def test_a_read_that_is_not_json_is_matched_on_its_text() -> None:
    saver = _saver()
    held = await _verified(
        saver, channel=_read("<p>work area THIRD saved</p>"), values={"workArea": "THIRD"}
    )
    assert (held.state, held.by) == ("held", "read")

    missing = await _verified(
        _saver(), channel=_read("<p>nothing here</p>"), values={"workArea": "THIRD"}
    )
    assert (missing.state, missing.by) == ("failed", "read")


async def test_nothing_to_decide_on_is_unclear_and_says_so() -> None:
    saver = _saver()
    saver.requests = []
    verdict = await _verified(saver, channel=FakeChannel(), values={})
    assert (verdict.state, verdict.by) == ("unclear", "none")
    assert verdict.reason, "a verdict nobody can read is not a record"


async def test_a_model_that_answered_nothing_leaves_the_step_unclear_with_its_error() -> None:
    saver = _saver()
    saver.requests = []
    judged = Answer(data=None, error="the model returned no candidates", cost_usd=0.0001)
    asker = FakeAsker(judged)

    verdict = await verify(
        step=_step(saver),
        sent_kind="ui.perform",
        answer=Reply(ok=True, result={"performed": True}),
        cited=[saver],
        values={},
        look_before=Look(None, None, ""),
        look_after=Look("u", b"after", "Saved"),
        channel=FakeChannel(),
        device_id="dev_test",
        run_id="run_1",
        origin=None,
        asker=asker,
        model="m",
    )

    assert (verdict.state, verdict.by) == ("unclear", "screen")
    assert verdict.reason == "the model returned no candidates"
    assert verdict.answer is judged, "the verdict carries what the reading cost"
    assert asker.asked[0]["instructions"], "a model told nothing judges nothing"


async def test_the_screen_verdict_is_the_models_own_word_and_its_own_reason() -> None:
    saver = _saver()
    saver.requests = []

    async def _screened(data):
        return await verify(
            step=_step(saver),
            sent_kind="ui.perform",
            answer=Reply(ok=True, result={"performed": True}),
            cited=[saver],
            values={},
            look_before=Look("u", b"before", "Save"),
            look_after=Look("u", b"after", "Saved"),
            channel=FakeChannel(),
            device_id="dev_test",
            run_id="run_1",
            origin=None,
            asker=FakeAsker(Answer(data=data)),
            model="m",
        )

    refused = await _screened({"held": False, "why": "the form still shows the old code"})
    assert (refused.state, refused.by) == ("failed", "screen")
    assert refused.reason == "the form still shows the old code"

    held = await _screened({"held": True, "why": "the saved record is on screen"})
    assert (held.state, held.by) == ("held", "screen")
    assert held.reason == "the saved record is on screen"

    silent = await _screened({"held": True})
    assert silent.reason == "", "no explanation is an empty one, not the word None"
