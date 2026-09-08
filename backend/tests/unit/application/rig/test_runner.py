"""The loop that takes a mined job and performs it.

Ported from `new_agent_arch/tests/test_runner.py`. That file is the largest in
the rig's suite and this port is split in two the way the module is: plan 3b's
task 6 is the skeleton -- the claimed row read back as the authority for what
was asked, look -> plan -> perform -> verify -> record per step, the step
budget, `_fell_over`, and the orphan sweep at startup -- and task 7 is the
rungs and the gates on top of it: the Pro rescue, the sight rung, the wider
`may_write`, the writes a dry run withholds, the wait for a person, `from_step`
and earned autonomy. The rig tests that turn on those are named in this plan's
ledger against task 7; everything else travels here, name unchanged.

Two things the rig recorded only in prose are pinned here as tests, because the
tasks that found them could not pin them at their own layer:

* the un-earning happens in the `finally`, and at that layer it is
  indistinguishable from an ordinary refused write. What tells them apart is a
  browser that goes away AFTER the write came back and BEFORE anything could
  look -- the step body is never reached, the step carries its write marker,
  and the run un-earns the job anyway.
* `_fell_over` stamps the step that was in flight, which is the only call in
  this system that hands the effects register a step whose `result` is `None`.
"""

import asyncio
import base64
from collections.abc import Mapping

import pytest

from sro.application.execution.run_workflow import (
    _bill,
    _fell_over,
    _look,
    _now,
    _result,
    _target_origin,
)
from sro.application.ports.channel import Reply
from sro.domain.execution.planning import Look, Planned
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from tests.unit.fakes import FakeChannel

TENANT = TenantId("acme")
"""The caller's tenant, which is also the evidence's: `gestures_for` is scoped
by it, so a job can only ever cite evidence filed under the tenant asking for
it. The workflow's own `tenant` field is deliberately something else in the
fixtures below -- see `_workflow` -- which is what keeps "the caller's tenant,
not the object's" checkable at all."""

DEVICE = DeviceId("dev_test")

# Never today. Every clock this suite reads is the module's own `_now`, and a
# fixture dated on the day it was written lets a run whose `started_at` came
# from somewhere else agree with it by the calendar.
STARTED = "2026-03-04T10:00:00+00:00"


def _bare_run(**over: object) -> WorkflowRun:
    base: dict[str, object] = {
        "id": "run_1",
        "tenant": "acme",
        "workflow_id": "wfl_1",
        "device_id": "dev_1",
        "values": {},
        "started_by": "form",
        "live": False,
        "allow_focus": True,
        "started_at": STARTED,
    }
    return WorkflowRun(**{**base, **over})  # type: ignore[arg-type]


def _step_record(**over: object) -> RunStep:
    return RunStep(**{"order": 0, "says": "s", "verdict": "skipped", **over})  # type: ignore[arg-type]


def _payload(sent: Mapping[str, object]) -> Mapping[str, object]:
    payload = sent["payload"]
    assert isinstance(payload, dict)
    return payload


# --------------------------------------------------------------------------
# What a step costs, and what the record keeps of what came back
# --------------------------------------------------------------------------


def test_a_step_is_billed_for_every_reading_it_took_and_for_none_it_did_not() -> None:
    """A step is planned once and verified once, and both readings are its
    cost. One unpriced reading makes the whole step's number untrustworthy."""
    record = _step_record()

    _bill(
        record,
        None,
        Answer(in_tokens=10, out_tokens=2, thought_tokens=1, cost_usd=0.001),
        Answer(in_tokens=5, out_tokens=3, thought_tokens=2, cost_usd=0.002, unpriced=True),
    )

    assert (record.in_tokens, record.out_tokens, record.thought_tokens) == (15, 5, 3)
    assert record.cost_usd == pytest.approx(0.003)
    assert record.unpriced is True, "one unpriced reading is an unpriced step"


def test_what_the_browser_answered_is_kept_and_what_it_answered_with_is_not() -> None:
    reply = Reply(
        ok=True,
        result={
            "status": 201,
            "matched_by": "component",
            "body": '{"clientCode":"ACME-4471"}',
            "headers": {"Set-Cookie": "session=abc"},
        },
    )

    assert _result(reply) == {"ok": True, "status": 201, "matched_by": "component"}
    assert _result(reply, wrote=True)["wrote"] is True

    refused = Reply(ok=False, error_kind="control_not_found", error_detail="no visible match")
    assert _result(refused) == {
        "ok": False,
        "status": None,
        "matched_by": None,
        "error_kind": "control_not_found",
    }


