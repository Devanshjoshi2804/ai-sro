import json

from rig.channel import Answer as Reply
from rig.channel import FakeChannel
from rig.correlate import correlate
from rig.models import Answer, FakeAsker
from rig.planner import Look
from rig.verify import confirming_read, expected_statuses, verify
from rig.wire import REDACTED, Batch
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


def test_expected_statuses_and_the_confirming_read_come_from_the_evidence() -> None:
    saver = _saver()
    by_id = {saver.id: saver}
    assert expected_statuses(_step(saver), by_id) == {
        r.status for r in saver.requests if r.method == "POST" and r.status
    }
    read = confirming_read(_step(saver), by_id)
    assert read is not None and read.method == "GET"
