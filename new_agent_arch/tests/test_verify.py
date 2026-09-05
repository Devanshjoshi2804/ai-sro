from rig.channel import Answer as Reply
from rig.channel import FakeChannel
from rig.correlate import correlate
from rig.models import Answer, FakeAsker
from rig.planner import Look
from rig.verify import confirming_read, expected_statuses, verify
from rig.wire import Batch
from rig.workflows import Step
from tests.fixtures import BATCH


def _saver():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return next(g for g in gestures if g.requests)


def _step(g):
    return Step(order=0, says="save", system=None, cites=[g.id])


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
    the run supplied, and no screenshot is looked at."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    later_get = next(
        r for r in saver.requests if r.method == "GET" and r.started_at > post.started_at
    )
    channel = FakeChannel(
        {"http.send": [Reply(ok=True, result={"status": 200, "body": '{"workArea":"THIRD"}'})]}
    )

    verdict = await verify(
        step=_step(saver),
        sent_kind="ui.perform",
        answer=Reply(ok=True, result={"performed": True}),
        cited=[saver],
        values={"workArea": "THIRD"},
        look_before=Look(None, None, ""),
        look_after=Look(None, None, ""),
        channel=channel,
        device_id="dev_test",
        run_id="run_1",
        origin="http://127.0.0.1:63319",
        asker=FakeAsker(),
        model="m",
    )

    assert (verdict.state, verdict.by) == ("held", "read")
    assert channel.sent[0]["payload"]["url"] == later_get.url


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