def test_a_reply_whose_status_and_match_are_not_what_they_claim_are_dropped() -> None:
    """New. The three facts are typed where they are read: `status` is compared
    against the evidence's own statuses and `matched_by` is compared against
    the locator ladder's names, and an extension answering a string status or a
    numeric match would put a value into the record that every later comparison
    silently fails."""
    odd = Reply(ok=True, result={"status": "201", "matched_by": 7})

    assert _result(odd) == {"ok": True, "status": None, "matched_by": None}


def test_the_origin_a_plan_would_reach_is_the_urls_for_the_two_kinds_that_leave() -> None:
    def _p(kind: str, payload: dict[str, object]) -> Planned:
        return Planned(kind, payload, "w", Answer())

    assert (
        _target_origin(_p("http.send", {"url": "https://wms.example/x"})) == "https://wms.example"
    )
    assert _target_origin(_p("navigate", {"url": "https://wms.example/x"})) == "https://wms.example"
    assert _target_origin(_p("navigate", {"url": "about:blank"})) is None
    assert (
        _target_origin(_p("ui.perform", {"origin": "https://wms.example", "url": "https://evil/x"}))
        == "https://wms.example"
    ), "ui.perform keeps the origin the evidence gave it"
    assert _target_origin(_p("ui.perform", {})) is None
    assert _target_origin(_p("ui.perform", {"origin": 7})) is None


# --------------------------------------------------------------------------
# A run that died, and the step it died on
# --------------------------------------------------------------------------


def test_a_run_that_died_between_steps_gets_a_step_of_its_own_to_say_so() -> None:
    run = _bare_run(steps=[_step_record(order=0), _step_record(order=1)])

    _fell_over(run, None, "the browser went away")

    assert run.outcome == "failed" and len(run.steps) == 3
    fresh = run.steps[-1]
    assert (fresh.order, fresh.says) == (2, ""), "past the last one, so (run_id, ord) cannot clash"
    assert (fresh.verdict, fresh.verdict_by, fresh.reason) == (
        "failed",
        "none",
        "the browser went away",
    )


def test_a_run_that_died_before_its_first_step_still_gets_step_zero() -> None:
    run = _bare_run(steps=[])
    _fell_over(run, None, "interrupted before finishing")
    assert [s.order for s in run.steps] == [0]


def test_a_run_that_died_mid_step_fails_that_step_and_keeps_what_it_cost() -> None:
    """Not a fabricated step: the one in flight, with its own order and the
    tokens its plan already spent."""
    in_flight = _step_record(order=4, says="save", in_tokens=300, cost_usd=0.0004)
    run = _bare_run(steps=[_step_record(order=3, verdict="held"), in_flight])

    _fell_over(run, in_flight, "the browser went away")

    assert len(run.steps) == 2 and run.steps[-1] is in_flight
    assert (in_flight.order, in_flight.in_tokens) == (4, 300)
    assert (in_flight.verdict, in_flight.verdict_by) == ("failed", "none")


def test_a_step_that_fell_over_carries_no_result_at_all() -> None:
    """New, and the shape the register of verified writes is handed. `wrote()`
    reads `step.result` and this is the only call in the system that leaves it
    `None` on a step whose verdict un-earns -- a step in flight sent nothing
    that came back, so it takes nothing away from the job."""
    in_flight = _step_record(order=1, says="save")

    _fell_over(_bare_run(steps=[in_flight]), in_flight, "gone")

    assert in_flight.result is None and in_flight.verdict == "failed"


def test_the_rig_stamps_its_times_in_utc() -> None:
    """Every other writer here produces UTC. A naive local stamp beside them
    reads as a run that finished hours before it started."""
    assert _now().endswith("+00:00")


# --------------------------------------------------------------------------
# The look: where the browser is and what is on the screen
# --------------------------------------------------------------------------


async def test_a_look_is_where_the_browser_is_and_what_is_on_the_screen() -> None:
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})],
            "screenshot": [
                Reply(
                    ok=True,
                    result={
                        "image_base64": base64.b64encode(b"png-bytes").decode(),
                        "text_digest": "Save",
                    },
                )
            ],
        }
    )

    look = await _look(channel, TENANT, DEVICE, "run_1", "http://127.0.0.1:63319", True)

    assert look == Look("http://127.0.0.1:63319/form", b"png-bytes", "Save")
    assert channel.sent == [
        {
            "tenant_id": "acme",
            "device_id": "dev_test",
            "kind": "ui.url",
            "run_id": "run_1",
            "payload": {"origin": "http://127.0.0.1:63319"},
        },
        {
            "tenant_id": "acme",
            "device_id": "dev_test",
            "kind": "screenshot",
            "run_id": "run_1",
            # inline, or the picture comes back as a url the backend would have
            # to fetch; allow_focus only when the run was given it.
            "payload": {
                "inline": True,
                "origin": "http://127.0.0.1:63319",
                "allow_focus": True,
            },
        },
    ]


async def test_a_look_a_run_may_not_take_focus_for_never_asks_for_it() -> None:
    channel = FakeChannel({"ui.url": [Reply(ok=True, result={"url": "http://x/"})]})
    await _look(channel, TENANT, DEVICE, "run_1", None, False)
    assert _payload(channel.sent[1]) == {"inline": True, "origin": None}


async def test_a_refused_screenshot_is_no_picture_rather_than_a_failure() -> None:
    """`focus_not_permitted` is the extension declining to steal the tab. The
    planner works from the url and the digest."""
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})],
            "screenshot": [Reply(ok=False, error_kind="focus_not_permitted", error_detail="no")],
        }
    )

    look = await _look(channel, TENANT, DEVICE, "run_1", None, True)

    assert look == Look("http://127.0.0.1:63319/form", None, "")


async def test_a_url_the_browser_did_not_actually_answer_is_not_where_it_is() -> None:
    for reply in (
        Reply(ok=False, error_kind="no_tab", error_detail="x", result={"url": "http://stale/"}),
        Reply(ok=True, result={}),
    ):
        channel = FakeChannel({"ui.url": [reply]})
        assert (await _look(channel, TENANT, DEVICE, "run_1", None, False)).url is None


async def test_a_picture_that_will_not_decode_is_no_picture_either() -> None:
    for raw in ("!!!not base64!!!", "", 17):
        channel = FakeChannel(
            {
                "ui.url": [Reply(ok=True, result={"url": "http://x/"})],
                "screenshot": [Reply(ok=True, result={"image_base64": raw, "text_digest": "d"})],
            }
        )
        look = await _look(channel, TENANT, DEVICE, "run_1", None, False)
        assert look.screenshot is None, raw
        assert look.digest == "d", "the text still reads even when the picture does not"


async def test_the_viewport_a_picture_shows_is_read_off_the_reply_it_came_with() -> None:
    """New. The width and height are the space a point acts in, and nothing in
    the rig's own suite ever asserted they arrive -- a `_look` that dropped them
    would leave every sight plan with a viewport of zero, which reads as "no
    screen to look at" rather than as a bug."""
    shot = {"image_base64": base64.b64encode(b"p").decode(), "width": 1280, "height": 720}
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://x/"})],
            "screenshot": [Reply(ok=True, result=shot)],
        }
    )

    look = await _look(channel, TENANT, DEVICE, "run_1", None, False)

    assert (look.width, look.height) == (1280, 720)


async def test_a_viewport_the_browser_gave_no_numbers_for_is_no_viewport() -> None:
    """New, and the half above it cannot say: a browser answering `"1280"` or
    nothing at all leaves the size at zero rather than putting a string where
    an int is compared."""
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://x/"})],
            "screenshot": [Reply(ok=True, result={"image_base64": "", "width": "1280"})],
        }
    )

    look = await _look(channel, TENANT, DEVICE, "run_1", None, False)

    assert (look.width, look.height) == (0, 0)


async def test_the_look_asks_the_browser_the_caller_named_under_the_run_it_is_for() -> None:
    """New, and not the rig's: its channel had no tenant. Both commands carry
    the caller's tenant, the caller's browser and this run's id -- the id is
    what the extension shows beside the tab it is driving, and the tenant is
    what stops a leaked device id from reaching somebody else's window."""
    channel = FakeChannel({"ui.url": [Reply(ok=True, result={"url": "http://x/"})]})

    await _look(channel, TenantId("someone-else"), DeviceId("dev_other"), "run_9", None, False)

    assert [(s["tenant_id"], s["device_id"], s["run_id"]) for s in channel.sent] == [
        ("someone-else", "dev_other", "run_9"),
        ("someone-else", "dev_other", "run_9"),
    ]


async def test_a_look_that_hangs_is_a_look_that_can_be_cancelled() -> None:
    """New. The shutdown path the run loop's `finally` exists for starts here:
    a browser that never answers leaves this awaiting forever, and the task is
    cancelled out of it rather than timing out on its own."""

    class _Hangs(FakeChannel):
        def __init__(self) -> None:
            super().__init__({})
            self.reached = asyncio.Event()

        async def send(self, *args: object, **kwargs: object) -> Reply:
            self.reached.set()
            await asyncio.Event().wait()
            raise AssertionError("never reached")

    channel = _Hangs()
    task = asyncio.create_task(_look(channel, TENANT, DEVICE, "run_1", None, False))
    await channel.reached.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
