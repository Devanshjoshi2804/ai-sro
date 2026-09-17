"""The loop that takes a mined job and performs it.

Ported from `new_agent_arch/tests/test_runner.py`, the largest file in the rig's
suite. It arrived in two halves, the way the module did: task 6 brought the
skeleton -- the claimed row read back as the authority for what was asked, look
-> plan -> perform -> verify -> record per step, the step budget, `_fell_over`,
and the orphan sweep at startup -- and task 7 brought the rungs and the gates on
top of it: the rescue, the rung that looks, the wider `may_write`, the writes a
dry run withholds, the wait for a person, `from_step` and earned autonomy. Both
halves are here; nothing of the rig's runner suite is still to come.

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
import json
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from sro.application.execution import run_workflow as runner_module
from sro.application.execution.approvals import K_APPROVAL_WAIT_S, Approvals
from sro.application.execution.run_workflow import (
    K_SAME_WRITE_WINDOW,
    K_STEP_SLACK,
    GatherValues,
    KnownFields,
    _bill,
    _fell_over,
    _look,
    _now,
    _refused_origin,
    _result,
    _saw_nothing,
    _target_origin,
    _withheld,
    fail_orphans,
    run_workflow,
    write_key,
)
from sro.application.execution.stops import Stops
from sro.application.ports.agent import DeviceUnreachable
from sro.application.ports.channel import Reply
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.belts import K_EARNED_RUNS, SCREEN_SCHEMA
from sro.domain.execution.gathering import Found, Gathered
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.planning import PLAN_SCHEMA, Look, Planned
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Action, Body, Call, Gesture, Target
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.repeats import K_MOST_ITEMS, Repeat
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import (
    FakeAsker,
    FakeChannel,
    FakeGestureRepository,
    FakeToolCallRepository,
    FakeUnitOfWork,
    FakeWorkflowRepository,
    FakeWorkflowRunRepository,
)

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
    return WorkflowRun(**{**base, **over})


def _step_record(**over: object) -> RunStep:
    return RunStep(**{"order": 0, "says": "s", "verdict": "skipped", **over})


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


STOOD = frozenset({"https://wms.example", "https://mail.example"})
CALLED = STOOD | {"https://api.wms.example", "https://play.google.com"}


def test_only_a_replay_may_reach_an_origin_nobody_stood_on() -> None:
    """The two sets are not interchangeable, and this is the difference.

    `http.send` replays a call this job's evidence already made, and a
    demonstrated write can be to an API origin the page itself never was --
    `wms.example` posting to `api.wms.example`. Refusing that refuses the step
    its own write.

    A NAVIGATE is a different act: it drives somebody's browser somewhere. A
    page calls whoever it likes, so allowing it everywhere the evidence's
    requests reached meant `https://play.google.com` -- a Gmail telemetry
    beacon -- was somewhere a planner could send an operator, on a job about
    warehouse customer types.
    """
    assert not _refused_origin(
        "http.send", "https://api.wms.example", standing=STOOD, replayable=CALLED
    )
    assert _refused_origin(
        "navigate", "https://api.wms.example", standing=STOOD, replayable=CALLED
    ), "a navigate reached an origin nobody ever stood on"
    assert _refused_origin(
        "navigate", "https://play.google.com", standing=STOOD, replayable=CALLED
    ), "a telemetry beacon is not a destination"


def test_an_origin_the_operator_stood_on_is_allowed_to_both() -> None:
    for kind in ("http.send", "navigate", "ui.perform"):
        assert not _refused_origin(kind, "https://wms.example", standing=STOOD, replayable=CALLED)


def test_a_kind_that_chooses_its_own_target_may_not_choose_nowhere() -> None:
    """`about:blank`, `file:`, a bare path. For the two kinds whose target the
    model picks that is a refusal; for the rest `None` means the recorder saw
    no url and the extension resolves it."""
    assert _refused_origin("navigate", None, standing=STOOD, replayable=CALLED)
    assert _refused_origin("http.send", None, standing=STOOD, replayable=CALLED)
    assert not _refused_origin("ui.perform", None, standing=STOOD, replayable=CALLED)


def test_an_origin_in_neither_set_is_refused_however_it_is_reached() -> None:
    for kind in ("http.send", "navigate", "ui.perform"):
        assert _refused_origin(kind, "https://evil.example", standing=STOOD, replayable=CALLED)


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
    async with asyncio.timeout(5):
        await channel.reached.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


# --------------------------------------------------------------------------
# A job walked end to end
# --------------------------------------------------------------------------


ELSEWHERE = "a-different-tenant"
"""The `tenant` on every workflow this suite builds, and a plant rather than a
plausible value.

The loop is handed a workflow AND a tenant, and only the tenant says whose
evidence this job may cite, whose run row this is and whose browser may be
driven. A fixture where the two agree cannot tell them apart: a loop that read
`workflow.tenant` wherever it should read the caller's would pass every test
below. So they disagree, and the evidence is filed under the caller's."""


async def _fixture() -> FakeUnitOfWork:
    """The measured batch, correlated and filed under the caller's tenant.

    `gestures()` mints a fresh id per call, so nothing here may call it twice
    and expect the same evidence: what was stored is read back off the
    repository, in the order it went in.
    """
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures(tuple(_gestures()))
    return uow


def _evidence(uow: FakeUnitOfWork) -> list[Gesture]:
    assert isinstance(uow.gestures, FakeGestureRepository)
    return list(uow.gestures.rows.values())


def _stale(uow: FakeUnitOfWork) -> dict[tuple[str, int], tuple[str | None, str]]:
    assert isinstance(uow.workflows, FakeWorkflowRepository)
    return uow.workflows.stale


def _effects(uow: FakeUnitOfWork) -> dict[tuple[str, str, int], tuple[str, str]]:
    assert isinstance(uow.workflows, FakeWorkflowRepository)
    return uow.workflows.effects


def _ids(uow: FakeUnitOfWork) -> list[str]:
    return [gesture.id for gesture in _evidence(uow)]


def _silent_click(uow: FakeUnitOfWork) -> str:
    """A click the recorder saw and heard no traffic from -- what a Save looks
    like when its call went out somewhere the recorder was not attached."""
    return next(g.id for g in _evidence(uow) if g.action.kind == "click" and not g.requests)


async def _workflow(uow: FakeUnitOfWork) -> Workflow:
    ids = _ids(uow)
    workflow = Workflow(
        id="wfl_1",
        tenant=ELSEWHERE,
        title="create a client",
        narrative="n",
        # A system the evidence does not name, and a plant rather than a
        # plausible value. The allowlist is every system the workflow's own
        # cited evidence names and deliberately ignores this field -- a fixture
        # where the two agree cannot tell them apart, and a loop that read
        # `systems` here would let a plan reach a host nothing was recorded on.
        # `test_an_origin_outside_the_evidence_is_refused_before_it_is_sent`
        # navigates to exactly this one.
        systems=["http://127.0.0.1:63319", "https://evil.example"],
        steps=[
            Step(
                order=0,
                says="type the code",
                system=None,
                cites=[ids[0]],
                parameters=["clientCode"],
            ),
            Step(order=1, says="save", system=None, cites=[ids[-1]]),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["A", "B"]}],
    )
    await uow.workflows.save(workflow)
    return workflow


async def _one_step(
    uow: FakeUnitOfWork, cite: str, says: str = "save", *, parameters: list[str] | None = None
) -> Workflow:
    """One step citing one gesture.

    `parameters` defaults to `["clientCode"]` because most of these steps type
    it. Pass `[]` for a step the run performs as a CLICK that was given a
    value: `plan_step` answers such a step with two clicks -- one to open the
    list, one on the row whose text is the value -- and refuses it outright
    when the step also writes. Either way it is not the plain single click most
    of these tests are about.
    """
    workflow = Workflow(
        id="wfl_one",
        tenant=ELSEWHERE,
        title=says,
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(
                order=0,
                says=says,
                system=None,
                cites=[cite],
                parameters=["clientCode"] if parameters is None else parameters,
            )
        ],
    )
    await uow.workflows.save(workflow)
    return workflow


async def _repeated(uow: FakeUnitOfWork, steps: int) -> Workflow:
    """One workflow of `steps` identical read steps, all citing the same typed
    gesture. Nothing here writes, so every step is performable in a live run."""
    typed = _ids(uow)[0]
    workflow = Workflow(
        id="wfl_n",
        tenant=ELSEWHERE,
        title="type it again",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(
                order=i,
                says="type the code",
                system=None,
                cites=[typed],
                parameters=["clientCode"],
            )
            for i in range(steps)
        ],
    )
    await uow.workflows.save(workflow)
    return workflow


def _looks(n: int) -> dict[str, list[Reply]]:
    return {
        "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * n,
        "screenshot": [Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "Save"})]
        * n,
    }


def _plan(action: str, value: str | None = None) -> Answer:
    return Answer(
        data={"kind": "ui.perform", "action": action, "value": value, "url": None, "why": "w"},
        cost_usd=0.001,
    )


def _navigate(url: str = "http://127.0.0.1:63319/form") -> Answer:
    return Answer(
        data={"kind": "navigate", "action": None, "value": None, "url": url, "why": "wrong page"}
    )


def _replay() -> Answer:
    """The planner's one way to send a write as a call: replay the recorded
    one. The url is never the model's -- `plan_step` takes it off the
    evidence -- so `url: None` here is the honest shape of that answer."""
    return Answer(
        data={"kind": "http.send", "action": None, "value": None, "url": None, "why": "w"}
    )


def _performed(matched_by: str = "component") -> Reply:
    return Reply(ok=True, result={"performed": True, "matched_by": matched_by, "candidates": 1})


class _Gone(FakeChannel):
    """A browser that is not there at all -- the real channel's answer to a
    device id with no socket open behind it."""

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        raise DeviceUnreachable(f"{device_id} has no channel open")


class _GoesAway(FakeChannel):
    """A browser that stops listening on the nth `ui.perform`."""

    def __init__(self, script: dict[str, list[Reply]], on_perform: int) -> None:
        super().__init__(script)
        self.on_perform = on_perform
        self.performs = 0

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        if kind == "ui.perform":
            self.performs += 1
            if self.performs >= self.on_perform:
                raise DeviceUnreachable(f"{device_id} stopped listening")
        return await super().send(
            tenant_id, device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )


class _AbortIsGone(FakeChannel):
    """A browser that answers everything but the stop command."""

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        if kind == "abort":
            raise DeviceUnreachable(f"{device_id} stopped listening")
        return await super().send(
            tenant_id, device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )


class _Breaks(FakeChannel):
    """A channel that raises something nobody planned for."""

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        if kind == "ui.perform":
            raise RuntimeError("boom")
        return await super().send(
            tenant_id, device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )


class _PerSchemaAsker(FakeAsker):
    """`FakeAsker`, answered by schema rather than by call order.

    A run asks a different number of questions depending on which belt verifies
    each step, and a positional queue has to be rewritten every time that number
    moves. This one answers `verdict` to a verification and `plan` to everything
    else, and still records every call in `.asked`.
    """

    def __init__(self, plan: Answer, verdict: Answer) -> None:
        super().__init__()
        self.plan, self.verdict = plan, verdict

    async def ask(self, **asked: object) -> Answer:
        await super().ask(**asked)
        schema = asked["schema"]
        assert isinstance(schema, dict)
        return self.verdict if "held" in schema["properties"] else self.plan


async def _earn(uow: FakeUnitOfWork, workflow: Workflow) -> None:
    """This job has earned the right to write without asking a person first.

    `K_EARNED_RUNS` live runs that held, each with every write of theirs in the
    register of verified effects -- which is what `earned_from` counts. Seeded
    rather than performed: the arithmetic has its own tests, and what this
    suite is about is which of a run's steps stop and ask.
    """
    for nth in range(K_EARNED_RUNS):
        proof = _bare_run(
            id=f"run_earned_{nth}",
            workflow_id=workflow.id,
            live=True,
            outcome="held",
            finished_at=STARTED,
            steps=[_step_record(verdict="held", verdict_by="status", result={"wrote": True})],
        )
        await uow.workflow_runs.save(proof)
        await uow.workflows.record_effect(
            workflow.id, run_id=proof.id, ord_=0, verified_by="status", at=STARTED
        )


async def _ran(
    uow: FakeUnitOfWork,
    workflow: Workflow,
    *,
    channel: FakeChannel,
    asker: FakeAsker,
    values: Mapping[str, str] | None = None,
    live: bool = True,
    allow_focus: bool = True,
    watched: bool = False,
    started_by: str = "form",
    tenant_id: TenantId = TENANT,
    device_id: DeviceId = DEVICE,
    stops: Stops | None = None,
    approvals: Approvals | None = None,
    run_id: str | None = None,
    items: Sequence[Mapping[str, str]] = (),
    plan_model: str = "flash",
    rescue_model: str = "pro",
    earned: bool = False,
    from_step: int = 0,
    cap_usd: float = -1.0,
    verified_writes: tuple[VerifiedWrite, ...] = (),
    known_fields: KnownFields | None = None,
    gather_values: GatherValues | None = None,
) -> WorkflowRun:
    """One run, with the arguments no test varies spelled once.

    `earned` says the job has already proved it can write, which is the only
    way a live write goes out without a person tapping approve. Five seconds
    rather than no deadline, because a run that parks waits `K_APPROVAL_WAIT_S`
    -- five minutes -- and a test that meant to earn and forgot should fail
    here rather than hang the suite.
    """
    if earned:
        await _earn(uow, workflow)
    return await asyncio.wait_for(
        run_workflow(
            uow,
            workflow,
            tenant_id=tenant_id,
            values={"clientCode": "x"} if values is None else values,
            channel=channel,
            device_id=device_id,
            asker=asker,
            plan_model=plan_model,
            rescue_model=rescue_model,
            live=live,
            allow_focus=allow_focus,
            watched=watched,
            started_by=started_by,
            stops=stops or Stops(),
            approvals=approvals or Approvals(),
            run_id=run_id,
            from_step=from_step,
            items=items,
            verified_writes=verified_writes,
            known_fields=known_fields,
            gather_values=gather_values,
            # No cap unless a test is about the cap: `over_cap` answers a
            # negative one before it touches the repository, so every other
            # test here pays nothing and asserts nothing about money.
            cap_usd=cap_usd,
        ),
        timeout=5,
    )


async def test_a_live_run_sends_the_write() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = FakeAsker(
        _plan("type", "THIRD"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"}, earned=True
    )

    assert [s.verdict for s in run.steps] == ["held", "held"] and not run.withheld
    performed = [s for s in channel.sent if s["kind"] == "ui.perform"]
    assert len(performed) == 2 and _payload(performed[0])["value"] == "THIRD"
    assert run.outcome == "held"
    assert [_payload(p).get("allow_focus") for p in performed] == [True, True], (
        "the run's answer on focus reaches the command. The only other"
        " assertion on this field is the negative one in"
        " `test_the_claimed_row_says_what_the_run_is_doing_and_the_arguments_do_not`,"
        " which a caller passing a hardcoded False satisfies just as well"
    )


async def test_the_run_is_saved_after_every_step_and_not_only_at_the_end() -> None:
    """New. The panel polls the row while the run is in flight, and a loop that
    saved once at the end would show a job that does nothing for a minute and
    then everything at once. The rig wrote this in its module docstring and
    nothing held it to it."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))
    seen: list[int] = []

    # Earned before the watch goes on, so the saves counted are this run's.
    await _earn(uow, workflow)
    saved = uow.workflow_runs.save

    async def _watch(run: WorkflowRun) -> None:
        seen.append(len([s for s in run.steps if s.verdict != "skipped"]))
        await saved(run)

    uow.workflow_runs.save = _watch  # type: ignore[method-assign]
    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "held"
    # Claimed with nothing done, then once per step, then the finish.
    assert seen == [0, 1, 2, 2]


async def test_an_origin_outside_the_evidence_is_refused_before_it_is_sent() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(_looks(2))
    asker = FakeAsker(_navigate("https://evil.example/x"))

    run = await _ran(uow, workflow, channel=channel, asker=asker, values={})

    assert run.outcome == "refused" and run.steps[0].verdict == "refused"
    assert "evil.example" in run.steps[0].reason
    assert not [s for s in channel.sent if s["kind"] == "navigate"], "nothing left the process"


async def test_a_navigate_to_a_url_that_names_no_system_is_refused() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(_looks(2))
    asker = FakeAsker(_navigate("about:blank"))

    run = await _ran(uow, workflow, channel=channel, asker=asker, values={})

    assert run.outcome == "refused" and run.steps[0].verdict == "refused"
    assert "about:blank" in run.steps[0].reason
    assert not [s for s in channel.sent if s["kind"] == "navigate"], "no origin is not permission"


async def test_a_navigate_gets_to_the_page_and_does_not_spend_the_rescue() -> None:
    """A deep job was demonstrated across several screens. Moving to the next
    one is not doing the step: after the navigate the same step is planned
    again on the same rung, so a step that needed a page change and then went
    wrong still has its one rescue.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(6),
            "navigate": [Reply(ok=True, result={"navigated": True})],
            "ui.perform": [_performed()],
        }
    )
    asker = FakeAsker(
        _navigate(),
        _plan("type", "x"),
        Answer(data={"held": True, "why": ""}),
        # The save below is withheld, so nothing after this one goes out.
        _plan("click"),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker, live=False)

    assert [s["kind"] for s in channel.sent if s["kind"] in ("navigate", "ui.perform")] == [
        "navigate",
        "ui.perform",
    ]
    moved = next(s for s in channel.sent if s["kind"] == "navigate")
    assert _payload(moved)["url"] == "http://127.0.0.1:63319/form", "the url the model gave"
    assert run.steps[0].verdict == "held" and run.steps[0].planned_by == "flash", (
        "the rescue was never needed"
    )


async def test_a_navigate_that_would_not_go_is_the_step_that_failed() -> None:
    """New. The rig had no test for a browser that refuses the move, and the
    difference matters: the reason names the browser's own words rather than
    leaving the step reading `skipped` and the run walking past it."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            # Two rungs: a rung that reached no command at all is not a write,
            # so the rescue is not spent and the second one moves too.
            **_looks(4),
            "navigate": [Reply(ok=False, error_kind="no_tab", error_detail="that window is gone")]
            * 2,
        }
    )
    asker = FakeAsker(_navigate(), _navigate())

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "stopped" and run.steps[0].verdict == "failed"
    assert "that window is gone" in run.steps[0].reason


async def test_a_planner_that_only_ever_navigates_stops_rather_than_going_round() -> None:
    """New, and the half of the navigate rule the budget test cannot see: a
    second navigate for one step is a planner going round in circles, not a
    plan, and the step fails on the spot."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(8),
            "navigate": [Reply(ok=True, result={"navigated": True})] * 4,
        }
    )
    asker = FakeAsker(*[_navigate()] * 4)

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "stopped" and run.steps[0].verdict == "failed"
    assert "wrong page" in run.steps[0].reason
    assert len([s for s in channel.sent if s["kind"] == "navigate"]) == 2, (
        "once per rung, and never twice within one: the second navigate of a rung"
        " is the planner going round, and the rung ends there"
    )


async def test_a_weak_locator_match_succeeds_and_flags_the_step_stale() -> None:
    """The second step is the weak one, so the row is against the step that
    matched weakly and not against whichever step happened to be first."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    await _claimed(uow, live=True)
    channel = FakeChannel(
        {**_looks(4), "ui.perform": [_performed("component"), _performed("css_path")]}
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    run = await _ran(uow, workflow, channel=channel, asker=asker, run_id="run_claimed", earned=True)

    assert [s.stale for s in run.steps] == [False, True]
    assert run.steps[1].verdict == "held" and run.steps[1].matched_by == "css_path"
    marked = _stale(uow)
    assert list(marked) == [("wfl_1", 1)], "one row, for the step that matched weakly"
    matched_by, noticed_at = marked[("wfl_1", 1)]
    assert matched_by == "css_path", "and it says which rung found it"
    assert noticed_at.endswith("+00:00"), "in UTC"
    assert noticed_at > run.started_at, "stamped when it was noticed, not when the run began"


async def test_a_step_found_the_strong_way_again_clears_its_stale_mark() -> None:
    """A warning that never clears is a warning nobody reads: the page is not
    moving under the job after all.

    The step that recovers is the SECOND one, and the first goes weak in the
    same run, so a loop that cleared step zero's mark whatever step it was on
    would leave the register the wrong way round rather than merely tidy.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    await uow.workflows.mark_stale("wfl_1", 0, matched_by="css_path", noticed_at=STARTED)
    await uow.workflows.mark_stale("wfl_1", 1, matched_by="css_path", noticed_at=STARTED)
    channel = FakeChannel(
        {**_looks(4), "ui.perform": [_performed("css_path"), _performed("component")]}
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    run = await _ran(uow, workflow, channel=channel, asker=asker, earned=True)

    assert [s.stale for s in run.steps] == [True, False]
    assert set(_stale(uow)) == {("wfl_1", 0)}, "only the step that matched strongly is cleared"


async def test_the_stop_button_is_honoured_between_steps() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed()],
            "abort": [Reply(ok=True, result={"aborted": True})],
        }
    )
    asker = FakeAsker(_plan("type", "x"), Answer(data={"held": True, "why": ""}))
    stops = Stops()
    stops.ask("run_stop")

    run = await _ran(uow, workflow, channel=channel, asker=asker, stops=stops, run_id="run_stop")

    assert run.outcome == "aborted" and run.steps == []
    assert [s["kind"] for s in channel.sent] == ["abort"], "the browser was told, and nothing else"
    assert _payload(channel.sent[0]) == {"run_id": "run_stop"}


async def test_a_run_stopped_by_the_flag_is_forgotten_by_the_register_when_it_ends() -> None:
    """Nothing outlives the run in the in-process register, or the next run
    under that id would inherit a stop it never asked for."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(2), "abort": [Reply(ok=True, result={"aborted": True})]})
    stops = Stops()
    stops.ask("run_forget_me")

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=FakeAsker(),
        stops=stops,
        run_id="run_forget_me",
    )

    assert run.outcome == "aborted"
    assert not stops.asked("run_forget_me"), "the finally forgets the flag"


async def test_the_step_budget_is_the_workflows_steps_plus_slack() -> None:
    """Every attempt counts against it, including the ones that only moved the
    browser, so a planner that navigates its way around a job runs out before
    it has spent the day."""
    uow = await _fixture()
    workflow = await _repeated(uow, 4)
    assert K_STEP_SLACK == 3
    budget = len(workflow.steps) + K_STEP_SLACK
    channel = FakeChannel(
        {
            **_looks(budget * 2),
            "navigate": [Reply(ok=True, result={"navigated": True})] * len(workflow.steps),
            "ui.perform": [_performed()] * len(workflow.steps),
        }
    )
    # Every step is asked twice: once for the navigate that gets to the page,
    # once for the command itself. Three steps at two attempts each spends six
    # of the seven, and the fourth step's navigate spends the last.
    asker = FakeAsker(
        *[
            answer
            for _ in range(3)
            for answer in (_navigate(), _plan("type", "x"), Answer(data={"held": True, "why": ""}))
        ],
        _navigate(),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "refused"
    last = run.steps[-1]
    assert last.order == 3 and last.verdict == "refused", "the budget stopped the last step"
    assert str(budget) in last.reason and "budget" in last.reason
    assert len([a for a in asker.asked if a["schema"] is PLAN_SCHEMA]) == budget


async def test_every_model_call_on_a_run_is_billed_to_its_step() -> None:
    """And all five of the run's numbers are the sum of the steps underneath.

    `_save`'s own claim: "a run saved without its steps summed is a row whose
    bill disagrees with the steps underneath it, and the panel reads the row."
    Cost was the only one of the five under a test, so zeroing any of the three
    token roll-ups -- or falsifying `unpriced` -- passed the whole suite.

    `unpriced` is not cosmetic. The daily-cap query reads that column off this
    row, so a roll-up that quietly stops working under-reports unpriced spend
    rather than showing nothing at all.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()]})
    asker = FakeAsker(
        Answer(
            data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""},
            cost_usd=0.002,
            in_tokens=100,
            out_tokens=10,
            thought_tokens=7,
        ),
        Answer(data={"held": True, "why": ""}, cost_usd=0.001, in_tokens=50, out_tokens=5),
        # The second step's plan came back with no price on it -- a reading the
        # vendor reported no usage for. The step carries the mark, and a run
        # whose steps carry one is an unpriced run.
        Answer(
            data={"kind": "ui.perform", "action": "click", "value": None, "url": None, "why": ""},
            in_tokens=9,
            out_tokens=3,
            thought_tokens=1,
            unpriced=True,
        ),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker, live=False)

    assert run.steps[0].cost_usd == pytest.approx(0.003) and run.steps[0].in_tokens == 150
    assert [s.unpriced for s in run.steps] == [False, True], "one of the two was unpriced"
    totals = (run.in_tokens, run.out_tokens, run.thought_tokens, run.unpriced)
    assert totals == (
        sum(s.in_tokens for s in run.steps),
        sum(s.out_tokens for s in run.steps),
        sum(s.thought_tokens for s in run.steps),
        any(s.unpriced for s in run.steps),
    )
    assert totals == (159, 18, 8, True), "and the sums are the numbers the readings carried"
    assert run.cost_usd == pytest.approx(sum(s.cost_usd for s in run.steps))
    stored = await uow.workflow_runs.get(TENANT, run.id)
    assert stored is not None and stored.cost_usd == pytest.approx(run.cost_usd), "and it is saved"
    assert (
        stored.in_tokens,
        stored.out_tokens,
        stored.thought_tokens,
        stored.unpriced,
    ) == totals, "the row the panel and the daily cap read carries all five"


async def test_a_browser_that_went_away_fails_the_run_and_says_so() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)

    run = await _ran(uow, workflow, channel=_Gone(), asker=FakeAsker(), values={})

    assert run.outcome == "failed" and "dev_test" in run.steps[0].reason


async def test_a_step_the_planner_could_not_plan_stops_the_run() -> None:
    """A rung that never reached a command left its reason on nothing but a
    local, and the run walked past the step as if it had been skipped.

    Both evidence rungs are asked and neither reaches a command; the sight
    rung is not, because nothing came back from a browser to say the control
    was the thing that could not be found.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(_looks(4))
    asker = FakeAsker(*[Answer(data={"kind": "nope", "why": "no idea"})] * 2)

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "stopped"
    assert [a["model"] for a in asker.asked] == ["flash", "pro"], "step 1 was never planned"
    assert not [s for s in channel.sent if s["kind"] == "ui.perform"], "nothing was performed"
    assert run.steps[0].verdict == "failed" and run.steps[0].reason, "it says why"


async def test_a_step_that_reached_no_command_claims_to_have_sent_nothing() -> None:
    """New. The record's `sent` and `planned_by` are what a reader takes for
    "this went out", and a plan of kind `none` sent nothing at all -- leaving
    them set would put a command beside a verdict that nothing performed."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    asker = FakeAsker(Answer(data={"kind": "nope", "why": "no idea"}))

    run = await _ran(uow, workflow, channel=FakeChannel(_looks(2)), asker=asker)

    assert run.steps[0].sent is None and run.steps[0].planned_by is None


async def test_a_step_with_nothing_actionable_to_cite_stops_the_run() -> None:
    """You scroll a page, not a control. A step whose whole evidence is a
    scroll cannot be performed, and a job that carries on past it is a job
    doing its later steps on an assumption nobody checked."""
    uow = await _fixture()
    original = _evidence(uow)[0]
    scrolled = replace(
        original,
        id="ges_scrolled",
        action=replace(original.action, kind="scroll", target=None, value=None),
    )
    await uow.gestures.add_gestures((scrolled,))
    workflow = await _workflow(uow)
    workflow.steps[0].cites = [scrolled.id]
    channel = FakeChannel(_looks(4))
    asker = FakeAsker(_plan("click"))

    run = await _ran(uow, workflow, channel=channel, asker=asker, values={})

    assert run.outcome == "stopped"
    assert len(run.steps) == 1 and run.steps[0].verdict == "skipped"
    assert run.steps[0].reason == "no cited gesture can be acted on"
    assert not asker.asked and not channel.sent, "nothing was planned and nothing was sent"


async def test_the_record_keeps_what_the_browser_answered_not_what_it_answered_with() -> None:
    """`verify` keeps a response body out of a prompt; the run record holds it
    for far longer than a prompt does, so it does not hold it at all."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1])
    channel = FakeChannel(
        {
            **_looks(2),
            "http.send": [
                Reply(
                    ok=True,
                    result={
                        "status": 200,
                        "body": '{"id": 41, "clientCode": "ACME-4471"}',
                        "headers": {"set-cookie": "session=secret"},
                    },
                )
            ],
        }
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=FakeAsker(_replay()), values={}, earned=True
    )

    assert run.steps[0].verdict == "held" and run.steps[0].verdict_by == "status"
    assert run.steps[0].result == {
        "ok": True,
        "status": 200,
        "matched_by": None,
        "wrote": True,
    }, "the three facts and the write marker; not the body, not the cookie"


async def test_a_failed_reply_keeps_the_error_kind_as_its_own_field() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [Reply(ok=False, error_kind="control_not_found", error_detail="gone")],
        }
    )
    asker = FakeAsker(_plan("type", "x"))

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.steps[0].result == {
        "ok": False,
        "status": None,
        "matched_by": None,
        "error_kind": "control_not_found",
    }
    assert "gone" in run.steps[0].reason, (
        "the detail is in the reason, not concatenated into a kind"
    )
    assert run.steps[0].matched_by is None, "a command that failed matched nothing"


def _only_run(uow: FakeUnitOfWork) -> WorkflowRun:
    assert isinstance(uow.workflow_runs, FakeWorkflowRunRepository)
    (row,) = uow.workflow_runs.rows.values()
    return row


async def test_a_browser_that_goes_away_mid_step_fails_that_step() -> None:
    """The step in flight is the one that failed -- with the step of the job it
    was on and the tokens its plan already cost -- not a fabricated one whose
    place in the run collides with a real step's.

    `order` is where in the RUN a row sits and `of_step` is which step of the
    job it is. They are the same number for a job whose steps are numbered from
    zero, which is every mined job; this fixture numbers from one on purpose,
    which is what makes the two visible apart."""
    uow = await _fixture()
    typed = _ids(uow)[0]
    workflow = Workflow(
        id="wfl_ordered",
        tenant=ELSEWHERE,
        title="two",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(order=1, says="type the code", system=None, cites=[typed]),
            Step(order=2, says="type it again", system=None, cites=[typed]),
        ],
    )
    await uow.workflows.save(workflow)
    channel = _GoesAway({**_looks(4), "ui.perform": [_performed()]}, on_perform=2)
    asker = FakeAsker(
        _plan("type", "x"),
        Answer(data={"held": True, "why": ""}),
        Answer(
            data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""},
            in_tokens=11,
        ),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "failed"
    assert [s.of_step for s in run.steps] == [1, 2], "the step in flight lost which step it was"
    assert [s.order for s in run.steps] == [0, 1], "two rows of one run collided on their place"
    assert run.steps[1].verdict == "failed" and "dev_test" in run.steps[1].reason
    assert run.steps[1].in_tokens == 11, "the plan it already paid for is still billed"
    saved = await uow.workflow_runs.get(TENANT, run.id)
    assert saved is not None and saved.outcome == "failed", "and it was saved"


async def test_a_run_that_dies_of_something_unexpected_is_not_left_saying_running() -> None:
    """The exception is nobody's to swallow; the record is nobody's to lose."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = _Breaks(_looks(4))
    asker = FakeAsker(_plan("type", "x"))

    with pytest.raises(RuntimeError):
        await _ran(uow, workflow, channel=channel, asker=asker)

    saved = _only_run(uow)
    assert saved.outcome == "failed" and saved.finished_at is not None
    assert "RuntimeError" in saved.steps[-1].reason and "boom" in saved.steps[-1].reason


async def test_a_run_cancelled_mid_step_is_not_left_saying_running() -> None:
    """Shutdown cancels the task. `CancelledError` is a BaseException, so
    neither `except` clause runs -- only the `finally`, which must still finish
    the record rather than leave a row that says `running` for good."""
    uow = await _fixture()
    workflow = await _workflow(uow)

    class _Hangs(FakeChannel):
        def __init__(self) -> None:
            super().__init__({})
            self.reached = asyncio.Event()

        async def send(
            self,
            tenant_id: TenantId,
            device_id: DeviceId,
            *,
            kind: str,
            payload: Mapping[str, object],
            run_id: str | None = None,
            deadline_s: float | None = None,
        ) -> Reply:
            self.reached.set()
            await asyncio.Event().wait()
            raise AssertionError("never reached")

    channel = _Hangs()
    task = asyncio.create_task(_ran(uow, workflow, channel=channel, asker=FakeAsker(), live=False))
    # Bounded, so a loop that never looks fails this test rather than hanging
    # the suite: a mutation that skipped the look was found exactly this way.
    async with asyncio.timeout(5):
        await channel.reached.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    saved = _only_run(uow)
    assert saved.outcome == "failed"
    assert saved.steps[-1].reason == "interrupted before finishing"
    assert saved.steps[-1].order == 0, "the step it was working on, not a fabricated one"


# --------------------------------------------------------------------------
# The claimed row is the authority for what the run is doing
# --------------------------------------------------------------------------


async def _claimed(uow: FakeUnitOfWork, **fields: object) -> WorkflowRun:
    """The row `POST /v1/runs` writes before it answers."""
    run = WorkflowRun(
        id="run_claimed",
        tenant=TENANT.value,
        workflow_id="wfl_1",
        device_id=DEVICE.value,
        values={},
        started_by="form",
        live=False,
        allow_focus=True,
        started_at=STARTED,
    )
    for name, value in fields.items():
        setattr(run, name, value)
    await uow.workflow_runs.save(run)
    return run


@pytest.mark.parametrize(
    ("field", "value"), [("device_id", "dev_other"), ("workflow_id", "wfl_other")]
)
async def test_a_claimed_run_that_disagrees_with_its_arguments_is_refused(
    field: str, value: str
) -> None:
    """The saved row is the authority for what a run is doing, so the two ways
    into this function must agree. Driving the row's browser instead of the
    caller's would put a hand on a window nobody asked about; driving the row's
    workflow would perform a different job under this one's id. Neither is a
    thing to guess between, and neither marks the row failed -- it belongs to
    whoever saved it."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    await _claimed(uow, **{field: value})
    channel = FakeChannel(_looks(4))

    with pytest.raises(ValueError, match="run_claimed"):
        await _ran(
            uow,
            workflow,
            channel=channel,
            asker=FakeAsker(),
            values={},
            run_id="run_claimed",
        )

    assert channel.sent == [], "refused before anything reached a browser"
    still = await uow.workflow_runs.get(TENANT, "run_claimed")
    assert still is not None and still.outcome == "running" and still.finished_at is None
    assert getattr(still, field) == value, "the row is left exactly as its owner saved it"


@pytest.mark.parametrize("outcome", ["held", "failed", "aborted"])
async def test_a_claimed_run_that_has_already_finished_is_not_performed_again(
    outcome: str,
) -> None:
    """New, and a deliberate divergence from the rig, which refuses on the row's
    browser and its job but not on whether the row is still running.

    Picked up anyway, a finished row plans its first step and pays for the model
    call before the send is blocked, then saves a step that never happened
    against an outcome from a run that ended some other day. Nothing re-presses
    a finished run today; phase 4's route will.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    await _claimed(uow, outcome=outcome, finished_at=STARTED)
    channel = FakeChannel(_looks(4))
    asker = FakeAsker(_plan("type", "x"))

    with pytest.raises(ValueError, match=f"run_claimed was saved {outcome}"):
        await _ran(uow, workflow, channel=channel, asker=asker, values={}, run_id="run_claimed")

    assert channel.sent == [] and asker.asked == [], "refused before it cost anything"
    still = await uow.workflow_runs.get(TENANT, "run_claimed")
    assert still is not None and still.outcome == outcome and still.steps == []


@pytest.mark.parametrize(("claimed", "asked"), [(1, 0), (0, 1)])
async def test_a_re_press_that_moves_from_step_is_refused_rather_than_performed(
    claimed: int, asked: int
) -> None:
    """The fourth thing the row is the authority for. Claim a run at
    `from_step=1`, re-enter it at `from_step=0`, and the operator's step is
    redone against a live warehouse -- silently, because the other three checks
    all pass. The other direction is the same defect wearing the opposite face:
    a step nobody performed is recorded `done_by_operator` and skipped.

    Both directions, because a check written against a constant -- `!= 0`
    rather than `!= from_step` -- catches exactly one of them.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    await _claimed(uow, from_step=claimed)
    channel = FakeChannel(_looks(4))
    asker = FakeAsker(_plan("click"))

    # Both halves of the sentence, not just the saved one. Matching only what
    # the row holds leaves the refusal free to stop naming what the caller
    # ASKED for -- and a message that says "this run is at step 1" without
    # saying "you pressed for 0" is one nobody can act on. Deleting the
    # ` from step {from_step}` clause left 2389 tests green until this line.
    with pytest.raises(
        ValueError,
        match=f"run_claimed was saved .*from step {claimed}, not running .*from step {asked}",
    ):
        await _ran(
            uow,
            workflow,
            channel=channel,
            asker=asker,
            values={},
            run_id="run_claimed",
            from_step=asked,
        )

    assert channel.sent == [] and asker.asked == [], "refused before it cost anything"
    still = await uow.workflow_runs.get(TENANT, "run_claimed")
    assert still is not None and still.from_step == claimed and still.steps == []


async def test_a_re_press_that_agrees_on_from_step_finishes_the_job_it_was_claimed_for() -> None:
    """The other half of the crossing: a claimed row and an argument that agree
    on a *non-zero* `from_step` is performed, so the refusal above is a
    comparison and not a rule against resuming at all."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    await _claimed(uow, from_step=1, live=True)
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(
        plan=_plan("click"), verdict=Answer(data={"held": True, "why": "saved"})
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        run_id="run_claimed",
        earned=True,
        from_step=1,
    )

    assert [s.verdict for s in run.steps] == ["done_by_operator", "held"]
    assert run.from_step == 1, "and the row still says what it was claimed for"


async def test_the_claimed_row_says_what_the_run_is_doing_and_the_arguments_do_not() -> None:
    """New, and the rule the rig wrote down in a comment: the row `POST /v1/runs`
    saved is read back rather than rebuilt here, so there is one answer to "what
    is this run doing" and not two that can drift. Every argument the row
    carries is given the opposite value at the call, and the row's wins."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    await _claimed(
        uow,
        workflow_id="wfl_one",
        live=True,
        allow_focus=False,
        values={"clientCode": "CLAIMED"},
        started_by="offer",
    )
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", None), verdict=Answer(data={"held": True}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "ARGUMENT"},
        live=False,
        allow_focus=True,
        started_by="form",
        run_id="run_claimed",
    )

    assert (run.live, run.allow_focus, run.started_by) == (True, False, "offer")
    assert run.values == {"clientCode": "CLAIMED"} and run.started_at == STARTED
    performed = next(s for s in channel.sent if s["kind"] == "ui.perform")
    assert _payload(performed)["value"] == "CLAIMED", "the row's values are what it types"
    assert "allow_focus" not in _payload(performed), "and the row's answer on focus"
    shots = [_payload(s) for s in channel.sent if s["kind"] == "screenshot"]
    assert len(shots) == 2 and not [s for s in shots if "allow_focus" in s], (
        "every look this run took, the one after the command included -- a run"
        " told not to take the operator's tab must not take it to verify either"
    )


async def test_a_run_nobody_claimed_gets_an_id_and_a_row_before_its_first_command() -> None:
    """New. The row exists before anything is sent, which is what makes a
    second press for the same browser a 409 rather than two hands on one
    window -- and a run that dies on its first look still leaves a record."""
    uow = await _fixture()
    workflow = await _workflow(uow)

    run = await _ran(uow, workflow, channel=_Gone(), asker=FakeAsker(), values={})

    assert run.id.startswith("run_") and len(run.id) == 36
    stored = await uow.workflow_runs.get(TENANT, run.id)
    assert stored is not None and stored.tenant == TENANT.value
    assert stored.workflow_id == workflow.id and stored.device_id == DEVICE.value


# --------------------------------------------------------------------------
# What a run's writes buy the job, and what one bad write costs it
# --------------------------------------------------------------------------


class _GoesAwayAfterTheWrite(FakeChannel):
    """A browser that answers the write and is gone before anyone can look."""

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        if any(s["kind"] == "http.send" for s in self.sent):
            raise DeviceUnreachable(f"{device_id} stopped listening")
        return await super().send(
            tenant_id, device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )


async def test_a_held_write_verified_by_state_is_recorded_as_an_effect() -> None:
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1])
    await _claimed(uow, workflow_id="wfl_one", live=True, started_by="offer")
    channel = FakeChannel(
        {
            **_looks(4),
            # 200 is what the capture's POST returned, and `expected_statuses`
            # is what "held by status" is measured against.
            "http.send": [Reply(ok=True, result={"status": 200, "body": "{}", "headers": {}})],
        }
    )
    asker = _PerSchemaAsker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        run_id="run_claimed",
        earned=True,
    )

    assert run.outcome == "held"
    assert run.steps[-1].result is not None and run.steps[-1].result.get("wrote") is True
    assert [key for key in _effects(uow) if key[1] == run.id] == [(workflow.id, run.id, 0)], (
        "against the job, under this run -- the rest of the register is what earned it"
    )
    verified_by, at = _effects(uow)[(workflow.id, run.id, 0)]
    assert verified_by == "status", "and by the belt that saw the state, not by a picture"
    assert at.endswith("+00:00"), "in UTC"
    assert at > run.started_at, "stamped when the write held, not when the run began"


async def test_the_effect_is_filed_against_the_step_that_wrote_it() -> None:
    """New. `RunProof` counts one row per write and keys it by the step's own
    order, so an effect filed against the wrong step mis-counts what a job has
    earned -- silently, since nothing downstream can tell the orders apart.

    Every other test in this section writes on step zero, where the step in
    hand and `run.steps[0]` are the same object and a caller reaching for
    either passes. Here the read is step zero and the write is step one.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    await _claimed(uow, live=True, started_by="offer", values={"clientCode": "THIRD"})
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed()],
            "http.send": [
                # The precondition read: is the write's effect already true?
                # The record does not exist yet, so the page's own read of it
                # 404s and the write goes ahead.
                Reply(ok=True, result={"status": 404, "body": "{}", "headers": {}}),
                Reply(ok=True, result={"status": 200, "body": "{}", "headers": {}}),
            ],
        }
    )
    # A plan per step: the read is typed, and the write is the recorded call
    # replayed. `_PerSchemaAsker` answers every planning question the same way
    # and cannot tell the two steps apart.
    asker = _ByRungAsker(
        plans=[_plan("type", "THIRD"), _replay()],
        sights=[],
        verdict=Answer(data={"held": True, "why": "ok"}),
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        run_id="run_claimed",
        earned=True,
    )

    assert [s.verdict for s in run.steps] == ["held", "held"]
    assert run.steps[1].result is not None and run.steps[1].result.get("wrote") is True
    assert [key for key in _effects(uow) if key[1] == run.id] == [(workflow.id, run.id, 1)], (
        "the step that wrote, not whichever step the run happens to have first"
    )


async def test_a_failed_write_forgets_the_effects_the_workflow_had_earned() -> None:
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1])
    await uow.workflows.record_effect(
        workflow.id, run_id="run_old", ord_=0, verified_by="status", at=STARTED
    )
    channel = FakeChannel(
        {
            # Two rungs: a write the server itself refused is the one write
            # that is safe to plan again, so the rescue goes out and fails too.
            **_looks(8),
            # Doubled again for the precondition read each write now makes:
            # a 500 answers nothing about the state, so the write goes ahead
            # and fails the way this test is about.
            "http.send": [Reply(ok=True, result={"status": 500, "body": "", "headers": {}})] * 4,
        }
    )
    asker = _PerSchemaAsker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        started_by="offer",
        earned=True,
    )

    assert run.steps[0].verdict == "failed" and run.steps[0].verdict_by == "status"
    assert _effects(uow) == {}, "the whole workflow's register, not this run's rows"


async def test_a_browser_that_goes_away_after_the_write_forgets_the_effects() -> None:
    """The step body never runs again after the browser goes: the write went
    out, nobody could show it held, and the job kept its autonomy.

    This is the one case that tells the `finally` apart from an ordinary
    refused write -- task 4 could not tell them apart at its own layer, and
    this is where they part.
    """
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1])
    await uow.workflows.record_effect(
        workflow.id, run_id="run_old", ord_=0, verified_by="status", at=STARTED
    )
    channel = _GoesAwayAfterTheWrite(
        {**_looks(2), "http.send": [Reply(ok=True, result={"status": 200, "body": "{}"})]}
    )
    asker = _PerSchemaAsker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={}, started_by="offer", earned=True
    )

    assert run.outcome == "failed" and run.steps[0].result is not None
    assert run.steps[0].result.get("wrote") is True, "the write went out"
    assert run.steps[0].verdict == "failed", "and nothing ever saw whether it held"
    assert _effects(uow) == {}


async def test_a_write_that_ends_unclear_forgets_the_effects() -> None:
    """No status the evidence knows, no read to make, no screen to look at:
    the write went out and nothing can say whether it held."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1])
    await uow.workflows.record_effect(
        workflow.id, run_id="run_old", ord_=0, verified_by="status", at=STARTED
    )
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 2,
            "screenshot": [Reply(ok=False, error_kind="focus_not_permitted")] * 2,
            # 300: not a refusal, and not a status the capture's POST returned.
            "http.send": [Reply(ok=True, result={"status": 300, "body": "{}"})],
        }
    )
    asker = _PerSchemaAsker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    # No values, so there is no proposition a confirming read could check.
    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={}, started_by="offer", earned=True
    )

    assert [s.verdict for s in run.steps] == ["unclear"]
    assert _effects(uow) == {}


async def test_a_step_that_ended_unclear_stops_the_run_where_it_stands() -> None:
    """New, and the other half of the gate above.

    "Nothing runs unattended past one" is the rule the loop states, and only
    `held` and `withheld` are steps somebody watched. `unclear` is precisely a
    live write that went out and which nothing could show held -- the worst of
    the three to walk past, because the next step is about to act on a state
    nobody knows.

    The test above produces an `unclear` on a ONE-step job, so it never reaches
    the gate and never asserts the outcome: adding `"unclear"` to the tuple the
    gate reads passed every unit test in the suite. This job has a second step,
    and that step must never be sent.
    """
    uow = await _fixture()
    saver = _ids(uow)[-1]
    workflow = Workflow(
        id="wfl_twice",
        tenant=ELSEWHERE,
        title="save, then save again",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(order=0, says="save", system=None, cites=[saver]),
            Step(order=1, says="save the next one", system=None, cites=[saver]),
        ],
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 4,
            "screenshot": [Reply(ok=False, error_kind="focus_not_permitted")] * 4,
            # One reply only, and 300: not a refusal, not a status the
            # capture's POST returned, and nothing behind it for a second step
            # to consume.
            "http.send": [Reply(ok=True, result={"status": 300, "body": "{}"})],
        }
    )
    asker = _PerSchemaAsker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    # No values, so there is no proposition a confirming read could check, and
    # earned so a live write does not park waiting for a person instead.
    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={}, started_by="offer", earned=True
    )

    assert [s.verdict for s in run.steps] == ["unclear"], "step one was never begun"
    assert run.outcome == "stopped"
    assert [s["kind"] for s in channel.sent].count("http.send") == 1, (
        "and its command never went out"
    )


async def test_a_step_that_only_read_neither_earns_nor_un_earns() -> None:
    """New. `wrote` is the marker the register counts on, and a step whose
    evidence records no mutation never gets one -- so a read that failed leaves
    a job's earned autonomy exactly where it found it."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    await uow.workflows.record_effect(
        workflow.id, run_id="run_old", ord_=0, verified_by="status", at=STARTED
    )
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": False}))

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.steps[0].verdict == "failed" and "wrote" not in (run.steps[0].result or {})
    assert set(_effects(uow)) == {(workflow.id, "run_old", 0)}, "the register is untouched"


# --------------------------------------------------------------------------
# The sweep the process runs at startup
# --------------------------------------------------------------------------


async def test_a_run_still_running_when_the_process_starts_is_marked_failed() -> None:
    uow = await _fixture()
    await _claimed(uow)
    await _claimed(uow, id="run_other", tenant="someone-else")
    before = uow.commits

    assert await fail_orphans(uow, "the worker restarted") == 2
    assert uow.commits == before + 1, "swept and committed, or the sweep did nothing"

    swept = await uow.workflow_runs.get(TENANT, "run_claimed")
    assert swept is not None and swept.outcome == "failed"
    assert swept.steps[-1].reason == "the worker restarted"


async def test_a_startup_with_nothing_to_sweep_writes_nothing() -> None:
    uow = await _fixture()
    await _claimed(uow, outcome="held", finished_at=STARTED)
    before = uow.commits

    assert await fail_orphans(uow, "the worker restarted") == 0
    assert uow.commits == before, "an empty sweep is not a transaction"


# --------------------------------------------------------------------------
# What reaches the planner, the verifier and the browser
#
# Every test below is new, and every one came from mutating an argument at the
# call site rather than the rule it feeds. The rig's own suite is green under
# all of them: a loop that plans from an empty screen, verifies with the two
# pages the wrong way round, asks a model nobody chose, drops the origin off
# the look, or sends every command on a tenant of its own passes 51 ported
# tests without one of them noticing.
# --------------------------------------------------------------------------


def _seen(asker: FakeAsker, which: int) -> dict[str, object]:
    return asker.asked[which]


def _prompt(asker: FakeAsker, which: int) -> dict[str, object]:
    evidence = _seen(asker, which)["evidence"]
    assert isinstance(evidence, str)
    parsed = json.loads(evidence)
    assert isinstance(parsed, dict)
    return parsed


def _two_screens() -> dict[str, list[Reply]]:
    """A browser that is somewhere different, and shows something different,
    after the command than before it."""
    return {
        "ui.url": [
            Reply(ok=True, result={"url": "http://127.0.0.1:63319/before"}),
            Reply(ok=True, result={"url": "http://127.0.0.1:63319/after"}),
        ],
        "screenshot": [
            Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "BEFORE-SCREEN"}),
            Reply(ok=True, result={"image_base64": "cGljMg==", "text_digest": "AFTER-SCREEN"}),
        ],
    }


async def test_a_step_is_planned_from_the_page_the_browser_is_on_and_verified_against_two() -> None:
    """The look before the command is what the planner is shown; the look after
    is what the verifier compares it with, and which is which is the whole
    question a screen belt answers. Both readings are asked of the model the
    caller named."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    channel = FakeChannel({**_two_screens(), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True, "why": ""}))

    run = await _ran(uow, workflow, channel=channel, asker=asker, plan_model="pro")

    planned, judged = _prompt(asker, 0), _prompt(asker, 1)
    assert planned["browser"] == {
        "url": "http://127.0.0.1:63319/before",
        "screen_text": "BEFORE-SCREEN",
    }, "the planner is shown where the browser is now"
    assert _seen(asker, 0)["image"] == base64.b64decode("aVBORw0="), (
        "and the picture that came with it"
    )
    assert (judged["screen_before"], judged["screen_after"]) == ("BEFORE-SCREEN", "AFTER-SCREEN")
    assert [a["model"] for a in asker.asked] == ["pro", "pro"], "the model the caller named"
    assert (run.steps[0].before_url, run.steps[0].after_url) == (
        "http://127.0.0.1:63319/before",
        "http://127.0.0.1:63319/after",
    ), "and the record says both"


async def test_the_planned_command_carries_the_origin_and_the_page_the_run_starts_on() -> None:
    """The origin is this step's own, off its own evidence -- a job spanning two
    systems types into the window it was demonstrated in and not the one that
    happens to be focused. `starts_on` is where the extension opens a tab when
    the operator's own is elsewhere."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    await _ran(uow, workflow, channel=channel, asker=asker)

    performed = _payload(next(s for s in channel.sent if s["kind"] == "ui.perform"))
    assert performed["origin"] == "http://127.0.0.1:63319"
    assert performed["starts_on"] == "http://127.0.0.1:63319/"


K_OTHER_SYSTEM = "http://127.0.0.1:63320"
"""A second warehouse system, for the job above's own claim -- "a job spanning
two systems types into the window it was demonstrated in". Every gesture in the
measured batch was recorded on one host, so until a step's evidence is moved to
another one, which step the origin came off cannot be told apart."""


async def test_each_steps_command_carries_the_origin_of_that_step_and_not_the_firsts() -> None:
    """New, and the sibling of the silent-click gate's own step test.

    `primary_gesture` supplies the origin, which becomes the command's `origin`
    payload, the origin every look is taken on, and the value checked against
    the evidence's allowlist -- and whether the step gets a model call at all.
    The test above makes the claim on a one-step job, where `ordered[0]` and
    the step in hand are the same step, so a loop asking about the wrong one
    passed it. Here the two steps were demonstrated on different systems: step
    one aimed at step zero's window would drive the wrong warehouse.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    assert isinstance(uow.gestures, FakeGestureRepository)
    saver = workflow.steps[1].cites[0]
    uow.gestures.rows[saver] = replace(
        uow.gestures.rows[saver],
        url=f"{K_OTHER_SYSTEM}/client/new",
        system=K_OTHER_SYSTEM,
        page_url=f"{K_OTHER_SYSTEM}/client/new",
    )
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    # No values, so every verdict comes off the screen and no confirming read
    # goes out: what is measured here is which step the origin came off.
    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={}, started_by="offer", earned=True
    )

    assert [s.verdict for s in run.steps] == ["held", "held"], "both steps ran"
    performed = [_payload(s) for s in channel.sent if s["kind"] == "ui.perform"]
    assert [p["origin"] for p in performed] == ["http://127.0.0.1:63319", K_OTHER_SYSTEM]
    # Four sends per step: a url and a picture before the command, and both
    # again after it.
    looked = [_payload(s) for s in channel.sent if s["kind"] in ("ui.url", "screenshot")]
    assert [p.get("origin") for p in looked[:4]] == ["http://127.0.0.1:63319"] * 4
    assert [p.get("origin") for p in looked[4:]] == [K_OTHER_SYSTEM] * 4, (
        "and the looks the second step took were taken on the second step's system"
    )


async def test_the_look_is_taken_on_the_system_the_step_was_demonstrated_on() -> None:
    """Both halves of the look carry the step's origin: the extension picks the
    tab from it, and a look with no origin is a look at whichever window the
    operator happens to have in front of them."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    await _ran(uow, workflow, channel=channel, asker=asker)

    looked = [s for s in channel.sent if s["kind"] in ("ui.url", "screenshot")]
    assert [s["kind"] for s in looked] == ["ui.url", "screenshot", "ui.url", "screenshot"], (
        "one look before the command and one after it"
    )
    assert {_payload(s).get("origin") for s in looked} == {"http://127.0.0.1:63319"}


async def test_the_confirming_read_goes_out_to_the_callers_own_browser_under_this_run() -> None:
    """The second belt sends a read of its own, and it goes out the same way
    every other command does: this tenant, this browser, this run. It is only
    sent at all because the step cites evidence that performs one and the run
    supplied a value it could look for."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel(
        {
            **_looks(2),
            "ui.perform": [_performed()],
            "http.send": [
                Reply(ok=True, result={"status": 200, "body": '{"clientCode": "ACME-4471"}'})
            ],
        }
    )
    asker = FakeAsker(_plan("click"))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "ACME-4471"},
        earned=True,
    )

    assert (run.steps[0].verdict, run.steps[0].verdict_by) == ("held", "read")
    probe = next(s for s in channel.sent if s["kind"] == "http.send")
    assert (probe["tenant_id"], probe["device_id"], probe["run_id"]) == (
        "acme",
        "dev_test",
        run.id,
    )
    assert _payload(probe)["url"] == "http://127.0.0.1:63319/api/stream", (
        "the read the cited evidence shows this page performs"
    )
    assert not asker.asked[1:], "no picture was needed: the state itself answered"


def _wrote(uow: FakeUnitOfWork, gesture_id: str, path: str, status: int) -> Gesture:
    """The Save click, given a write of its own and the read the page makes
    after it. Two of these are two steps whose evidence agrees about nothing:
    not the status the store answered with, and not the url that shows it."""
    click = next(g for g in _evidence(uow) if g.id == _ids(uow)[-1])
    return replace(
        click,
        id=gesture_id,
        requests=[
            Call(
                method="POST",
                url=f"http://127.0.0.1:63319/api/{path}",
                status=status,
                started_at=1788165604.9,
            ),
            Call(
                method="GET",
                url=f"http://127.0.0.1:63319/api/{path}/1",
                status=200,
                started_at=1788165605.0,
            ),
        ],
    )


async def test_the_verifier_is_asked_about_the_step_being_performed() -> None:
    """New, and the sibling of the silent-click gate's own step test.

    `verify` reads two things off the step it is handed: the statuses the
    demonstration showed this write coming back with, and the read the page
    performs afterwards. Asked about another step, it checks a write against
    evidence that was never about it and probes a url that proves nothing --
    and every workflow in this suite that reaches the verifier is one step, or
    N identical steps, so which step it was handed never changed the answer.

    Here the two steps disagree on both. Step one's write comes back 302: step
    ONE's evidence never showed that status, so the artifact belt does not
    answer and the run falls through to a read of step ONE's url. Step zero's
    evidence did show it -- so a verifier asked about step zero calls the same
    reply held on the spot, off a status another step demonstrated, and sends
    no read at all.
    """
    uow = await _fixture()
    await uow.gestures.add_gestures(
        (_wrote(uow, "ges_alpha", "alpha", 302), _wrote(uow, "ges_beta", "beta", 303))
    )
    workflow = Workflow(
        id="wfl_two_writes",
        tenant=ELSEWHERE,
        title="write, then write again",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(order=0, says="file the order", system=None, cites=["ges_alpha"]),
            Step(order=1, says="file the shipment", system=None, cites=["ges_beta"]),
        ],
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel(
        {
            **_looks(4),
            "http.send": [
                # Each write is now preceded by its own step's confirming read,
                # asked as a precondition: is this already true? The record
                # does not exist yet, so the page's own read of it 404s, which
                # is what a read of a record nobody has created answers.
                Reply(ok=True, result={"status": 404, "body": "{}"}),
                # Step zero's write: a status step zero's own evidence showed.
                Reply(ok=True, result={"status": 302, "body": "{}"}),
                Reply(ok=True, result={"status": 404, "body": "{}"}),
                # Step one's write: the same status, which step ONE's evidence
                # never showed. Not 2xx either, so nothing falls back to it.
                Reply(ok=True, result={"status": 302, "body": "{}"}),
                # And so a read goes out, and answers.
                Reply(ok=True, result={"status": 200, "body": '{"clientCode": "ACME-4471"}'}),
            ],
        }
    )
    asker = _PerSchemaAsker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "ACME-4471"},
        started_by="offer",
        earned=True,
    )

    assert [s.verdict for s in run.steps] == ["held", "held"] and run.outcome == "held"
    assert [s.verdict_by for s in run.steps] == ["status", "read"], (
        "step one's 302 is not a status step one demonstrated, so the artifact"
        " belt passes it on rather than reading step zero's evidence"
    )
    sent = [_payload(s) for s in channel.sent if s["kind"] == "http.send"]
    # Each write is preceded by its own step's confirming read, asked as a
    # precondition -- "is this already true" -- and then the write, and then
    # the same read again where the status did not settle it. What this test
    # is about is the LAST one: the read that confirmed step one is step one's,
    # not step zero's.
    assert [s["url"] for s in sent] == [
        "http://127.0.0.1:63319/api/alpha/1",
        "http://127.0.0.1:63319/api/alpha",
        "http://127.0.0.1:63319/api/beta/1",
        "http://127.0.0.1:63319/api/beta",
        "http://127.0.0.1:63319/api/beta/1",
    ], "and the read that confirmed step one is the one step one's page performs"
    assert sent[0]["method"] == "GET" and sent[1]["method"] == "POST", (
        "the precondition read goes out before the write it might make unnecessary"
    )


async def test_every_command_a_run_sends_names_the_caller_the_browser_and_the_run() -> None:
    """One envelope rule for the whole loop. A leaked device id must not reach a
    browser that is not the caller's, and a command with no run on it is a
    command the extension cannot show beside the tab it is driving."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel(
        {
            **_looks(2),
            "navigate": [Reply(ok=True, result={"navigated": True})],
            "ui.perform": [_performed()],
            "http.send": [Reply(ok=True, result={"status": 200, "body": "{}"})],
        }
    )
    asker = FakeAsker(_navigate(), _plan("click"))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "ACME-4471"},
        earned=True,
    )

    assert {s["kind"] for s in channel.sent} >= {"ui.url", "screenshot", "navigate", "ui.perform"}
    assert {(s["tenant_id"], s["device_id"], s["run_id"]) for s in channel.sent} == {
        ("acme", "dev_test", run.id)
    }


async def test_the_steps_are_performed_in_the_order_the_workflow_gave_them() -> None:
    """New. `order` is the job's order and the list is whatever the store handed
    back; a loop that trusted the list would type the client code into a form it
    had not opened yet."""
    uow = await _fixture()
    ids = _ids(uow)
    workflow = Workflow(
        id="wfl_backwards",
        tenant=ELSEWHERE,
        title="out of order",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(order=1, says="second", system=None, cites=[ids[-1]]),
            Step(order=0, says="first", system=None, cites=[ids[0]]),
        ],
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True}))

    run = await _ran(uow, workflow, channel=channel, asker=asker, values={}, earned=True)

    assert [(s.order, s.says) for s in run.steps] == [(0, "first"), (1, "second")]


class _StopsAfterTheFirstStep(Stops):
    """A person who presses stop while step zero is being performed."""

    def __init__(self) -> None:
        super().__init__()
        self.seen = 0

    def asked(self, run_id: str) -> bool:
        self.seen += 1
        return self.seen > 1


async def test_a_run_that_died_between_two_steps_leaves_the_finished_one_alone() -> None:
    """New. The step in flight is cleared once a step is finished, so a run that
    dies between steps writes a step of its own rather than rewriting the
    verdict of the one that already held."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = _AbortIsGone({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    stops = _StopsAfterTheFirstStep()

    run = await _ran(uow, workflow, channel=channel, asker=asker, stops=stops)

    assert run.outcome == "failed"
    assert [(s.order, s.verdict) for s in run.steps] == [(0, "held"), (1, "failed")]
    assert "stopped listening" in run.steps[1].reason
    assert stops.seen == 2, (
        "read once per step and never mid-command: step zero sent four commands"
        " between the two readings, and a gesture already sent cannot be recalled"
    )


async def test_a_stale_step_is_recorded_once_per_step_not_once_per_run() -> None:
    """A job run every morning reports its weak step once rather than every
    morning: one row per step, replaced.

    The rig asserted this against the store directly. It is asserted through
    the loop here because the loop is what does it twice -- two runs of the same
    job, the same step weak in both -- and the row a re-mine cannot race is only
    one row if the caller keys it the way the repository expects.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    # A different code each morning, which is what a job done every morning
    # looks like: the same values twice inside half an hour is a duplicate
    # write and the loop now refuses the second one.
    for code in ("MONDAY-1", "TUESDAY-1"):
        channel = FakeChannel(
            {**_looks(4), "ui.perform": [_performed("component"), _performed("css_path")]}
        )
        run = await _ran(
            uow, workflow, channel=channel, asker=asker, values={"clientCode": code}, earned=True
        )
        assert run.steps[1].stale is True

    assert list(_stale(uow)) == [("wfl_1", 1)], "one row, not one per run"
    assert await uow.workflows.stale_count("wfl_1") == 1


# --------------------------------------------------------------------------
# The rungs: the plan model, one rescue, and the rung below both that looks
#
# The ordering the rescue and the sight rung stand in is the whole of what
# this section exists to prove, and it is not observable anywhere else: task 2
# found that `plan_by_sight`'s own suite cannot see "only after both evidence
# rungs missed with control_not_found", and task 6 found that a single-rung
# loop cannot either.
# --------------------------------------------------------------------------


async def test_a_failed_step_is_retried_once_with_pro_then_the_run_stops_and_asks() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(6),
            "ui.perform": [
                Reply(ok=False, error_kind="control_not_found", error_detail="gone"),
                Reply(ok=False, error_kind="control_not_found", error_detail="still gone"),
            ],
        }
    )
    asker = FakeAsker(_plan("type", "x"), _plan("type", "x"))

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "stopped"
    assert run.steps[0].verdict == "failed" and run.steps[0].planned_by == "pro", (
        "the second attempt was Pro's"
    )
    assert [a["model"] for a in asker.asked] == ["flash", "pro"]
    assert len(run.steps) == 1, "it stopped rather than carrying on to save"


async def test_a_read_that_failed_is_still_rescued() -> None:
    """The write rule must not cost every step its rescue."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed()] * 2})
    asker = FakeAsker(
        _plan("type", "x"),
        Answer(data={"held": False, "why": "nothing typed"}),
        _plan("type", "x"),
        Answer(data={"held": True, "why": "typed"}),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "held" and run.steps[0].planned_by == "pro"
    assert [a["model"] for a in asker.asked] == ["flash", "flash", "pro", "flash"], (
        "the verifier stays on the model the caller named; only the plan escalates"
    )


async def test_the_pro_rescue_sees_the_page_the_flash_attempt_left_behind() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(6), "ui.perform": [_performed()] * 3})
    # Step 0 is a read, so a failed verdict is rescued once by Pro.
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": False, "why": "still blank"})
    )

    await _ran(uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"})

    plans = [a for a in asker.asked if a["schema"] is PLAN_SCHEMA]
    assert [p["model"] for p in plans][:2] == ["flash", "pro"]
    assert plans[0]["images"] == (), "the first attempt has no failed attempt to show"
    images = plans[1]["images"]
    assert isinstance(images, tuple) and len(images) == 1, (
        "the rescue is shown the page the first attempt left"
    )
    assert isinstance(images[0], bytes), "a real picture, not a placeholder"


async def test_a_rescue_is_told_what_the_attempt_before_it_failed_with() -> None:
    """New, and a caller seam: `failure` is what stops the rescue re-planning
    the attempt that just missed. The rig threaded it and nothing held it to
    it -- a loop that passed `failure=None` on every rung passes the four
    tests above."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed()] * 2})
    asker = FakeAsker(
        _plan("type", "x"),
        Answer(data={"held": False, "why": "the field is still blank"}),
        _plan("type", "x"),
        Answer(data={"held": True, "why": "typed"}),
    )

    await _ran(uow, workflow, channel=channel, asker=asker)

    plans = [a for a in asker.asked if a["schema"] is PLAN_SCHEMA]
    assert _prompt(asker, 0)["previous_attempt_failed"] is None
    assert plans[1] is _seen(asker, 2)
    assert _prompt(asker, 2)["previous_attempt_failed"] == "the field is still blank"


async def test_a_rung_that_reached_no_command_leaves_the_previous_rungs_plan_standing() -> None:
    """Flash failed AT a command and Pro failed BEFORE one. The record's
    verdict is Flash's, so its `planned_by` and `sent` must be too."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    channel = FakeChannel(
        {
            **_looks(6),
            "ui.perform": [Reply(ok=False, error_kind="control_not_found", error_detail="gone")],
        }
    )
    asker = FakeAsker(_plan("type", "x"), Answer(data={"kind": "nope", "why": "lost"}))

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    step = run.steps[0]
    assert step.verdict == "failed" and "control_not_found" in step.reason
    assert step.planned_by == "flash", "Pro never got as far as a command"
    assert step.sent is not None and step.sent["kind"] == "ui.perform"
    assert step.result == {
        "ok": False,
        "status": None,
        "matched_by": None,
        "error_kind": "control_not_found",
    }
    assert [a["model"] for a in asker.asked] == ["flash", "pro"], "Pro was still asked"


# --------------------------------------------------------------------------
# The rung below the ladder: a control found by looking
# --------------------------------------------------------------------------


def _sight(x: int = 40, y: int = 30, action: str = "type", value: str | None = "x") -> Answer:
    return Answer(
        data={"found": True, "x": x, "y": y, "action": action, "value": value, "why": "there"},
        cost_usd=0.002,
    )


def _looks_with_size(n: int) -> dict[str, list[Reply]]:
    """`_looks`, with a viewport. A picture the browser gave no numbers for is
    a picture nothing can point into, and `plan_by_sight` refuses it -- so the
    sight rung is only reachable at all through a screenshot with a size."""
    return {
        "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * n,
        "screenshot": [
            Reply(
                ok=True,
                result={
                    "image_base64": "aVBORw0=",
                    "text_digest": "Save",
                    "width": 800,
                    "height": 600,
                },
            )
        ]
        * n,
    }


class _ByRungAsker(FakeAsker):
    """Answers the evidence planner, the sight planner and the verifier each
    from their own queue, by schema, and records every call."""

    def __init__(self, plans: list[Answer], sights: list[Answer], verdict: Answer) -> None:
        super().__init__()
        self.plans, self.sights, self.verdict = list(plans), list(sights), verdict

    async def ask(self, **asked: object) -> Answer:
        await super().ask(**asked)
        schema = asked["schema"]
        assert isinstance(schema, dict)
        properties = schema["properties"]
        assert isinstance(properties, dict)
        if "held" in properties:
            return self.verdict
        if "found" in properties:
            return self.sights.pop(0)
        return self.plans.pop(0)


def _by_sight(asker: FakeAsker) -> list[dict[str, object]]:
    """Every question put to the rung that looks, told apart by its schema."""
    seen = []
    for asked in asker.asked:
        schema = asked["schema"]
        assert isinstance(schema, dict)
        properties = schema["properties"]
        assert isinstance(properties, dict)
        if "found" in properties:
            seen.append(asked)
    return seen


async def _run_by_sight(
    *,
    sights: list[Answer],
    perform_at: list[Reply],
    performs: list[Reply] | None = None,
    live: bool = True,
    looks: dict[str, list[Reply]] | None = None,
    earned: bool = True,
) -> tuple[WorkflowRun, FakeChannel, _ByRungAsker]:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **(looks or _looks_with_size(12)),
            # Two misses on the first step; the save then matches by evidence.
            "ui.perform": performs
            or [
                Reply(ok=False, error_kind="control_not_found", error_detail="gone"),
                Reply(ok=False, error_kind="control_not_found", error_detail="gone"),
                _performed("role_and_name"),
            ],
            "ui.perform_at": perform_at,
        }
    )
    asker = _ByRungAsker(
        [_plan("type", "x")] * 4, sights, Answer(data={"held": True, "why": "typed"})
    )
    run = await _ran(uow, workflow, channel=channel, asker=asker, live=live, earned=earned)
    return run, channel, asker


async def test_a_control_neither_rung_could_find_is_found_by_sight_and_the_job_marked_stale() -> (
    None
):
    run, channel, asker = await _run_by_sight(
        sights=[_sight()], perform_at=[Reply(ok=True, result={"performed": True})]
    )

    first = run.steps[0]
    assert first.verdict == "held", first.reason
    assert first.matched_by == "sight" and first.stale is True
    assert first.result == {"ok": True, "status": None, "matched_by": "sight"}
    assert [a["model"] for a in _by_sight(asker)] == ["pro"]
    [sent] = [s for s in channel.sent if s["kind"] == "ui.perform_at"]
    assert _payload(sent) == {
        "origin": "http://127.0.0.1:63319",
        "x": 40,
        "y": 30,
        "action": "type",
        "value": "x",
    }
    assert first.planned_by == "pro"
    assert run.outcome == "held", "the run carried on to the save and held"


async def test_the_sight_rung_is_for_a_control_that_was_not_found_and_nothing_else() -> None:
    """A plan the browser refused for another reason -- the page did not
    answer, the tab is gone -- is not a page that moved, and a picture answers
    nothing about it."""
    run, channel, asker = await _run_by_sight(
        sights=[_sight()],
        perform_at=[Reply(ok=True, result={"performed": True})],
        performs=[Reply(ok=False, error_kind="not_actionable", error_detail="no answer")] * 2,
    )

    assert run.outcome == "stopped" and run.steps[0].verdict == "failed"
    assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"]
    assert not _by_sight(asker), "the rung was never asked"


async def test_the_sight_rung_comes_after_both_evidence_rungs_and_not_instead_of_one() -> None:
    """New, and the ordering nothing else in this system can see: the rung
    that looks is asked once, third, and only once the rescue has missed by
    every recorded identity too. A loop that reached for the picture as soon
    as the first attempt missed passes every other test in this section."""
    run, _, asker = await _run_by_sight(
        sights=[_sight()], perform_at=[Reply(ok=True, result={"performed": True})]
    )

    kinds = [
        "sight" if asked in _by_sight(asker) else "evidence"
        for asked in asker.asked
        if asked["schema"] is not SCREEN_SCHEMA
    ]
    assert kinds[:3] == ["evidence", "evidence", "sight"]
    assert [a["model"] for a in asker.asked if a["schema"] is PLAN_SCHEMA][:2] == ["flash", "pro"]
    assert run.steps[0].verdict == "held"


async def test_a_point_off_the_screen_or_a_control_not_seen_is_a_step_that_stops() -> None:
    for sight in (
        _sight(x=900, y=30),
        Answer(data={"found": False, "x": 0, "y": 0, "action": "click", "why": "not here"}),
    ):
        run, channel, _ = await _run_by_sight(
            sights=[sight], perform_at=[Reply(ok=True, result={"performed": True})]
        )

        assert run.outcome == "stopped" and run.steps[0].verdict == "failed", sight.data
        assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"], "nothing was sent"
        assert "then by sight: " in run.steps[0].reason
        assert "not on the screen" in run.steps[0].reason or "not here" in run.steps[0].reason
        assert run.steps[0].result == {
            "ok": False,
            "status": None,
            "matched_by": None,
            "error_kind": "control_not_found",
        }, "the record keeps the last command that went out"


async def test_without_a_picture_there_is_no_sight_rung() -> None:
    """A screenshot the browser refused -- `focus_not_permitted` -- is no
    picture, and a rung that looks has nothing to look at."""
    run, channel, asker = await _run_by_sight(
        sights=[_sight()],
        perform_at=[Reply(ok=True, result={"performed": True})],
        looks={
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 12,
            "screenshot": [Reply(ok=False, error_kind="focus_not_permitted", error_detail="no")]
            * 12,
        },
    )

    assert run.outcome == "stopped" and "no screen to look at" in run.steps[0].reason
    assert not _by_sight(asker), "the model was not asked to look at nothing"
    assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"]


async def test_an_action_a_point_cannot_take_is_a_step_that_stops() -> None:
    run, channel, _ = await _run_by_sight(
        sights=[Answer(data={"found": True, "x": 1, "y": 1, "action": "select", "why": "w"})],
        perform_at=[Reply(ok=True, result={"performed": True})],
    )

    assert run.outcome == "stopped" and "'select' is not an action" in run.steps[0].reason
    assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"]


async def test_an_evidence_rung_with_no_plan_is_not_blamed_on_sight() -> None:
    """The reason append is the sight rung's alone: an evidence rung whose
    planner had no answer keeps its own reason, unadorned."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(_looks(6))
    asker = FakeAsker(Answer(error="503 UNAVAILABLE"), Answer(error="503 UNAVAILABLE"))

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.steps[0].verdict == "failed" and run.steps[0].reason == "503 UNAVAILABLE"
    assert "by sight" not in run.steps[0].reason


# --------------------------------------------------------------------------
# What a step may have changed, and what follows from it
# --------------------------------------------------------------------------


def _saw_traffic(uow: FakeUnitOfWork) -> Gesture:
    """The silent click, given one completed read of its own -- a menu or a
    tab, which changed nothing and is safe to try again."""
    click = next(g for g in _evidence(uow) if g.id == _silent_click(uow))
    heard = Call(
        method="GET",
        url="http://127.0.0.1:63319/api/clients",
        status=200,
        started_at=1788165604.9,
    )
    return replace(click, id="ges_read_click", requests=[heard])


def test_a_step_whose_evidence_shows_no_completed_traffic_saw_nothing() -> None:
    by_id = {gesture.id: gesture for gesture in _gestures()}
    saver = next(g for g in by_id.values() if g.requests)
    typed = next(g for g in by_id.values() if not g.requests)

    assert not _saw_nothing(Step(order=0, says="s", system=None, cites=[saver.id]), by_id)
    assert _saw_nothing(Step(order=0, says="s", system=None, cites=[typed.id]), by_id)
    assert not _saw_nothing(
        Step(order=0, says="s", system=None, cites=["ges_gone", saver.id]), by_id
    ), "a cited gesture the repository lost does not hide the evidence behind it"

    dead = replace(
        saver,
        requests=[
            replace(call, status=502, failure_reason="Failed to fetch") for call in saver.requests
        ],
    )
    assert _saw_nothing(Step(order=0, says="s", system=None, cites=[dead.id]), {dead.id: dead}), (
        "a call that never landed is not traffic the recorder saw"
    )


async def test_a_write_that_went_out_is_not_performed_a_second_time() -> None:
    """The rescue exists for a step that did not happen. A write the browser
    sent and the server accepted, which then could not be shown to have held,
    is not that: retrying it creates the order twice."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()]})
    asker = FakeAsker(_plan("click"), Answer(data={"held": False, "why": "no confirmation"}))

    run = await _ran(uow, workflow, channel=channel, asker=asker, earned=True)

    assert run.outcome == "stopped"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 1, "sent once"
    assert [a["model"] for a in asker.asked] == ["flash", "flash"], "Pro was never asked"
    assert run.steps[0].reason.startswith("state unknown after a write; not retried: ")


async def test_a_click_the_capture_heard_nothing_from_is_not_clicked_twice() -> None:
    """`writes()` is False for a Save whose call the recorder never saw, and a
    rescue of that click submits the order a second time."""
    uow = await _fixture()
    workflow = await _one_step(uow, _silent_click(uow), says="press Save", parameters=[])
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()]})
    asker = FakeAsker(_plan("click"), Answer(data={"held": False, "why": "no confirmation"}))

    run = await _ran(uow, workflow, channel=channel, asker=asker, earned=True)

    assert run.outcome == "stopped"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 1, "clicked once"
    assert [a["model"] for a in asker.asked] == ["flash", "flash"], "Pro was never asked"
    assert "state unknown" in run.steps[0].reason
    assert (run.steps[0].result or {})["wrote"] is True, "and it counts as a write"


async def test_a_click_that_fired_a_read_still_gets_its_rescue() -> None:
    """A menu or a tab click that the recorder DID see traffic from changed
    nothing, and the write rule must not cost it its second attempt."""
    uow = await _fixture()
    await uow.gestures.add_gestures((_saw_traffic(uow),))
    workflow = await _one_step(uow, "ges_read_click", says="open the tab", parameters=[])
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed()] * 2})
    asker = FakeAsker(
        _plan("click"),
        Answer(data={"held": False, "why": "the panel did not open"}),
        _plan("click"),
        Answer(data={"held": True, "why": "the panel is open"}),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "held" and run.steps[0].planned_by == "pro"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 2
    assert "wrote" not in (run.steps[0].result or {}), "a completed read is not a write"


async def test_a_step_the_evidence_calls_a_read_but_the_model_typed_into_is_no_write() -> None:
    """New, and the seam the predicate is asked at: `may_write` widens
    `writes()` only for a click or a press. A type on evidence the recorder
    heard nothing from is not a possible write, and a loop that widened on
    every action would refuse every rescue this suite has."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[0], says="type the code")
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed()] * 2})
    asker = FakeAsker(
        _plan("type", "x"),
        Answer(data={"held": False, "why": "still blank"}),
        _plan("type", "x"),
        Answer(data={"held": True, "why": "typed"}),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker)

    assert run.outcome == "held" and run.steps[0].planned_by == "pro", "it was rescued"
    assert "wrote" not in (run.steps[0].result or {})


# --------------------------------------------------------------------------
# The write a dry run does not send
# --------------------------------------------------------------------------


async def test_a_dry_run_sends_the_reads_and_withholds_the_write_in_full() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()]})
    asker = FakeAsker(
        _plan("type", "THIRD"), Answer(data={"held": True, "why": "typed"}), _plan("click")
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"}, live=False
    )

    assert run.outcome == "held"
    assert [s.verdict for s in run.steps] == ["held", "withheld"]
    performed = [s for s in channel.sent if s["kind"] == "ui.perform"]
    assert len(performed) == 1 and _payload(performed[0])["value"] == "THIRD", "the typing went out"
    assert run.withheld and run.withheld[0]["method"] == "POST", "the write is shown, in full"
    assert await uow.workflow_runs.get(TENANT, run.id) == run, "saved"


def test_what_a_dry_run_withholds_is_the_write_in_full() -> None:
    """What a person reads before pressing through to live: the command the
    planner chose, and the call the operator's own demonstration made."""
    by_id = {gesture.id: gesture for gesture in _gestures()}
    saver = next(g for g in by_id.values() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")
    step = Step(order=1, says="save", system=None, cites=[saver.id])
    planned = Planned("ui.perform", {"action": "click"}, "w", Answer())

    assert _withheld(step, planned, by_id) == {
        "step": 1,
        "planned": {"kind": "ui.perform", "payload": {"action": "click"}},
        "method": "POST",
        "url": post.url,
        "body": post.request_body.text if post.request_body else None,
    }

    typed = next(g for g in by_id.values() if not g.requests)
    quiet = _withheld(Step(order=0, says="type", system=None, cites=[typed.id]), planned, by_id)
    assert quiet == {"step": 0, "planned": {"kind": "ui.perform", "payload": {"action": "click"}}}


def test_a_withheld_replay_shows_the_body_this_run_would_send() -> None:
    """The card is read to decide whether to press through, so it has to name
    what would go out. A replay's body is re-aimed at this run's values, so
    showing the demonstration's bytes would show the code the operator typed
    on the day and send a different one the moment the person said yes."""
    by_id = {gesture.id: gesture for gesture in _gestures()}
    saver = next(g for g in by_id.values() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")
    step = Step(order=1, says="save", system=None, cites=[saver.id])
    planned = Planned(
        "http.send",
        {"method": "POST", "url": post.url, "headers": {}, "body": '{"clientCode": "THIRD"}'},
        "w",
        Answer(),
        rewrote=True,
    )

    shown = _withheld(step, planned, by_id)

    assert shown["body"] == '{"clientCode": "THIRD"}'
    assert shown["body"] != (post.request_body.text if post.request_body else None)
    assert (shown["method"], shown["url"]) == ("POST", post.url)


async def test_a_dry_run_records_no_effect_even_for_a_click_it_does_send() -> None:
    """`writes()` is False for a Save whose call the recorder never saw, so a
    dry run performs it -- and a dry run's evidence earns nothing."""
    uow = await _fixture()
    workflow = await _one_step(uow, _silent_click(uow), says="press Save", parameters=[])
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"}, live=False
    )

    assert run.outcome == "held", "the click was sent, not withheld"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 1
    assert _effects(uow) == {}


async def test_a_dry_run_reads_by_sight_too_and_its_writes_never_reach_the_rung() -> None:
    """A dry run performs reads, so a read neither evidence rung could find is
    found by sight the same way. Its writes are withheld before any rung could
    miss them: the save below is withheld by evidence, and the sight rung is
    never asked about it."""
    run, channel, asker = await _run_by_sight(
        sights=[_sight()],
        perform_at=[Reply(ok=True, result={"performed": True})],
        live=False,
    )

    assert [s.verdict for s in run.steps] == ["held", "withheld"], [s.reason for s in run.steps]
    assert run.steps[0].matched_by == "sight" and run.steps[0].stale is True
    assert len([s for s in channel.sent if s["kind"] == "ui.perform_at"]) == 1
    assert len(_by_sight(asker)) == 1
    shown = run.withheld[0]["planned"]
    assert isinstance(shown, dict) and shown["kind"] == "ui.perform", (
        "withheld by evidence, unasked"
    )


# --------------------------------------------------------------------------
# The write that stops and asks a person
# --------------------------------------------------------------------------


async def _parked(approvals: Approvals) -> str:
    """The run that has stopped in front of a person, once it has.

    A deadline rather than a bare loop: a wait for something that never
    happens is a test that hangs, and the rig's own version of this polled
    two hundred times and then raised by hand.
    """
    async with asyncio.timeout(5):
        # Polled rather than awaited: the event this register holds belongs to
        # the run waiting on it and is popped on the way out, so there is
        # nothing here for a watcher to await. ASYNC110's advice needs an event
        # that does not exist.
        while not approvals.waiting():  # noqa: ASYNC110
            await asyncio.sleep(0.01)
    # One, and named, rather than whichever the frozenset yields first: a run
    # that parked a second key under some other id is a bug, and reading it
    # through `next(iter(...))` would report it as a different failure on every
    # `PYTHONHASHSEED`.
    (parked,) = approvals.waiting()
    return parked


async def test_a_live_write_waits_for_approval_and_goes_out_when_it_comes() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    approvals = Approvals()

    task = asyncio.create_task(
        _ran(
            uow,
            workflow,
            channel=channel,
            asker=asker,
            values={"clientCode": "THIRD"},
            started_by="offer",
            approvals=approvals,
        )
    )
    run_id = await _parked(approvals)

    saved = await uow.workflow_runs.get(TENANT, run_id)
    assert saved is not None and saved.steps[-1].verdict == "awaiting"
    assert saved.steps[-1].sent is not None, "the panel shows what would go out"
    assert saved.steps[-1].verdict_by == "none" and "approve" in saved.steps[-1].reason
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1, (
        "the read step went; the write waits"
    )

    assert approvals.approve(run_id) is True
    run = await task
    assert run.outcome == "held"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 2


class _RecordsTheWait(Approvals):
    """A register nobody ever taps, that remembers how long it was asked to
    hold the write for."""

    def __init__(self) -> None:
        super().__init__()
        self.waited: list[float] = []

    async def wait_for(
        self,
        run_id: str,
        # The signature it is standing in for, whose own `noqa` says why the
        # rule does not apply: the wait IS the timeout here.
        timeout: float = K_APPROVAL_WAIT_S,  # noqa: ASYNC109
    ) -> bool:
        self.waited.append(timeout)
        return False


async def test_the_person_the_write_waits_on_is_given_five_minutes() -> None:
    """New. Every other test of this branch patches `K_APPROVAL_WAIT_S` down to
    milliseconds so the suite does not sit for five minutes, which left the
    number itself held by nothing here: it could have been thirty seconds and
    the whole file would still pass.

    Both halves are read off it -- the deadline the loop hands the register,
    and the minutes it tells the person afterwards -- and the number is a
    measurement of somebody reading a panel, not a round one that was liked.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    approvals = _RecordsTheWait()

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        started_by="offer",
        approvals=approvals,
    )

    assert approvals.waited == [300.0], "the loop's own deadline, not the register's default"
    assert "within 5 minutes" in run.steps[-1].reason


async def test_a_step_the_job_would_skip_is_not_a_write_to_ask_about(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Measured on the deployment, 2026-09-17: three approval windows spent on
    "Click the Add button", which opens a form.

    `may_write` is deliberately wide -- a click whose demonstration showed no
    traffic might be a write, so it asks. But a step in the reserve is one an
    unwatched run of this very job does not perform at all: it is scaffolding
    for a write that is in the ledger, and that write is the Save at the end of
    it. Asking somebody to approve doing what the same job would otherwise skip
    is incoherent, and it stopped every watched run three steps early.

    The write still asks. `scaffolding_for` returns what comes BEFORE the write
    step, so the step carrying the call is never in the reserve.
    """
    # The write at the end still parks, and this test is not about that wait.
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    uow = await _fixture()
    workflow = await _workflow(uow)
    for step in workflow.steps:
        step.order += 1
    workflow.steps.insert(
        0,
        Step(order=0, says="click Add", system=None, cites=[_silent_click(uow)], parameters=[]),
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed()] * 4})
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        started_by="offer",
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
        watched=True,
    )

    assert run.steps[0].verdict != "awaiting", run.steps[0].reason
    assert "approve" not in (run.steps[0].reason or ""), run.steps[0].reason


async def test_a_write_nobody_approves_stops_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        started_by="offer",
    )

    assert run.outcome == "stopped"
    assert "nobody approved" in run.steps[-1].reason
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1
    # The step is done, not merely un-sent: a rung that carried on would climb
    # to the rescue, look again, spend a Pro plan on the write the person
    # declined and park a second time -- ten more minutes and a bigger bill for
    # an answer that has already been given. One plan means one rung and one
    # wait.
    assert [a["model"] for a in asker.asked if a["schema"] is PLAN_SCHEMA] == ["flash", "flash"], (
        "one plan for the read and one for the write: Pro was never asked"
    )


async def test_a_stop_pressed_during_the_wait_aborts_the_run() -> None:
    """A released wait is not a yes. The stop button releases it as well as
    setting the flag, and the loop asks which of the two it was before it lets
    the write out."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    approvals, stops = Approvals(), Stops()

    task = asyncio.create_task(
        _ran(
            uow,
            workflow,
            channel=channel,
            asker=asker,
            values={"clientCode": "THIRD"},
            started_by="offer",
            approvals=approvals,
            stops=stops,
        )
    )
    run_id = await _parked(approvals)

    stops.ask(run_id)
    approvals.approve(run_id)
    run = await task

    assert run.outcome == "aborted"
    assert run.steps[-1].verdict == "failed" and "stopped while waiting" in run.steps[-1].reason
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1, "the write never went out"
    # The browser is told, on this path as well as between steps. Until it
    # hears the abort its band goes on claiming the run for up to
    # `RUN_QUIET_MS`, and this is the path where somebody is watching: they
    # pressed Stop on a panel showing a write and their own screen would go on
    # saying the run was theirs.
    assert [s["kind"] for s in channel.sent][-1] == "abort"
    assert _payload(channel.sent[-1]) == {"run_id": run_id}


async def test_a_stop_during_the_wait_still_aborts_when_the_browser_has_gone() -> None:
    """The send is best effort and the abort is not. A browser that has already
    gone is the commonest reason to press Stop, and a raise here would reach
    `_fell_over` -- which rewrites the outcome to `failed` and the reason to the
    socket error, reporting "the browser went away" for a run a person
    deliberately stopped.

    Deliberately unlike the between-steps send at the top of the loop, which is
    bare: there a send that raises IS a run that died, and
    `test_a_run_that_died_between_two_steps_leaves_the_finished_one_alone` pins
    it. Here the intention is already recorded before anything is sent.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = _AbortIsGone(
        {**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]}
    )
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    approvals, stops = Approvals(), Stops()

    task = asyncio.create_task(
        _ran(
            uow,
            workflow,
            channel=channel,
            asker=asker,
            values={"clientCode": "THIRD"},
            started_by="offer",
            approvals=approvals,
            stops=stops,
        )
    )
    run_id = await _parked(approvals)

    stops.ask(run_id)
    approvals.approve(run_id)
    run = await task

    assert run.outcome == "aborted", "a browser that went away did not turn a stop into a failure"
    assert "stopped while waiting" in run.steps[-1].reason
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1, "the write never went out"


async def test_a_dry_run_never_pauses() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    approvals = Approvals()

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        live=False,
        approvals=approvals,
    )

    assert [s.verdict for s in run.steps] == ["held", "withheld"]
    assert not approvals.waiting(), "a dry run withholds; it never waits"


async def test_an_earned_workflow_writes_without_asking() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    approvals = Approvals()

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        started_by="offer",
        approvals=approvals,
        earned=True,
    )

    assert run.outcome == "held" and not approvals.waiting()
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 2


async def test_a_job_one_verified_run_short_of_earning_still_asks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """New, and the seam `earned` is asked at: the rule is `K_EARNED_RUNS`
    proofs, and a loop that asked the register a question it does not answer
    -- "has this job ever written", say -- would let the third run of a job
    write unasked."""
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    uow = await _fixture()
    workflow = await _workflow(uow)
    await _earn(uow, workflow)
    assert isinstance(uow.workflow_runs, FakeWorkflowRunRepository)
    del uow.workflow_runs.rows[f"run_earned_{K_EARNED_RUNS - 1}"]
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"})

    assert run.outcome == "stopped" and "nobody approved" in run.steps[-1].reason


async def test_a_click_the_capture_heard_nothing_from_also_waits() -> None:
    """`writes()` is False for a Save whose call the recorder never saw, and
    the rescue gate already refuses to retry it. A step nobody may retry is a
    step nobody may send unasked either, so it waits for the tap too."""
    uow = await _fixture()
    workflow = await _one_step(uow, _silent_click(uow), says="press Save", parameters=[])
    channel = FakeChannel({**_looks(2), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))
    approvals = Approvals()

    task = asyncio.create_task(
        _ran(
            uow,
            workflow,
            channel=channel,
            asker=asker,
            values={"clientCode": "THIRD"},
            started_by="offer",
            approvals=approvals,
        )
    )
    run_id = await _parked(approvals)

    saved = await uow.workflow_runs.get(TENANT, run_id)
    assert saved is not None and saved.steps[-1].verdict == "awaiting"
    assert not [s for s in channel.sent if s["kind"] == "ui.perform"], "nothing went out"

    assert approvals.approve(run_id) is True
    run = await task
    assert run.outcome == "held"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 1


async def test_the_silent_click_gate_is_asked_about_the_step_being_performed() -> None:
    """New, and the argument `_saw_nothing` is threaded with. `may_write`
    widens `writes()` for a click on evidence the recorder heard nothing from,
    and the step it asks about has to be the step in hand.

    Every other workflow in this suite is one step, or N identical steps, or
    two whose write is already a write by evidence -- so which step the
    predicate was handed never changed its answer, and a loop asking about
    `ordered[0]` or `ordered[-1]` passed all of them. Here the silent click is
    in the MIDDLE and both its neighbours are clicks the recorder did hear a
    completed read from: the middle one waits for a person, and neither
    neighbour does. A middle step asked about the wrong one is a live write
    sent unasked, and then retried.
    """
    uow = await _fixture()
    await uow.gestures.add_gestures((_saw_traffic(uow),))
    heard, silent = "ges_read_click", _silent_click(uow)
    workflow = Workflow(
        id="wfl_middle",
        tenant=ELSEWHERE,
        title="open the tab, save, look again",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(order=0, says="open the tab", system=None, cites=[heard]),
            Step(order=1, says="press Save", system=None, cites=[silent]),
            Step(order=2, says="open the tab again", system=None, cites=[heard]),
        ],
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed()] * 3})
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))
    approvals = Approvals()

    # No values, so no step has a proposition a confirming read could check and
    # every verdict comes off the screen: what is being measured here is which
    # step the write gate was asked about, not which belt answered.
    task = asyncio.create_task(
        _ran(
            uow,
            workflow,
            channel=channel,
            asker=asker,
            values={},
            started_by="offer",
            approvals=approvals,
        )
    )
    run_id = await _parked(approvals)

    parked = await uow.workflow_runs.get(TENANT, run_id)
    assert parked is not None, "the parked step is saved before the wait begins"
    assert (parked.steps[-1].order, parked.steps[-1].verdict) == (1, "awaiting")
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1, "step zero went unasked"

    assert approvals.approve(run_id) is True
    run = await task

    assert run.outcome == "held" and [s.verdict for s in run.steps] == ["held"] * 3
    assert [bool((s.result or {}).get("wrote")) for s in run.steps] == [False, True, False], (
        "the click the recorder heard nothing from, and only that one"
    )
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 3, "step two never waited"


async def test_a_click_by_sight_is_a_write_until_a_person_says_otherwise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first step's evidence is a typed field, not a silent click: by
    evidence, a click there would not be a possible write. By sight it is --
    the point is on a page that has moved, and what is there now is unknown --
    so on a job that has not earned it, the click waits for a tap. Nobody
    taps, and it never goes out."""
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)

    run, channel, _ = await _run_by_sight(
        sights=[_sight(action="click", value=None)],
        perform_at=[Reply(ok=True, result={"performed": True})],
        earned=False,
    )

    assert run.steps[0].verdict == "failed" and "nobody approved" in run.steps[0].reason
    assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"], "it waited, then stopped"
    assert run.steps[0].sent == {
        "kind": "ui.perform_at",
        "payload": {"origin": "http://127.0.0.1:63319", "x": 40, "y": 30, "action": "click"},
    }, "what would have gone out was shown"


# --------------------------------------------------------------------------
# A job the operator started themselves, and the rig asked to finish
# --------------------------------------------------------------------------


def _demonstrated_on(uow: FakeUnitOfWork, gesture_id: str, page_url: str) -> None:
    """Move one gesture to a page of its own.

    Every gesture in the measured batch was recorded on
    `http://127.0.0.1:63319/`, so until one of them is somewhere else,
    `starts_on` reads the same url whichever step it is taken from -- and
    which step it is taken from is the whole of what `starts_on` says. Task
    6's review found this seam unpinned; it is pinned here because `from_step`
    is what moves it.
    """
    assert isinstance(uow.gestures, FakeGestureRepository)
    uow.gestures.rows[gesture_id] = replace(uow.gestures.rows[gesture_id], page_url=page_url)


K_SECOND_SCREEN = "http://127.0.0.1:63319/client/new"
"""Where the save was demonstrated, once the fixture says the job spans two
screens. Not the page step zero was recorded on."""


async def test_a_run_started_mid_job_records_the_operators_steps_and_performs_the_rest() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(
        plan=_plan("click"), verdict=Answer(data={"held": True, "why": "saved"})
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        started_by="offer",
        earned=True,
        from_step=1,
    )

    assert [s.verdict for s in run.steps] == ["done_by_operator", "held"]
    assert run.steps[0].verdict_by == "none" and workflow.steps[0].cites[0] in run.steps[0].reason
    assert run.steps[0].sent is None and run.steps[0].in_tokens == 0, "nothing asked, nothing sent"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1
    assert run.outcome == "held"
    stored = await uow.workflow_runs.get(TENANT, run.id)
    assert stored is not None and stored.from_step == 1, (
        "and on the row rather than only in this frame -- it is what a re-press"
        " has to agree with, and a row saying zero would refuse the resume it"
        " was itself started for"
    )


async def test_only_the_first_step_a_run_performs_may_open_a_tab() -> None:
    """`starts_on` is where a tab is OPENED when the operator's own is
    elsewhere. It is a fact about BEGINNING the run -- and it was computed once
    and then attached to every step, which dragged a job that crosses systems
    back to the first one on every leg.

    Measured on the deployment, 2026-09-15: step 2 of `Create a Customer Type`
    went out with `origin` naming the warehouse and `starts_on` naming the
    operator's mail. The extension found their warehouse tab, threw it away
    because it was not on that page, opened the mail, and clicked a warehouse
    control there -- `not_actionable: the page did not answer`.

    After the first command a tab is pinned to the run and `commands.js` keeps
    it while it is on the step's own origin, which is all the later steps need.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    _demonstrated_on(uow, workflow.steps[1].cites[0], K_SECOND_SCREEN)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True, "why": ""}))

    await _ran(uow, workflow, channel=channel, asker=asker, earned=True)

    performed = [_payload(one) for one in channel.sent if one["kind"] == "ui.perform"]
    assert len(performed) >= 2, "this is about the steps after the first"
    assert performed[0].get("starts_on"), "the run could not open a tab to begin"
    assert all("starts_on" not in one for one in performed[1:]), (
        "a later step carried the page the run began on"
    )


async def test_a_run_started_mid_job_starts_on_the_page_of_the_step_it_starts_at() -> None:
    """`starts_on` is what the extension opens a tab at when the operator's own
    tab is elsewhere. Aimed at step 0 for a run that starts at step 1, it would
    abandon the very progress the offer was made on."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    _demonstrated_on(uow, workflow.steps[1].cites[0], K_SECOND_SCREEN)
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(
        plan=_plan("click"), verdict=Answer(data={"held": True, "why": "saved"})
    )

    await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        started_by="offer",
        earned=True,
        from_step=1,
    )

    [performed] = [s for s in channel.sent if s["kind"] == "ui.perform"]
    assert _payload(performed)["starts_on"] == K_SECOND_SCREEN


async def test_two_doings_of_a_step_name_the_screen_and_not_either_visit() -> None:
    """The screen a run opens is asked of the demonstrations, not of one of
    them.

    Found on the deployment's own row, 2026-09-15. Step 2 of `Create a Customer
    Type` is "Navigate to the Customer Types screen", and the two gestures it
    cites sit on `…inbound.receiving.optimaldoorassignment` and
    `…warehouse.warehouse` -- the screens the operator happened to be on when
    they reached for the menu, neither of them this step's. A run resuming
    there opened whichever one `primary_gesture` picked, then planned every
    step against it.

    What two doings of one step agree on is the screen; what differs is the
    visit. Here they agree on `/client` and on `siteId=SG`, and disagree on the
    fragment and on the session token -- so the fragment and the token go and
    nothing else does.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    # A step with two doings in it, which is what the fixture's one-cite steps
    # cannot be: a job demonstrated twice cites both, and every step of the
    # deployment's own `Create a Customer Type` cites two or more.
    ids = _ids(uow)
    again = next(one for one in ids if one != workflow.steps[1].cites[0])
    workflow.steps[1] = replace(workflow.steps[1], cites=[*workflow.steps[1].cites, again])
    await uow.workflows.save(workflow)
    once, twice = workflow.steps[1].cites
    _demonstrated_on(
        uow, once, "http://127.0.0.1:63319/client?libraryContext=aaaa&siteId=SG#inbound"
    )
    _demonstrated_on(
        uow, twice, "http://127.0.0.1:63319/client?libraryContext=bbbb&siteId=SG#warehouse"
    )
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(
        plan=_plan("click"), verdict=Answer(data={"held": True, "why": "saved"})
    )

    await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        started_by="offer",
        earned=True,
        from_step=1,
    )

    [performed] = [s for s in channel.sent if s["kind"] == "ui.perform"]
    assert _payload(performed)["starts_on"] == "http://127.0.0.1:63319/client?siteId=SG"


async def test_a_run_that_starts_at_the_top_starts_on_the_first_steps_page() -> None:
    """New, and the other half of the same seam: on the same two-screen
    fixture, a run that starts where the job does opens at step zero's page and
    not at the second screen's."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    _demonstrated_on(uow, workflow.steps[1].cites[0], K_SECOND_SCREEN)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True, "why": ""}))

    await _ran(uow, workflow, channel=channel, asker=asker, earned=True)

    starts = [_payload(s).get("starts_on") for s in channel.sent if s["kind"] == "ui.perform"]
    # The first one, which is the only one that carries it: `starts_on` opens a
    # tab to BEGIN the run, and sending it again on the second step aimed a
    # cross-system job back at the first system. `test_only_the_first_step_a_
    # run_performs_may_open_a_tab` holds that half; this one holds WHICH page
    # the first step is given, which is where the job starts and not the second
    # screen.
    assert starts[0] == "http://127.0.0.1:63319/"


async def test_the_steps_the_operator_did_buy_no_budget() -> None:
    """A run that starts at step k attempts fewer steps, so it gets fewer
    attempts. The slack is for the job that is left."""
    uow = await _fixture()
    workflow = await _repeated(uow, 5)
    budget = len(workflow.steps) - 1 + K_STEP_SLACK
    channel = FakeChannel(
        {
            **_looks(budget * 2),
            "navigate": [Reply(ok=True, result={"navigated": True})] * len(workflow.steps),
            "ui.perform": [_performed()] * len(workflow.steps),
        }
    )
    # Three of the four steps left take a navigate and a command each, which is
    # six of the seven; the fourth's navigate spends the last.
    asker = FakeAsker(
        *[
            answer
            for _ in range(3)
            for answer in (_navigate(), _plan("type", "x"), Answer(data={"held": True, "why": ""}))
        ],
        _navigate(),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker, started_by="offer", from_step=1)

    assert run.outcome == "refused"
    last = run.steps[-1]
    assert last.order == 4 and last.verdict == "refused"
    assert str(budget) in last.reason, "the operator's step is not slack for the rig"
    assert len([a for a in asker.asked if a["schema"] is PLAN_SCHEMA]) == budget


async def test_a_run_started_past_its_last_step_performs_nothing_and_holds() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(_looks(2))
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True, "why": ""}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "THIRD"},
        live=False,
        from_step=len(workflow.steps),
    )

    assert [s.verdict for s in run.steps] == ["done_by_operator", "done_by_operator"]
    assert run.outcome == "held" and channel.sent == [] and asker.asked == []


# --------------------------------------------------------------------------
# The seams the rungs and the gates are asked at
#
# Every test below is new, and every one came from mutating an argument at the
# call site rather than the rule it feeds. The suite above is green under all
# of them: a loop that shows the rung that looks a blank step, tells it
# nothing about what just missed, plans on the run's own values and then fills
# the control from somewhere else, or registers a wait nobody can tap, passes
# the eighty-eight tests before this comment.
# --------------------------------------------------------------------------


def _sight_prompt(asker: FakeAsker) -> dict[str, object]:
    [asked] = _by_sight(asker)
    evidence = asked["evidence"]
    assert isinstance(evidence, str)
    parsed = json.loads(evidence)
    assert isinstance(parsed, dict)
    return parsed


def _silent_press(uow: FakeUnitOfWork) -> str:
    """A press the recorder saw and heard no traffic from. Enter on a form is
    a submit, and a submit whose call went out where the recorder was not
    attached is exactly as unknown as a silent click."""
    return next(g.id for g in _evidence(uow) if g.action.kind == "press" and not g.requests)


async def test_the_rung_that_looks_is_told_the_step_the_values_and_what_missed() -> None:
    """Three arguments, none of which the rung's own answer reveals: which
    step it is planning, the values the person asked this run for, and what
    the two evidence rungs failed with. The value is the sharp one -- the
    model reads a value off the screen and the run's own value wins over it,
    so a rung planned on `{}` fills the control with what the picture said.

    Three separate seams die on this one test -- a blank step, `values={}` and
    `failure=None` each fail an assertion here and nowhere else -- so narrowing
    it later reopens three at once."""
    run, channel, asker = await _run_by_sight(
        sights=[_sight(value="WHAT-THE-SCREEN-SHOWED")],
        perform_at=[Reply(ok=True, result={"performed": True})],
    )

    shown = _sight_prompt(asker)
    assert shown["step"] == {"order": 0, "says": "type the code", "parameters": ["clientCode"]}
    assert shown["values"] == {"clientCode": "x"}, "the values this run was asked for"
    failed = shown["previous_attempt_failed"]
    assert isinstance(failed, str) and "control_not_found" in failed, (
        "and what the rungs above it missed with"
    )
    [sent] = [s for s in channel.sent if s["kind"] == "ui.perform_at"]
    assert _payload(sent)["value"] == "x", "the run's value, not the one the model read"
    assert run.steps[0].verdict == "held"


async def test_a_press_the_capture_heard_nothing_from_is_a_write_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A click is not the only way to submit a form. The press rule is the
    click rule, and dropping it from the predicate lets Enter on an order form
    go out unasked."""
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    uow = await _fixture()
    workflow = await _one_step(uow, _silent_press(uow), says="press Enter to submit")
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("press", "Enter"), verdict=Answer(data={"held": True}))

    run = await _ran(uow, workflow, channel=channel, asker=asker, started_by="offer")

    assert "nobody approved" in run.steps[0].reason
    assert not [s for s in channel.sent if s["kind"] == "ui.perform"], "it never went out"


async def test_a_tap_that_lands_before_the_wait_starts_is_not_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The save is what puts the step in front of a person, and the wait
    starts after it. A tap in that window has to find an event to set, which
    is why the register is asked before the save and not by the wait."""
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True}))
    approvals = Approvals()
    taps: list[bool] = []

    saved = uow.workflow_runs.save

    async def _tap_on_save(run: WorkflowRun) -> None:
        await saved(run)
        if run.steps and run.steps[-1].verdict == "awaiting":
            taps.append(approvals.approve(run.id))

    uow.workflow_runs.save = _tap_on_save  # type: ignore[method-assign]
    run = await _ran(
        uow, workflow, channel=channel, asker=asker, started_by="offer", approvals=approvals
    )

    assert taps == [True], "the tap found something waiting"
    assert run.outcome == "held"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 2, "and the write went out"


async def test_an_approved_step_stops_saying_it_is_waiting_before_the_write_goes_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`awaiting` is what the panel draws the Approve button from.

    Left standing through the send it is a row that lies for as long as the
    step takes -- the call, the read-back, and on the third rung a screenshot
    and a vision call. So an operator taps Approve, the tap is recorded, the
    wait really is released, and the panel redraws the same paused row with the
    same button. Reported on the live deployment 2026-09-16 as "I clicked
    approve and nothing happened", against a run whose approval had landed
    every time.
    """
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 5.0)
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True}))
    approvals = Approvals()
    saved = uow.workflow_runs.save
    seen: list[str] = []

    async def _watch(run: WorkflowRun) -> None:
        await saved(run)
        if run.steps:
            last = run.steps[-1]
            if not seen or seen[-1] != last.verdict:
                seen.append(last.verdict or "")
            if last.verdict == "awaiting":
                approvals.approve(run.id)

    uow.workflow_runs.save = _watch  # type: ignore[method-assign]

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, started_by="offer", approvals=approvals
    )

    assert run.outcome == "held"
    # The row said `awaiting`, and the very next thing saved about that step
    # said it no longer was -- before the command went out, not after it came
    # back.
    assert "awaiting" in seen, "the step parked"
    after = seen[seen.index("awaiting") + 1 :]
    assert after and after[0] == "skipped", (
        f"the row went {after[:1]} after approval, so the panel kept drawing Approve"
    )


async def test_a_run_that_dies_while_it_parks_leaves_nothing_waiting() -> None:
    """The register is what the panel's `awaiting` list reads. A run that
    registered and then died before it could wait would sit in that list
    forever, offering a person a tap on a run nobody is driving."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = _PerSchemaAsker(plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True}))
    approvals = Approvals()

    saved = uow.workflow_runs.save
    died = False

    async def _die_on_the_parking_save(run: WorkflowRun) -> None:
        nonlocal died
        if not died and run.steps and run.steps[-1].verdict == "awaiting":
            died = True
            raise RuntimeError("the session went away")
        await saved(run)

    uow.workflow_runs.save = _die_on_the_parking_save  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        await _ran(
            uow, workflow, channel=channel, asker=asker, started_by="offer", approvals=approvals
        )

    assert died, "it died where it parks and nowhere else"
    assert approvals.waiting() == frozenset(), "the wait went with the run"


async def test_the_operators_steps_are_saved_as_the_run_walks_past_them() -> None:
    """The panel polls the row, and a run finishing a job the operator started
    shows their steps before it performs the rest -- not all at once at the
    end."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True}))
    seen: list[int] = []

    await _earn(uow, workflow)
    saved = uow.workflow_runs.save

    async def _watch(run: WorkflowRun) -> None:
        seen.append(len([s for s in run.steps if s.verdict != "skipped"]))
        await saved(run)

    uow.workflow_runs.save = _watch  # type: ignore[method-assign]
    run = await _ran(uow, workflow, channel=channel, asker=asker, started_by="offer", from_step=1)

    assert run.outcome == "held"
    # Claimed with nothing done, the operator's step, the performed one, the finish.
    assert seen == [0, 1, 2, 2]


async def test_a_click_cannot_apply_a_value_and_the_run_stops_rather_than_guessing() -> None:
    """The wrong-carrier bug on a step that writes, refused where the truth is
    first known. The step that does not write is answered rather than refused
    -- see the two-click pick below.

    `VALUED` says a click types nothing, so a step planned as a click drops the
    run's value and goes out carrying the locators of whatever the RECORDING
    clicked. The save returns 2xx, `verify` holds it by status, and the
    warehouse has the demonstrated choice rather than the asked-for one.

    Real, and in the store: acme's `Create a Carrier Cross Reference` is done
    entirely with dropdowns -- every cited gesture is a click with no value --
    and declares `Carrier`, `Service Level` and `External System Name`.
    `StartWorkflowRun` refuses a press that leaves a declared parameter empty,
    so the operator is made to supply all three, and no click step can apply
    one of them.

    `undeliverable` cannot catch this: it asks whether `value_for` would FIND
    the name, and it does, through `step.parameters`. Nor can the miner: the
    action is the model's to choose at plan time, so a step whose recorded
    gesture is a click is routinely planned as a `type` and delivers its value
    perfectly well -- which is why the check is here and not there.
    """
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], says="pick the carrier")
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed()]})
    # Twice: the refusal costs the step its first rung, and the rescue plans it
    # again on the stronger model. A click is still a click, so it refuses
    # again -- which is the point. Nothing is ever sent.
    asker = FakeAsker(_plan("click"), _plan("click"))

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "ENVEYO"}, earned=True
    )

    assert run.outcome == "stopped", "a value that cannot be applied stops the run"
    reason = run.steps[0].reason or ""
    assert "clientCode" in reason and "cannot carry a value" in reason, reason
    assert "this step also writes" in reason, reason
    assert not [s for s in channel.sent if s["kind"] == "ui.perform"], (
        "nothing was sent: the wrong click is what this refuses, not a click that failed"
    )


async def test_a_dropdown_is_answered_with_two_clicks_and_the_second_names_the_value() -> None:
    """The other half of the wrong-carrier bug: not refusing it, doing it.

    A person answers an ExtJS combo with two clicks -- one on the field, which
    opens a floating list, and one on the row they want. So does this. The
    first command carries the demonstrated locators and answers nothing; the
    second is a click on a control whose TEXT is the value the run was given,
    so the row is named by the operator's own answer and nothing is guessed. A
    page with no such row answers `control_not_found`, which is where the
    refusal left the step anyway.
    """
    uow = await _fixture()
    # A click the recorder heard no traffic from: opening a list is allowed
    # only for a step that changes nothing, because the opening command goes
    # out ahead of the gate that withholds a write.
    workflow = await _one_step(uow, _silent_click(uow), says="pick the external system")
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed(), _performed()]})
    asker = FakeAsker(_plan("click"), _plan("click"))

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "ENVEYO"}, earned=True
    )

    clicks = [sent for sent in channel.sent if sent["kind"] == "ui.perform"]
    assert len(clicks) == 2, f"a pick is two clicks, not {len(clicks)}"
    assert [rung["strategy"] for rung in clicks[1]["payload"]["locators"]] == ["text"]
    assert clicks[1]["payload"]["locators"][0]["query"] == "ENVEYO"
    assert clicks[0]["payload"]["locators"] != clicks[1]["payload"]["locators"], (
        "the first click is the demonstrated control, which opens the list"
    )
    assert run.steps[0].verdict != "failed", run.steps[0].reason


async def test_a_step_that_writes_still_refuses_rather_than_opening_a_list() -> None:
    """The opening click is sent from inside the planning loop, ahead of the
    gate that withholds a write from a dry run and parks one on a person. A
    step whose own evidence made a mutation must not have a command sent from
    there, so it keeps the refusal."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], says="save the carrier")
    channel = FakeChannel({**_looks(8), "ui.perform": [_performed(), _performed()]})
    asker = FakeAsker(_plan("click"), _plan("click"))

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "ENVEYO"}, earned=True
    )

    assert run.outcome == "stopped"
    assert "this step also writes" in (run.steps[0].reason or "")
    assert not [sent for sent in channel.sent if sent["kind"] == "ui.perform"]


async def test_a_click_that_was_asked_for_nothing_is_performed_as_before() -> None:
    """The mirror, and the reason the refusal is scoped to a value the run
    actually supplied. Every Save and every tab click in this suite is a click
    step, and none of them takes a value -- refusing those would stop every job
    this rig has."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], says="press Save", parameters=[])
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()]})
    asker = FakeAsker(_plan("click"), Answer(data={"held": True, "why": "it saved"}))

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "ENVEYO"}, earned=True
    )

    assert run.outcome == "held", "a click nobody asked to carry a value is just a click"


async def test_a_step_that_wants_a_password_keeps_saying_so_after_the_rung_gives_up() -> None:
    """The refusal has to survive the rung that produced it.

    A step that types a credential with nothing in the vault plans `none`, and
    the payload it plans names the system and the field so the panel can draw a
    box and ask the person watching for it. Then the loop reached
    `planned is None` and handed the record back to the previous rung -- which
    put `sent` back to `None`, and the operator got a step marked ✗ with
    nothing on it to act on. Found on a real login: three runs in the store
    whose password step carried no payload at all.
    """
    uow = await _fixture()
    typed = next(g for g in _evidence(uow) if g.action.kind == "type")
    assert typed.action.target is not None
    secret = replace(
        typed,
        id="ges_secret",
        action=replace(typed.action, target=replace(typed.action.target, secret=True), value=None),
    )
    await uow.gestures.add_gestures((secret,))
    workflow = Workflow(
        id="wfl_password",
        tenant=ELSEWHERE,
        title="sign in",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[Step(order=0, says="Type the password.", system=None, cites=["ges_secret"])],
        parameters=[],
    )
    run = await asyncio.wait_for(
        run_workflow(
            uow,
            workflow,
            tenant_id=TENANT,
            values={},
            channel=FakeChannel(_looks(4)),
            device_id=DEVICE,
            # The model is asked first and plans the typing; the refusal comes
            # after, from the vault having nothing under the key.
            asker=FakeAsker(_plan("type", "x")),
            plan_model="flash",
            rescue_model="pro",
            live=True,
            allow_focus=True,
            started_by="form",
            stops=Stops(),
            approvals=Approvals(),
            cap_usd=-1.0,
            # The vault this deployment has, holding nothing for this key.
            secret_for=lambda _key: _nothing_stored(),
        ),
        timeout=5,
    )

    step = run.steps[0]
    assert step.verdict == "failed"
    assert step.sent is not None, "the refusal was rolled back and left nothing to act on"
    wants = step.sent["payload"]["needs_secret"]
    assert wants["field"] and wants["system"], "a card cannot ask for a password it cannot name"
    assert "value" not in step.sent["payload"]


async def _nothing_stored() -> str | None:
    """A vault that holds no password for the key it was asked about.

    Absence and not a failure: the port says callers decide what absence means,
    and this one decides it means "ask the person watching".
    """
    return None


# --- the status a UI step can finally be held by -----------------------------


def _called(status: int, url: str = "http://127.0.0.1:63319/api/orders") -> Reply:
    return Reply(
        ok=True,
        result={"calls": [{"method": "POST", "url": url, "status": status, "started_at": 1.0}]},
    )


async def test_a_write_the_server_answered_is_held_by_its_status_and_never_photographed() -> None:
    """The lever this exists for.

    Every step of every run this deployment has performed was judged `screen`:
    a screenshot, an upload and a vision call, per step, to reach the weakest
    of the three rungs the verifier documents. A click cannot reach rung 1 on
    its own -- its reply says the control was found and clicked -- so the
    browser is asked what the page called while it was being driven, and the
    step's own demonstrated endpoint answering 200 settles it with no picture.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed(), _performed()],
            "calls.since": [_called(200), _called(200)],
        }
    )
    asker = FakeAsker(
        _plan("type", "THIRD"), Answer(data={"held": True, "why": ""}), _plan("click")
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"}, earned=True
    )

    saving = run.steps[1]
    assert (saving.verdict, saving.verdict_by) == ("held", "status"), saving.reason
    assert "200" in saving.reason
    # The step still says where it left the browser -- that is what `after_url`
    # is -- and it costs a message rather than a camera.
    assert saving.after_url
    # Three, not four: each step is looked at before it is planned, and only
    # the first step is looked at again to judge it.
    shots = [one for one in channel.sent if one["kind"] == "screenshot"]
    assert len(shots) == 3, "the saving step was photographed to reach a worse answer"


async def test_a_write_the_server_refused_fails_on_the_status_rather_than_on_a_picture() -> None:
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed(), _performed()],
            "calls.since": [_called(409), _called(409)],
        }
    )
    asker = FakeAsker(
        _plan("type", "THIRD"), Answer(data={"held": True, "why": ""}), _plan("click")
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"}, earned=True
    )

    saving = run.steps[1]
    assert (saving.verdict, saving.verdict_by) == ("failed", "status")
    assert "409" in saving.reason


async def test_a_page_that_called_nothing_this_run_recognises_is_still_looked_at() -> None:
    """Absence of evidence, which the ladder is for. A beacon on the same host
    is not this step's endpoint, and a step nobody can place by status is
    judged the way it always was."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    beacon = _called(200, "http://127.0.0.1:63319/telemetry/batch")
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed(), _performed()],
            "calls.since": [beacon, beacon],
        }
    )
    asker = FakeAsker(
        _plan("type", "THIRD"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": "the order is on the screen"}),
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"}, earned=True
    )

    saving = run.steps[1]
    assert (saving.verdict, saving.verdict_by) == ("held", "screen")
    assert len([one for one in channel.sent if one["kind"] == "screenshot"]) == 4


async def test_a_replay_is_not_judged_by_what_the_page_called() -> None:
    """This rung is for clicks, and asking it about a replay is wrong twice.

    It cannot answer: the extension sends an `http.send` through the page's own
    `fetch` in the ISOLATED world precisely so the replay does not re-enter the
    evidence plane as the operator's own action, so `calls.since` can never see
    it and the round trip buys nothing.

    And it must not answer. The rung settles a step by STATUS, and the runner
    reads `settled or await verify(...)` -- so a call the page made on its own
    to the same endpoint shape would decide the step here and skip the ladder
    entirely, taking the read-back that a re-aimed body needs with it. The 409
    scripted below is that coincidence: if the rung is consulted, this step
    fails on a status the replay never got.
    """
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1])
    channel = FakeChannel(
        {
            **_looks(2),
            "http.send": [Reply(ok=True, result={"status": 200, "body": "{}"})],
            "calls.since": [_called(409)],
        }
    )
    asker = _PerSchemaAsker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={}, started_by="offer", earned=True
    )

    step = run.steps[0]
    assert (step.verdict, step.verdict_by) == ("held", "status"), step.reason
    assert "200" in step.reason
    assert not [one for one in channel.sent if one["kind"] == "calls.since"], (
        "the browser was asked what it called about a call the browser did not make"
    )

    # And no picture of the page it did not move. A `fetch` repaints nothing,
    # so the "after" screen is the before screen: the only shot is the one the
    # planner was given.
    assert len([one for one in channel.sent if one["kind"] == "screenshot"]) == 1, (
        "a replay was photographed to judge a page it never touched"
    )


_FIRST = {"customerType": "GGD", "longDescription": "type 01", "crossDockFlag": -1}
_SECOND = {"customerType": "GKB", "longDescription": "type 02", "crossDockFlag": -1}
_CODE = "customertype-customerType"
_DESCRIPTION = "customertype-longDescription"


def _demonstrated(gesture_id: str, body: dict[str, object]) -> Gesture:
    """One doing of the save, carrying the create it produced."""
    text = json.dumps(body, ensure_ascii=False)
    return Gesture(
        id=gesture_id,
        # The run's tenant, not the workflow row's: `Workflow.tenant` in these
        # fixtures is a deliberate plant, and the evidence is looked up by the
        # tenant the run is performed for.
        tenant=TENANT.value,
        stream_id="str-1",
        batch_id="bat-1",
        at=1_000.0,
        url="http://127.0.0.1:63319/portal?siteId=SG",
        system="http://127.0.0.1:63319",
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=1_000.0, target=Target(tag="button", name="Save")),
        requests=[
            Call(
                method="POST",
                url="http://127.0.0.1:63319/api/orders?siteId=SG",
                started_at=1_000.0,
                request_body=Body(text=text, size_bytes=len(text)),
                status=201,
            ),
            # The read the page performs to show what it just made. This is
            # what `confirming_read` finds, and it is the belt that can tell a
            # truncated record from the record this run asked for.
            Call(
                method="GET",
                url="http://127.0.0.1:63319/api/orders?siteId=SG",
                started_at=1_001.0,
                request_body=None,
                status=200,
            ),
        ],
    )


async def _demonstrated_twice(uow: FakeUnitOfWork) -> Workflow:
    """The job as it is actually stored: one step citing both doings of the
    write, and the two parameters with what each was seen taking."""
    await uow.gestures.add_gestures((_demonstrated("g1", _FIRST), _demonstrated("g2", _SECOND)))
    workflow = Workflow(
        id="wfl_twice",
        tenant=ELSEWHERE,
        title="create a customer type",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(
                order=0,
                says="Click the Save button",
                system=None,
                cites=["g1", "g2"],
                parameters=[_CODE, _DESCRIPTION],
            )
        ],
        parameters=[
            {"name": _CODE, "seen_values": ["GGD", "GKB"]},
            {"name": _DESCRIPTION, "seen_values": ["type 01", "type 02"]},
        ],
    )
    await uow.workflows.save(workflow)
    return workflow


async def test_a_replay_sends_the_values_this_run_was_given_and_is_read_back() -> None:
    """The whole point, end to end and with no model in it.

    Two demonstrations of one write differing in the two fields the operator
    typed. The run supplies a third pair, the diff says which keys those are,
    the values go in, and everything else goes out exactly as the form sent it.

    And the status alone does not settle it. `csttyp truncates at 4 chars`: a
    create asking for five characters is answered 201 and the record is four,
    with nobody told -- so a body this run re-aimed is held only by a read that
    shows the value back, never by the number the endpoint returned.
    """
    uow = await _fixture()
    workflow = await _demonstrated_twice(uow)
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/portal"})] * 2,
            "http.send": [
                # The same read, asked three times over one step. First to see
                # whether the record is already there -- it is not, so the run
                # goes on -- then the write, then the read that confirms it.
                Reply(ok=True, result={"status": 200, "body": "[]"}),
                Reply(ok=True, result={"status": 201, "body": "{}"}),
                Reply(
                    ok=True,
                    result={
                        "status": 200,
                        "body": '{"customerType": "GPDP", "longDescription": "type 03"}',
                    },
                ),
            ],
        }
    )
    asker = FakeAsker()

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={_CODE: "GPDP", _DESCRIPTION: "type 03"},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
    )

    sent = [_payload(one) for one in channel.sent if one["kind"] == "http.send"]
    writes = [one for one in sent if one["method"] == "POST"]
    assert len(writes) == 1, "one call, and it is the job"
    body = json.loads(str(writes[0]["body"]))
    assert body["customerType"] == "GPDP", "the value this run was given, not the demonstration's"
    assert body["longDescription"] == "type 03"
    assert body["crossDockFlag"] == -1, "and the field nobody varied went out as it was sent"
    assert not asker.asked, "with no model anywhere in it"
    assert (run.steps[0].verdict, run.steps[0].verdict_by) == ("held", "read"), (
        "a re-aimed body held by its status is the truncation nobody is told about"
    )


async def test_a_write_the_ledger_has_watched_is_planned_without_asking_anybody() -> None:
    """The evidence settles this step, so nothing is asked.

    The cited gesture says which call the step made, the ledger says this
    deployment has already watched that `(method, path)` succeed, and there is
    nothing left for a model to decide. Asking one anyway costs a screenshot, an
    upload and a vision call -- and buys a coin flip: a step planned by a model
    is planned from scratch every run, so the same job replays the call on
    Tuesday and clicks Save on Wednesday. The one step that changes warehouse
    state is exactly where that must not be true.
    """
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 2,
            "screenshot": [Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "s"})],
            "http.send": [Reply(ok=True, result={"status": 200, "body": "{}"})],
        }
    )
    asker = FakeAsker()

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
    )

    assert run.outcome == "held"
    assert not asker.asked, "a model was asked about a step the evidence decides"
    assert run.steps[0].planned_by == "evidence", "the row names who planned it"
    assert not [one for one in channel.sent if one["kind"] == "screenshot"]
    sent = [_payload(one) for one in channel.sent if one["kind"] == "http.send"]
    assert len(sent) == 1
    # Byte for byte. A job with no parameters has nothing to re-aim, and
    # re-serialising it would change the bytes for nothing.
    assert sent[0]["body"] == '{"clientCode":"ACME-4471","dock":"D3"}'


async def test_a_call_the_ledger_has_not_watched_is_still_the_models_to_plan() -> None:
    """Narrow on purpose. The ledger is the only thing that makes replaying
    recorded bytes safe -- a write outside it carries a struck-out
    `CSRF-ENCRYPT-TOKEN` and is refused before it is routed -- so every call
    this does not cover keeps the standing preference for driving the
    interface, and keeps the model that decides it."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel({**_looks(2), "ui.perform": [_performed()]})
    asker = FakeAsker(_plan("click"), Answer(data={"held": True, "why": "saved"}))

    run = await _ran(uow, workflow, channel=channel, asker=asker, values={}, earned=True)

    assert run.steps[0].planned_by == "flash", "the plan model planned it"
    assert asker.asked, "and it was actually asked"


async def test_a_replay_that_comes_back_refused_still_falls_to_the_model() -> None:
    """First rather than instead. A replay the endpoint refused is precisely
    when clicking Save is the right next move, so the deterministic rung sits
    in front of the ladder rather than in place of it."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel(
        {
            **_looks(2),
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 3,
            "http.send": [Reply(ok=True, result={"status": 409, "body": "{}"})],
            "ui.perform": [_performed()],
        }
    )
    asker = FakeAsker(_plan("click"), Answer(data={"held": True, "why": "saved"}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
    )

    assert [one["kind"] for one in channel.sent].count("http.send") == 1, "the replay went out"
    assert run.steps[0].planned_by == "flash", "and the click that followed was the model's"
    assert run.outcome == "held"


async def test_the_steps_that_only_opened_a_form_are_not_done_when_the_write_is_a_call() -> None:
    """The job is one request and the rest is scaffolding.

    Of the six steps of `Create a Customer Type`, only step 6 changes warehouse
    state: steps 4 and 5 make no network call at all -- they are keystrokes
    into a form step 6 posts -- and step 2's thirty-four GETs are the screen
    loading. Replay the write and there is nothing left for the others to do,
    so typing into a form nobody is going to submit is a plan, a command and a
    screenshot spent to arrive where the call was going to be sent from anyway.

    Recorded, not dropped: the row still says the step existed and why it was
    not done, because the per-step trail is what a reviewer reads.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 2,
            "http.send": [Reply(ok=True, result={"status": 200, "body": "{}"})],
        }
    )
    asker = FakeAsker()

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
    )

    assert run.outcome == "held"
    assert [one.verdict for one in run.steps] == ["not_needed", "held"]
    assert "cites" in run.steps[0].reason, "the row says which evidence it stood for"
    assert not [one for one in channel.sent if one["kind"] == "ui.perform"], "nothing was typed"
    assert [one["kind"] for one in channel.sent].count("http.send") == 1
    assert not asker.asked, "and no model was asked about any of it"


async def test_a_write_the_browser_never_sent_gives_its_claim_back() -> None:
    """The claim is taken before the call and kept whatever the call answers,
    because a timeout may well have landed. That reasoning is about the wire,
    and a command the extension refused never reached it.

    Live, 2026-09-16: a run failed `no_tab_for_system` because the operator's
    warehouse session had expired, and every later run of the same job with the
    same values was refused for half an hour on the grounds that the first
    might have landed. It could not have.
    """
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel(
        {
            **_looks(8),
            # Every attempt, not one: the ladder plans again after a failure,
            # and a fake that runs out answers `not_actionable` -- a different
            # kind, which would keep the claim and pass this test for the
            # wrong reason.
            "ui.perform": [Reply(ok=False, error_kind="no_tab_for_system", error_detail="no tab")]
            * 4,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))
    approvals = Approvals()

    # `no_tab_for_system` now asks for a signed-in browser before it is a
    # failure, so this run parks once on the way to the failure it is about.
    task = asyncio.create_task(
        _ran(
            uow,
            workflow,
            channel=channel,
            asker=asker,
            values={},
            earned=True,
            approvals=approvals,
        )
    )
    approvals.approve(await _parked(approvals))
    await task

    assert isinstance(uow.tool_calls, FakeToolCallRepository)
    assert not uow.tool_calls.claimed, "the claim was held for a command that never went out"


async def test_a_write_that_timed_out_keeps_its_claim() -> None:
    """The case the claim exists for, and the line this change must not cross:
    a timeout is the one failure where the send may well have landed, so the
    key stays held and a person is told it may already have happened."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel(
        {
            **_looks(8),
            "ui.perform": [Reply(ok=False, error_kind="timeout", error_detail="no answer")] * 4,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    await _ran(uow, workflow, channel=channel, asker=asker, values={}, earned=True)

    assert isinstance(uow.tool_calls, FakeToolCallRepository)
    assert uow.tool_calls.claimed, "a write that may have landed gave its claim back"


async def test_a_run_with_no_value_for_a_parameter_goes_and_finds_one() -> None:
    """The gap the live deployment named. A press carries what somebody typed;
    a job fired by a rule, or one whose request arrived as a mail, has a
    parameter and no value -- and that used to be the end of it."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = FakeAsker(
        _plan("type", "FROMMAIL"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )
    asked: list[tuple[str, ...]] = []

    async def _gather(wanted: Sequence[str]) -> Gathered:
        asked.append(tuple(wanted))
        return Gathered(
            values={
                "clientCode": Found(
                    value="FROMMAIL", from_message="m-9", quoting="the code is FROMMAIL"
                )
            }
        )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={}, earned=True, gather_values=_gather
    )

    assert asked == [("clientCode",)], "it asked for exactly what it was missing"
    assert run.outcome == "held"
    typed = _payload(next(s for s in channel.sent if s["kind"] == "ui.perform"))
    assert typed["value"] == "FROMMAIL", "the gathered value never reached the page"
    # Where it came from, on the row: a value nobody typed is only as good as
    # the message it was read out of.
    assert run.gathered["clientCode"]["from_message"] == "m-9"
    # And the VALUE on the row, not only in the frame that found it: `perform`
    # re-reads the row and hands its values back down, so a gather kept in a
    # local is a gather every resume does again -- against a mailbox that may
    # answer differently the second time.
    assert run.values["clientCode"] == "FROMMAIL"


async def test_a_value_the_person_typed_is_not_overruled_by_the_mailbox() -> None:
    """The gather is asked only about what is missing, and what it finds is
    merged UNDER what the run was given. Said twice on purpose: a person who
    typed a value has said what they want."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = FakeAsker(
        _plan("type", "TYPED"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )
    asked: list[tuple[str, ...]] = []

    async def _gather(wanted: Sequence[str]) -> Gathered:
        asked.append(tuple(wanted))
        return Gathered(values={"clientCode": Found(value="FROMMAIL", from_message="m-9")})

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "TYPED"},
        earned=True,
        gather_values=_gather,
    )

    assert asked == [], "the mailbox was read about a value the person had already given"
    assert run.gathered == {}
    assert run.outcome == "held"


async def test_what_the_dictionary_knows_reaches_the_card_a_person_approves() -> None:
    """The one failure the ladder cannot see, answered before the write.

    A column that keeps four characters of six answers 201, the read-back shows
    the record the system actually made, and nothing in the run can tell that
    from success. The knowledge base already holds the answer -- 404 `field`
    claims read off the vendor's documentation, `customerType` among them --
    and this is the run reaching for it at the one moment a person is looking.
    """
    uow = await _fixture()
    workflow = await _demonstrated_twice(uow)
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/portal"})] * 2,
            "http.send": [Reply(ok=True, result={"status": 201, "body": "{}"})] * 3,
        }
    )
    asked: list[tuple[str, ...]] = []
    screens: list[str] = []

    async def _known(keys: tuple[str, ...], screen: str) -> Mapping[str, Mapping[str, object]]:
        asked.append(keys)
        # The screen as well as the keys: a body key does not name a form --
        # `customerType` is posted by two of them on the real base -- so the
        # lookup that reads a form's required set has to be told which screen
        # this write is going to.
        screens.append(screen)
        # The ledger's own gotcha for this endpoint, as a claim: `csttyp
        # truncates at 4 chars`, and this run asks for five.
        return {"customerType": {"labels": ["Customer Type"], "max_length": 4}}

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=FakeAsker(),
        values={_CODE: "ZV9680", _DESCRIPTION: "type 03"},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
        known_fields=_known,
    )

    assert asked == [("customerType", "longDescription")], "asked once, about what it fills"
    # And told where the write is going, so the form for THAT screen is the one
    # whose required fields apply.
    assert screens and screens[0], "the lookup was given no screen to match a form against"
    # The whole chain: the plan says which body key each value went into, the
    # dictionary says how much that key holds, and the run says so on the row a
    # person reads. Without it the write goes out, the warehouse answers 201,
    # and the record is `ZV96`.
    assert run.steps[0].notes == ["Customer Type holds 4 characters and this run supplies 6"], (
        run.steps[0].notes
    )


async def test_the_step_that_opens_the_mail_is_not_performed_once_the_mail_is_read() -> None:
    """Measured on the deployment, 2026-09-16, on a run watching a screen.

    `Create a Customer Type` begins in a mailbox, and what the recorder kept is
    the operator finding THAT afternoon's message. So the plan clicks a link
    whose text is that message -- "a customer type :- GGD, description :-
    leaning new SRO type 01" -- and a job asked for by a new mail every time
    has no such link on the screen. The run stopped at step 0 with
    `not_actionable: the page did not answer`, holding a value it had read out
    of the right mail, server-side, a second earlier.

    It is skipped in EITHER mode, which is what separates it from the collapse:
    that one is about a form whose write goes out as a call, and it is off for
    a watched run on purpose. This step's whole content happened before the run
    began. A person watching wants to see the form fill; nobody wants to watch
    their own mailbox being clicked.
    """
    uow = await _fixture()
    # The job first, then the mail gesture: `_workflow` cites whatever evidence
    # the unit of work holds when it is called, so a gesture added before it
    # becomes the Save step's own citation and makes that step a mail step too.
    workflow = await _workflow(uow)
    mail = _demonstrated("mail-1", {"threadId": "t1"})
    mail.url = "https://mail.google.com/mail/u/0/#inbox/t1"
    mail.system = "https://mail.google.com"
    await uow.gestures.add_gestures((mail,))
    # Numbered from zero, with the rest moved along: a step at order -1 is one
    # the press says the operator already did, which is a different rule and
    # not the one under test.
    for step in workflow.steps:
        step.order += 1
    workflow.steps.insert(
        0, Step(order=0, says="Open the email", system=None, cites=["mail-1"], parameters=[])
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = FakeAsker(
        _plan("type", "FROMMAIL"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    async def _gather(wanted: Sequence[str]) -> Gathered:
        return Gathered(
            values={
                "clientCode": Found(
                    value="FROMMAIL", from_message="m-9", quoting="the code is FROMMAIL"
                )
            }
        )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        watched=True,
        gather_values=_gather,
    )

    assert run.steps[0].verdict == "not_needed", run.steps[0]
    assert "only opened the request" in run.steps[0].reason
    # And nothing was driven at the mailbox. The old failure was a click sent
    # there naming a message from the recording.
    assert not [
        one for one in channel.sent if "mail.google.com" in json.dumps(one.get("payload") or {})
    ], "it drove the operator's mailbox"
    # The rest of the job is performed as normal: this rule is about one step,
    # not about watched runs.
    assert [one.verdict for one in run.steps[1:]] == ["held", "held"], run.steps


async def test_a_step_that_sends_a_mail_is_not_a_step_that_reads_one() -> None:
    """Measured on the deployment, 2026-09-17 at 03:59.

    The job that answers a request by replying to it happens entirely in a
    mailbox. The first version of the mail rule read "every gesture is in a
    mailbox" as "this step only opened the request", skipped all five steps,
    and reported the run `held` -- a job that sends a mail, having sent none
    and saying it worked. Nobody goes looking after a success.

    Sending is a WRITE. It happens where the request arrived, which is a fact
    about mailboxes and not about what the step does.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    # A gesture in the mailbox that POSTs: Gmail's own send.
    sending = _demonstrated("mail-send", {"threadId": "t1"})
    sending.url = "https://mail.google.com/mail/u/0/#inbox/t1"
    sending.system = "https://mail.google.com"
    sending.requests = [
        replace(sending.requests[0], url="https://mail.google.com/mail/u/0/sendmessage")
    ]
    await uow.gestures.add_gestures((sending,))
    for step in workflow.steps:
        step.order += 1
    workflow.steps.insert(
        0, Step(order=0, says="Send the reply", system=None, cites=["mail-send"], parameters=[])
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel({**_looks(6), "ui.perform": [_performed()] * 3})
    asker = FakeAsker(
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
        _plan("type", "TYPED"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "TYPED"},
        earned=True,
        watched=True,
    )

    assert run.steps[0].verdict == "held", run.steps[0]


async def test_a_run_that_skipped_every_step_did_not_do_the_job() -> None:
    """The belt under the rule above, because the rule will be wrong again.

    A run whose every step is `not_needed` performed nothing, sent nothing and
    made nothing. It said `held` -- on the deployment, for a real job -- and a
    run that claims the job is done and did not do it is worse than one that
    fails.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    mail = _demonstrated("mail-1", {"threadId": "t1"})
    mail.url = "https://mail.google.com/mail/u/0/#inbox/t1"
    mail.system = "https://mail.google.com"
    mail.requests = []
    await uow.gestures.add_gestures((mail,))
    # Every step of this job is a reading of the mail, so every step is skipped.
    workflow.steps = [
        Step(order=0, says="Open the email", system=None, cites=["mail-1"], parameters=[]),
        Step(order=1, says="Read the code", system=None, cites=["mail-1"], parameters=[]),
    ]
    await uow.workflows.save(workflow)

    run = await _ran(
        uow,
        workflow,
        channel=FakeChannel({**_looks(4)}),
        asker=FakeAsker(),
        values={},
        earned=True,
        watched=True,
    )

    assert [one.verdict for one in run.steps] == ["not_needed", "not_needed"]
    assert run.outcome == "stopped", "a run that did nothing at all reported the job done"
    assert "nothing was done" in run.steps[-1].reason


async def test_the_mail_step_is_skipped_even_when_the_run_gathered_nothing() -> None:
    """The version of this rule that asked whether the GATHER read the mail,
    and the press that got past it.

    Measured on the deployment, 2026-09-16 at 21:11: the panel's own look had
    already pulled the code out of the message, so the press carried every
    value and the run gathered nothing -- `gathered` empty, the rule silent,
    and step 0 failed exactly as it had before the rule existed.

    `gathered` says which of the two things read the mail. This step does not
    care: by the time a run exists the request has been read, because a run
    cannot start without its values. And opening that mail could never work
    anyway -- the link the plan clicks names the message from the recording.
    """
    uow = await _fixture()
    # The job first, then the mail gesture: `_workflow` cites whatever evidence
    # the unit of work holds when it is called, so a gesture added before it
    # becomes the Save step's own citation and makes that step a mail step too.
    workflow = await _workflow(uow)
    mail = _demonstrated("mail-1", {"threadId": "t1"})
    mail.url = "https://mail.google.com/mail/u/0/#inbox/t1"
    mail.system = "https://mail.google.com"
    await uow.gestures.add_gestures((mail,))
    for step in workflow.steps:
        step.order += 1
    workflow.steps.insert(
        0, Step(order=0, says="Open the email", system=None, cites=["mail-1"], parameters=[])
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel({**_looks(6), "ui.perform": [_performed()] * 3})
    asker = FakeAsker(
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
        _plan("type", "TYPED"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "TYPED"},
        earned=True,
        watched=True,
    )

    assert run.steps[0].verdict == "not_needed", run.steps[0]
    # And the rest of the job is performed, which is what keeps this rule about
    # one step rather than about mail-shaped jobs.
    assert [one.verdict for one in run.steps[1:]] == ["held", "held"], run.steps


async def test_a_replay_names_its_own_screen_even_when_it_is_not_the_first_command() -> None:
    """Measured on the deployment's own row, 2026-09-16.

    `Create a Customer Type` step 1 is "Open an email" and carries 15 writes --
    Gmail's own -- so it is not scaffolding and it is performed. Steps 2 to 5
    collapse. The replay is therefore the SECOND command, by which time the
    run's first-command `starts_on` has been spent on the mail, and the call
    wants a Blue Yonder tab to read `CSRF-ENCRYPT-TOKEN` off while the browser
    is in Gmail. It failed `no_tab_for_origin` for an operator who had not left
    a warehouse tab open.

    So the page is taken from THIS step's own demonstrations, which name its
    own system by construction -- and `opensFor` still refuses a `starts_on`
    whose origin is not the command's, so it can only open the page the call
    is going to. That is the distinction the 2026-09-15 failure turned on: what
    dragged a cross-system job back to its first system was sending every step
    the page the RUN began on.
    """
    uow = await _fixture()
    mail = _demonstrated("m1", {"threadId": "t1"})
    mail.url = "https://mail.example/mail/u/0/#inbox/t1"
    mail.system = "https://mail.example"
    mail.requests[0] = replace(mail.requests[0], url="https://mail.example/sync")
    await uow.gestures.add_gestures((mail,))
    workflow = await _demonstrated_twice(uow)
    workflow.steps.insert(
        0, Step(order=-1, says="Open the email", system=None, cites=["m1"], parameters=[])
    )
    await uow.workflows.save(workflow)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed()],
            "http.send": [Reply(ok=True, result={"status": 201, "body": "{}"})] * 3,
        }
    )
    asker = FakeAsker(_plan("click"), Answer(data={"held": True, "why": "opened"}))

    await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={_CODE: "GPDP", _DESCRIPTION: "type 03"},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
    )

    call = next(
        one
        for one in channel.sent
        if one["kind"] == "http.send" and _payload(one)["method"] == "POST"
    )
    opens = _payload(call).get("starts_on")
    assert opens is not None, "the second command had no page to open a tab at"
    assert str(opens).startswith("http://127.0.0.1:63319"), (
        "and it names the system the call is going to, not the mail the run began in"
    )


async def test_a_collapsed_first_step_does_not_get_to_say_where_the_run_opens() -> None:
    """`starts_on` is the page the extension OPENS a tab at when the operator's
    own is somewhere else, and it is taken from the step the run begins at.

    Collapse the steps that only opened the form and the step it is taken from
    is one the run never performs -- on a cross-system job that is "Open an
    email", so a run whose one command is a warehouse call would name the
    operator's mail. `opensFor` in `commands.js` drops a `starts_on` whose
    origin is not the command's, so nothing is ever driven into the wrong
    system; but then no tab is opened either, and a run whose operator has no
    warehouse tab open fails instead of opening one.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/portal"})] * 2,
            "http.send": [Reply(ok=True, result={"status": 200, "body": "{}"})],
        }
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=FakeAsker(),
        values={},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
    )

    assert run.steps[0].verdict == "not_needed"
    call = next(one for one in channel.sent if one["kind"] == "http.send")
    opens = _payload(call).get("starts_on")
    assert opens is not None, "the run could not open a tab to begin"
    assert opens.startswith("http://127.0.0.1:63319"), (
        "and it names the system the call is going to, not the one a skipped step sat on"
    )


async def test_a_form_step_is_still_done_when_the_write_is_not_a_call() -> None:
    """The collapse is tied to the replay, not to the shape of the job. With no
    ledger row the write goes out as a click, so the form still has to be
    filled and every step is performed exactly as it was."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = FakeAsker(
        _plan("type", "THIRD"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"}, earned=True
    )

    assert [one.verdict for one in run.steps] == ["held", "held"]
    assert len([one for one in channel.sent if one["kind"] == "ui.perform"]) == 2


# --- what a run finds out, and what the next one does with it ----------------


class _ByRung(FakeAsker):
    """`FakeAsker` answered by which question was asked.

    The sight rung has a schema of its own, and a positional queue has to be
    rewritten every time a belt changes how many questions a step asks.
    """

    def __init__(self, *, plan: Answer, sight: Answer, verdicts: list[Answer]) -> None:
        super().__init__()
        self.plan, self.sight, self.verdicts = plan, sight, list(verdicts)

    async def ask(self, **asked: object) -> Answer:
        await super().ask(**asked)
        schema = asked["schema"]
        assert isinstance(schema, dict)
        fields = schema["properties"]
        assert isinstance(fields, dict)
        if "held" in fields:
            return self.verdicts.pop(0) if self.verdicts else Answer(data={"held": True, "why": ""})
        return self.sight if "points_at" in fields else self.plan


def _last_run(uow: FakeUnitOfWork) -> WorkflowRun:
    return sorted(uow.workflow_runs.rows.values(), key=lambda one: one.started_at)[-1]


async def test_a_run_keeps_the_control_a_picture_found() -> None:
    """The half that was missing, and the reason this system repeated itself.

    A step whose recorded identity no longer matches is found by a rung further
    down -- and until now that discovery lived for one command. Measured on the
    deployment, 2026-09-17: the rung that looks at a picture worked out three
    times in one afternoon that the control is called "Customer Types", and the
    job knew no more at the end of it than at the start.

    `mark_stale` already said the step was about to break. This says what
    worked instead.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks_with_size(6),
            # The recorded identity misses; the point a picture found does not.
            "ui.perform": [
                Reply(ok=False, error_kind="control_not_found", error_detail="nothing matched")
            ]
            * 2,
            "ui.perform_at": [
                Reply(
                    ok=True,
                    result={
                        "performed": True,
                        "candidates": 1,
                        "control": {"tag": "span", "name": "Customer Types"},
                    },
                )
            ],
        }
    )
    # By schema rather than by call order: a run asks a different number of
    # questions depending on which belt verifies each step, and the sight rung
    # has a schema of its own.
    asker = _ByRung(
        plan=_plan("click"),
        sight=Answer(
            data={
                "found": True,
                "points_at": "the_control",
                "x": 40,
                "y": 50,
                "action": "click",
                "why": "there it is",
            }
        ),
        # Only the one: a command the browser refused is never verified, so
        # the two failed rungs ask nothing and the picture's own answer is the
        # first verdict there is.
        verdicts=[Answer(data={"held": True, "why": "it opened"})],
    )

    await _ran(uow, workflow, channel=channel, asker=asker, values={}, earned=True)

    kept = await uow.workflows.learned_for(workflow.id)
    assert kept, [(one.verdict, one.matched_by, one.reason[:60]) for one in _last_run(uow).steps]
    assert (kept[0].strategy, kept[0].query) == ("text", "Customer Types")
    assert kept[0].found_by == "sight"


async def test_the_next_run_tries_what_the_last_one_found_first() -> None:
    """And it is tried FIRST, above the recorded ladder -- which has already
    failed at least once, because that is the only way anything gets written
    there. The recorded identity stays underneath: a page repaired tomorrow
    goes back to being found the strong way."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    await uow.workflows.remember_locator(
        workflow.id,
        LearnedStep(ord=0, strategy="text", query="Customer Types", found_by="sight"),
    )
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed("text"), _performed()]})
    asker = FakeAsker(
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    await _ran(uow, workflow, channel=channel, asker=asker, values={}, earned=True)

    sent = _payload(next(one for one in channel.sent if one["kind"] == "ui.perform"))
    ladder = [(one["strategy"], one["query"]) for one in sent["locators"]]
    assert ladder[0] == ("text", "Customer Types"), ladder
    assert len(ladder) > 1, "the demonstration's own ladder was thrown away"


# --- which of the two ways this run does the job -----------------------------


async def test_a_watched_run_does_the_job_on_the_screen() -> None:
    """The mode decision, one half.

    A press in an open panel means *show me*. Somebody is sitting in front of
    the screen, and a run that answers by posting a call leaves them looking at
    a form that never moved -- the record appears, the page does not, and the
    only honest thing they can conclude is that nothing happened. So a watched
    run performs every step: the field is typed, Save is pressed, and what they
    see is what was done.

    The evidence here is exactly the evidence that collapses an unwatched run
    -- a ledger row for `POST /api/orders`, earned standing -- and the run
    still fills the form. Nothing about the JOB decides this. The person does.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed(), _performed()]})
    asker = FakeAsker(
        _plan("type", "WATCHED"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "WATCHED"},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
        watched=True,
    )

    assert [one.verdict for one in run.steps] == ["held", "held"], run.steps
    assert len([one for one in channel.sent if one["kind"] == "ui.perform"]) == 2
    # And the call is not ALSO made. Either the form is filled and Save is
    # pressed, or the call is replayed and neither happens -- both is two
    # records in a warehouse that wanted one.
    assert not [
        one
        for one in channel.sent
        if one["kind"] == "http.send" and _payload(one)["method"] != "GET"
    ], "a watched run filled the form and posted the call as well"


async def test_a_watched_run_that_cannot_fill_the_form_still_makes_the_write() -> None:
    """The fallback the write step's own could not reach.

    Measured on the deployment, 2026-09-17 at 10:40. The run stopped on
    "Navigate to the Customer Types screen" -- a step with no call of its own,
    two steps before the one that has one. A run stops at its first failed
    step, so the write it was on its way to was never tried, though the call
    was sitting there the whole time.

    So a watched run gives up on the SCREEN rather than on the job: the steps
    that were only scaffolding for the write collapse, exactly as an unwatched
    run would have had them from the start.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(10),
            # The form-filling step is where the page refuses.
            "ui.perform": [
                Reply(ok=False, error_kind="not_actionable", error_detail="the page did not answer")
            ]
            * 3,
            "http.send": [Reply(ok=True, result={"status": 201, "body": "{}"})] * 2,
        }
    )
    asker = FakeAsker(
        _plan("type", "WATCHED"),
        Answer(data={"held": False, "why": "nothing happened on the screen"}),
        _plan("type", "WATCHED"),
        Answer(data={"held": False, "why": "nothing happened on the screen"}),
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
        watched=True,
    )

    assert run.steps[0].verdict == "not_needed", run.steps[0]
    assert "going out as a call" in run.steps[0].reason
    wrote = [
        one
        for one in channel.sent
        if one["kind"] == "http.send" and _payload(one).get("method") == "POST"
    ]
    assert wrote, [(one.verdict, one.reason[:60]) for one in run.steps]
    # And it tried the screen first, which is what watching is for.
    assert any(one["kind"] == "ui.perform" for one in channel.sent)


async def test_a_watched_run_falls_back_to_the_call_when_the_screen_will_not_take_it() -> None:
    """Watching must not mean "and if the page cannot be driven, do not do it".

    Measured on the deployment, 2026-09-16 and into the 17th: every UI step
    ever attempted on the warehouse host failed -- a loaded page that answered
    nothing at all -- while the same write went through as a call on the first
    try. The operator had pressed yes. A system that answers "I could not click
    it" while holding a call it knows works is refusing for the wrong reason.

    The screen is tried first and fully -- plan from the evidence, plan again,
    look at a picture -- and the call is what happens instead of stopping.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(12),
            # The form fills. Then the button the write is behind answers the
            # way that host answers: nothing ran, so nothing can be said about
            # a control.
            "ui.perform": [
                _performed(),
                *[
                    Reply(
                        ok=False,
                        error_kind="not_actionable",
                        error_detail="the page did not answer",
                    )
                ]
                * 3,
            ],
            "http.send": [Reply(ok=True, result={"status": 201, "body": "{}"})] * 3,
        }
    )
    asker = FakeAsker(
        _plan("type", "WATCHED"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": False, "why": "nothing happened on the screen"}),
        _plan("click"),
        Answer(data={"held": False, "why": "nothing happened on the screen"}),
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
        watched=True,
    )

    sent = [one["kind"] for one in channel.sent]
    assert "ui.perform" in sent, "it went to the call without trying the screen"
    assert "http.send" in sent, "the screen refused it and the run stopped anyway"
    assert sent.index("ui.perform") < sent.index("http.send"), (
        "the call came before the screen a person was watching"
    )
    # The write itself, not the read the runner does first to see whether the
    # record is already there. Whether this fixture's read-back can then
    # confirm the effect is `verify`'s business and has its own tests; what is
    # under test here is that the run reached for the call at all instead of
    # stopping on a page that would not answer.
    wrote = [
        one
        for one in channel.sent
        if one["kind"] == "http.send" and _payload(one).get("method") == "POST"
    ]
    assert wrote, ("|".join(sent), [(one.verdict, one.reason) for one in run.steps])


async def test_an_unwatched_run_replays_the_call() -> None:
    """The other half, and the same job.

    At three in the morning nobody is looking, so the fastest correct thing is
    the right thing: the call the demonstration already made goes back out and
    the form-filling steps collapse to `not_needed`. This test exists beside
    the one above to hold the pair together -- if a change makes both runs do
    the same thing, one of these two fails.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(2),
            "http.send": [Reply(ok=True, result={"status": 201, "body": "{}"})],
        }
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=FakeAsker(),
        # No value: the demonstrated body carries its own, and a run that
        # supplies one the body never carried is refused a replay rather than
        # sent with the wrong code in it -- which is `_assigned`'s doing and has
        # its own tests.
        values={},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
    )

    assert run.steps[0].verdict == "not_needed", "the form step was filled anyway"
    assert [one["kind"] for one in channel.sent].count("http.send") == 1
    assert not [one for one in channel.sent if one["kind"] == "ui.perform"]


# --- a write that would only make a second copy ------------------------------


async def test_a_write_whose_effect_is_already_true_is_not_made_again() -> None:
    """The run that made this worth writing signed in an operator who was
    already signed in. The class behind it is wider -- a rule fires twice, two
    browsers take one job, a card is answered a day late -- and every one of
    them ends with a second record in a warehouse that wanted one.

    The verifier's second rung, asked before the write instead of after: the
    page's own read already shows the value this run would supply, so there is
    nothing to do.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed()],
            "http.send": [
                # The precondition read, answering with the record already
                # there under the code this run was going to create.
                Reply(ok=True, result={"status": 200, "body": '{"clientCode": "THIRD"}'}),
            ],
        }
    )
    asker = _ByRungAsker(
        plans=[_plan("type", "THIRD"), _replay()],
        sights=[],
        verdict=Answer(data={"held": True, "why": "ok"}),
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"clientCode": "THIRD"}, earned=True
    )

    saving = run.steps[1]
    assert (saving.verdict, saving.verdict_by) == ("held", "read")
    assert saving.result == {"skipped": True, "already": True}
    assert "already shows the value" in (saving.reason or "")
    posts = [one for one in channel.sent if _payload(one).get("method") == "POST"]
    assert posts == [], "the warehouse was given a second copy of a record it already had"
    # Not a write this run made: what earns a job the right to write unasked is
    # a write that was watched to hold, and this one never went.
    assert [key for key in _effects(uow) if key[1] == run.id] == []


async def test_a_record_that_only_matches_on_the_unchanged_half_is_not_this_one() -> None:
    """The defect four live runs found, which every test here missed by
    carrying exactly one value.

    A job carries values that change from run to run beside values that do
    not -- an order's reference, a facility, a site. Asked with `any`, the
    precondition reads the PREVIOUS record, sees the unchanged half match, and
    skips the write. On 2026-09-15 that was four live runs of a three-step job
    against a real page: a new client code each time, the same reference, all
    four reported `held`, and the page received nothing.

    Every value, or it is not this record.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed()],
            "http.send": [
                # The record BEFORE this one: same reference, different code.
                Reply(
                    ok=True,
                    result={
                        "status": 200,
                        "body": '{"clientCode": "FIRST", "reference": "PO-88213"}',
                    },
                ),
                Reply(ok=True, result={"status": 201, "body": "{}"}),
            ],
            "calls.since": [Reply(ok=True, result={"calls": []})] * 4,
        }
    )
    asker = _ByRungAsker(
        plans=[_plan("type", "SECOND"), _replay()],
        sights=[],
        verdict=Answer(data={"held": True, "why": "ok"}),
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={"clientCode": "SECOND", "reference": "PO-88213"},
        earned=True,
    )

    saving = run.steps[1]
    assert "already shows the value" not in (saving.reason or "")
    posts = [one for one in channel.sent if _payload(one).get("method") == "POST"]
    assert posts, "the write was skipped on the previous record's reference"


async def test_a_value_the_page_is_merely_scoped_to_does_not_skip_a_write() -> None:
    """The false positive worth being strict about.

    A run carries its context as well as its content -- a facility, a site, a
    screen -- and the page's read is addressed to it, so that value is in the
    probe's own url AND in everything it returns. Matching on it would skip a
    write for a record nobody has created. Here the run's only value is the
    one the read is addressed to (`/api/stream`), so the read proves nothing
    and the write goes.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed()],
            "http.send": [
                Reply(ok=True, result={"status": 200, "body": '{"scope": "stream"}'}),
                Reply(ok=True, result={"status": 200, "body": "{}", "headers": {}}),
            ],
        }
    )
    asker = _ByRungAsker(
        plans=[_plan("type", "stream"), _replay()],
        sights=[],
        verdict=Answer(data={"held": True, "why": "ok"}),
    )

    run = await _ran(
        uow, workflow, channel=channel, asker=asker, values={"scope": "stream"}, earned=True
    )

    posts = [one for one in channel.sent if _payload(one).get("method") == "POST"]
    assert posts, "the write was skipped over a value that only says which screen this is"
    assert run.steps[1].verdict == "held"


async def test_two_runs_of_one_job_with_one_set_of_values_write_once() -> None:
    """The double fire, from the panel's side: a rule fires twice, two browsers
    take one job, a card is answered while another run of it is still going.
    The warehouse gets one record.

    Keyed by the job, the step and the values -- never the run id, because two
    runs are the whole point -- and claimed before the send and kept whatever
    it answers: a timeout is the one case where the write may well have landed.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    values = {"clientCode": "ONCE-9"}

    async def _go() -> WorkflowRun:
        channel = FakeChannel(
            {
                **_looks(4),
                "ui.perform": [_performed(), _performed()],
                "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 2,
                "calls.since": [Reply(ok=True, result={"calls": []})] * 2,
            }
        )
        asker = _ByRungAsker(
            plans=[_plan("type", "ONCE-9"), _plan("click")],
            sights=[],
            verdict=Answer(data={"held": True, "why": "ok"}),
        )
        return await _ran(uow, workflow, channel=channel, asker=asker, values=values, earned=True)

    first, second = await _go(), await _go()

    assert first.steps[1].verdict == "held"
    assert second.steps[1].verdict == "failed"
    assert "may have landed" in (second.steps[1].reason or "")


async def test_the_same_job_with_different_values_is_a_different_write() -> None:
    """A job done every morning is done every morning. What makes two writes
    one write is the values, and a new supplier is a new supplier."""
    uow = await _fixture()
    workflow = await _workflow(uow)

    async def _go(code: str) -> WorkflowRun:
        channel = FakeChannel(
            {
                **_looks(4),
                "ui.perform": [_performed(), _performed()],
                "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 2,
                "calls.since": [Reply(ok=True, result={"calls": []})] * 2,
            }
        )
        asker = _ByRungAsker(
            plans=[_plan("type", code), _plan("click")],
            sights=[],
            verdict=Answer(data={"held": True, "why": "ok"}),
        )
        return await _ran(
            uow, workflow, channel=channel, asker=asker, values={"clientCode": code}, earned=True
        )

    assert (await _go("MON-1")).steps[1].verdict == "held"
    assert (await _go("TUE-1")).steps[1].verdict == "held"


async def test_a_claim_older_than_the_window_does_not_stop_tomorrows_run() -> None:
    """A key that never expired would mean a tenant could create one supplier
    with a given code, ever. `remember` takes over a claim older than the
    window, which is the difference between this key and a connector call's."""
    uow = await _fixture()
    assert isinstance(uow.tool_calls, FakeToolCallRepository)
    at = datetime(2026, 9, 14, 9, 0, tzinfo=UTC)

    assert await uow.tool_calls.remember(TENANT, "k", tool="t", at=at)
    assert not await uow.tool_calls.remember(
        TENANT, "k", tool="t", at=at + K_SAME_WRITE_WINDOW / 2, stale_after=K_SAME_WRITE_WINDOW
    )
    assert await uow.tool_calls.remember(
        TENANT,
        "k",
        tool="t",
        at=at + K_SAME_WRITE_WINDOW * 2,
        stale_after=K_SAME_WRITE_WINDOW,
    )


# --- a job done once per thing on a list -------------------------------------


def _adding_three() -> tuple[Repeat, list[dict[str, str]]]:
    """The mail that prompted this: three equipment types in one message."""
    return Repeat(first_step=0, last_step=1), [
        {"clientCode": "8SITDOWN"},
        {"clientCode": "8STANDUP"},
        {"clientCode": "8REACHT"},
    ]


class _SaysYes(Approvals):
    """Somebody at the panel who answers every time the run stops to ask.

    A subclass rather than a task polling beside the run: the run parks by
    awaiting this register, so answering from inside it is the one place that
    cannot race the park it is answering.
    """

    async def wait_for(
        self,
        run_id: str,
        timeout: float = K_APPROVAL_WAIT_S,  # noqa: ASYNC109 - the wait IS the timeout
    ) -> bool:
        self.approve(run_id)
        return await super().wait_for(run_id, timeout)


async def test_the_body_is_done_once_for_each_thing_on_the_list() -> None:
    """A mail carrying three rows produced a run that created the first, and an
    operator did the other two by hand while watching a browser that had just
    proved it could do them."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    repeat, items = _adding_three()
    workflow.repeat = repeat
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        items=items,
        earned=True,
        # A list of more than one thing stops once after the first, to
        # show somebody what it made before it makes the rest.
        approvals=_SaysYes(),
    )

    assert [step.of_step for step in run.steps] == [0, 1, 0, 1, 0, 1]
    assert [step.item for step in run.steps] == [0, 0, 1, 1, 2, 2]
    assert [step.order for step in run.steps] == [0, 1, 2, 3, 4, 5], (
        "two rows of one run collided on their place, which is the table's own key"
    )
    assert run.outcome == "held"


async def test_each_thing_is_finished_before_the_next_is_started() -> None:
    """Three records made and two not is a half-finished run somebody can read.
    Five records each missing their last field is not."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat, items = _adding_three()
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        items=items,
        earned=True,
        # A list of more than one thing stops once after the first, to
        # show somebody what it made before it makes the rest.
        approvals=_SaysYes(),
    )

    done = [(step.item, step.of_step) for step in run.steps]
    assert done == sorted(done), "the run wandered between things rather than finishing each"


async def test_one_thing_on_the_list_is_the_job_it_always_was() -> None:
    """The property everything else in the loop depends on: a repeating job
    given one item performs exactly like a job with no repeat, so nothing else
    had to learn about repeats."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat = Repeat(first_step=0, last_step=1)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [_performed(), _performed()],
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})],
            "calls.since": [Reply(ok=True, result={"calls": []})] * 2,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "ONE"), verdict=Answer(data={"held": True}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        items=[{"clientCode": "ONE"}],
        earned=True,
    )

    assert [step.item for step in run.steps] == [None, None]
    assert [step.order for step in run.steps] == [0, 1]


async def test_each_thing_gets_its_own_write_claim() -> None:
    """The bug this would have been without it: the ledger keys a write by the
    job, the step and the VALUES, so the second thing on the list would have
    been refused as a duplicate of the first."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat, items = _adding_three()
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        items=items,
        earned=True,
        # A list of more than one thing stops once after the first, to
        # show somebody what it made before it makes the rest.
        approvals=_SaysYes(),
    )

    assert [step.verdict for step in run.steps] == ["held"] * 6
    assert not any("may have landed" in (step.reason or "") for step in run.steps)

    # And the half that not being refused does not prove: that a claim was
    # made for every thing on the list. `claimed_here` used to hold step
    # numbers, and a repeating job performs one step number once per item, so
    # items 2..N never reached the ledger at all -- nothing refused them
    # because nothing had claimed them, and a second run carrying an
    # overlapping list created the overlap twice.
    writing = [step for step in workflow.steps if step.order == 1]
    keys = {write_key(workflow.id, writing[0], {**item}) for item in items}
    assert len(keys) == 3, "the fixture's three items do not write three different things"
    assert {key for _, key in uow.tool_calls.claimed} == keys


async def test_what_the_operator_already_did_was_done_once_not_once_per_thing() -> None:
    """`from_step` is about the operator's own progress, and they made progress
    on one thing.

    A run entered at `from_step=1` after the operator filled the form for the
    first item used to mark step 0 `done_by_operator` for every OTHER item
    too -- so the second and third things on the list never had their fields
    filled, and the run pressed Save against whatever the first one had left
    on the screen. It reported `held`, with rows claiming a person had
    performed steps nobody had touched.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat, items = _adding_three()
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        items=items,
        earned=True,
        approvals=_SaysYes(),
        from_step=1,
    )

    done = [(step.of_step, step.item) for step in run.steps if step.verdict == "done_by_operator"]
    assert done == [(0, 0)], "a step the operator did once was skipped for things they never saw"
    assert [step.item for step in run.steps if step.of_step == 0] == [0, 1, 2]


async def test_a_long_list_reads_the_days_bill_again_and_stops_when_it_is_spent() -> None:
    """The cap was read at the press and never again.

    `over_cap` is asked by `StartWorkflowRun` before the run row exists, and
    appeared nowhere in the loop. A press that passed that check at $0 could
    then spend the rest of the tenant's day inside one run: 25 items of a
    four-step body is about a hundred legs, and at this deployment's measured
    $0.0118 a step that is $1.20 against a $5 day, with nothing asking.

    The bill is planted mid-run by a chat row landing after the first thing on
    the list, which is what a mining pass or another browser does while a long
    run is going.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat, items = _adding_three()
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )

    class _SpendsWhileItRuns(_PerSchemaAsker):
        """Somebody else's bill arriving mid-run."""

        def __init__(self) -> None:
            super().__init__(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))
            # Not `asked`: the parent keeps the calls it was given under that
            # name, and shadowing it turns a list into a counter three frames
            # from here.
            self.times = 0

        async def ask(self, *args: object, **kwargs: object) -> Answer:
            self.times += 1
            if self.times == 2:
                await uow.chats.record(
                    ChatReading(
                        id="cha_someone_else",
                        tenant=TENANT.value,
                        at=datetime.now(tz=UTC).isoformat(),
                        cost_usd=9.99,
                    )
                )
            return await super().ask(*args, **kwargs)

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=_SpendsWhileItRuns(),
        items=items,
        earned=True,
        approvals=_SaysYes(),
        cap_usd=5.0,
    )

    assert run.outcome == "stopped"
    assert "daily cap reached" in (run.steps[-1].reason or "")
    # Stopped at a boundary between two things on the list, so what it did is
    # whole records rather than half of one.
    assert run.steps[-1].item is not None and run.steps[-1].item > 0


async def test_a_list_longer_than_one_press_can_mean_is_refused_before_anything_is_sent() -> None:
    """An operator pressing yes on "add these" has read a mail with a handful of
    rows in it. Two hundred is either a mistake or a decision they have not
    made, and the run that would make two hundred records is not the one they
    authorised."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat = Repeat(first_step=0, last_step=1)
    channel = FakeChannel(_looks(4))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=FakeAsker(),
        items=[{"clientCode": f"C{n}"} for n in range(K_MOST_ITEMS + 1)],
        earned=True,
    )

    assert run.outcome == "refused"
    assert f"at most {K_MOST_ITEMS}" in run.steps[0].reason
    assert channel.sent == [], "a refused list still reached the browser"


class _CountsTheAsks(Approvals):
    """The register, counting how many times a run stopped to ask.

    The run's own rows cannot answer that: a step parked on a person is
    recorded `awaiting` and then rewritten with the verdict on the write that
    followed, so by the time anybody reads the run there is no trace of the
    waiting left in it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.asked = 0

    async def wait_for(
        self,
        run_id: str,
        timeout: float = K_APPROVAL_WAIT_S,  # noqa: ASYNC109 - the wait IS the timeout
    ) -> bool:
        self.asked += 1
        return await super().wait_for(run_id, timeout)


async def test_one_tap_answers_for_the_whole_list() -> None:
    """A person answering "add these three" read three rows and pressed one
    button. Asking again for the second and the third is asking them to
    authorise what they have already authorised, and a card per thing on a list
    of ten is a panel nobody reads by the fourth."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat, items = _adding_three()
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))
    approvals = _CountsTheAsks()
    answering = True

    read: list[str] = []

    async def _tap() -> None:
        """Somebody at the panel, answering whenever the run stops to ask.

        What the card SAID is read here and not off the finished run: a parked
        step is recorded `awaiting` with its question and then rewritten with
        the verdict on what followed, so by the time the run is over there is
        no trace of either.
        """
        while answering:
            with suppress(TimeoutError):
                run_id = await _parked(approvals)
                saved = await uow.workflow_runs.get(TENANT, run_id)
                if saved is not None:
                    read.append(saved.steps[-1].reason)
                approvals.approve(run_id)
            await asyncio.sleep(0.01)

    tapping = asyncio.create_task(_tap())
    run = await _ran(uow, workflow, channel=channel, asker=asker, items=items, approvals=approvals)
    answering = False
    await tapping

    assert run.outcome == "held", [step.reason for step in run.steps]
    # Two, for a list of any length: the write gate once for the whole list,
    # and once more before the second thing with the first one's result in
    # front of them. Not one per thing, which for ten things is a panel nobody
    # reads by the fourth.
    assert approvals.asked == 2, [step.reason for step in run.steps]
    assert any("the first of 3 is done" in one for one in read), (
        f"the second tap was asked for without saying what the first one made: {read}"
    )
    # Three writes went out, which is the point: two answers, three records.
    assert [one["kind"] for one in channel.sent].count("ui.perform") == 6


async def test_a_second_run_of_the_same_list_asks_again(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    """The tap answers for this list, not for the job. A second press is a
    second decision, and a run that inherited the first one's yes would be a
    write nobody authorised."""
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat, items = _adding_three()
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    # Nobody taps. The first write parks and the run fails waiting, which is
    # what a fresh list does with no answer -- the previous test's yes is not
    # in this run.
    run = await asyncio.wait_for(
        run_workflow(
            uow,
            workflow,
            tenant_id=TENANT,
            values={},
            channel=channel,
            device_id=DEVICE,
            asker=asker,
            plan_model="flash",
            rescue_model="pro",
            live=True,
            allow_focus=True,
            started_by="form",
            stops=Stops(),
            approvals=Approvals(),
            cap_usd=-1.0,
            items=items,
            run_id="run_second_list",
        ),
        timeout=5,
    )

    assert any(step.verdict == "failed" for step in run.steps)
    assert not any(step.result and step.result.get("wrote") for step in run.steps)


async def test_a_wrong_list_costs_one_record_and_not_twenty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The protection this exists for.

    A tap on "add these twenty" is one decision made before anything happened.
    The job read out of a sentence can be the wrong job -- an operator asking
    for a warehouse equipment type was once answered with a customer type --
    and the way to find that out is to do one and show them. Nobody says yes to
    the rest, so the rest is not done.
    """
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat, items = _adding_three()
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))

    # Earned, so the write gate does not ask: what is under test is the gate
    # AFTER the first thing, which asks whether a job that can write unasked
    # should go on writing.
    run = await _ran(uow, workflow, channel=channel, asker=asker, items=items, earned=True)

    done = [step for step in run.steps if step.item == 0 and step.verdict == "held"]
    assert len(done) == 2, "the first thing was not finished before the run stopped"
    assert not any(step.item == 2 for step in run.steps), "the third thing was done anyway"
    assert run.outcome == "stopped"
    assert "within" in (run.steps[-1].reason or "")


async def test_even_a_job_that_has_earned_its_autonomy_is_asked_after_the_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one place this system does not let earning through.

    Earning says a job's writes have been watched to hold over runs. It says
    nothing about whether this is the right job for what somebody just asked
    for, and that is the question a list makes expensive: a job cannot earn its
    way out of being the wrong job twenty times.
    """
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    uow = await _fixture()
    workflow = await _workflow(uow)
    workflow.repeat, items = _adding_three()
    await _earn(uow, workflow)
    channel = FakeChannel(
        {
            **_looks(12),
            "ui.perform": [_performed()] * 6,
            "http.send": [Reply(ok=True, result={"status": 404, "body": "{}"})] * 3,
            "calls.since": [Reply(ok=True, result={"calls": []})] * 6,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("type", "x"), verdict=Answer(data={"held": True}))
    approvals = _CountsTheAsks()

    run = await _ran(uow, workflow, channel=channel, asker=asker, items=items, approvals=approvals)

    assert approvals.asked == 1, "an earned job wrote the whole list without being asked once"
    # Nobody answered, so the rest was not done -- and the first one was.
    assert len([step for step in run.steps if step.item == 0 and step.verdict == "held"]) == 2
    assert not any(step.item == 2 for step in run.steps)


async def test_a_browser_that_is_not_on_the_system_is_asked_for_rather_than_failed() -> None:
    """The failure this system can do something about by asking.

    Measured live 2026-09-16: a run failed `no_tab_for_system` because the
    operator's warehouse session had expired. The job was right, the plan was
    right, the values were right, and the run died on a sentence about a tab --
    while the person who could fix it in four seconds was watching the panel it
    died in.
    """
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel(
        {
            **_looks(8),
            "ui.perform": [
                Reply(ok=False, error_kind="no_tab_for_origin", error_detail="somewhere else"),
                _performed(),
            ],
        }
    )
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))
    approvals = Approvals()

    task = asyncio.create_task(
        _ran(
            uow,
            workflow,
            channel=channel,
            asker=asker,
            values={},
            earned=True,
            approvals=approvals,
        )
    )
    run_id = await _parked(approvals)

    parked = await uow.workflow_runs.get(TENANT, run_id)
    assert parked is not None and parked.steps[-1].verdict == "awaiting"
    assert "sign in" in parked.steps[-1].reason, parked.steps[-1].reason

    approvals.approve(run_id)
    run = await task

    assert run.outcome == "held"
    # The same command, sent again. Not a different plan and not a rung up the
    # ladder: nothing was wrong with the step.
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 2


async def test_a_run_nobody_comes_back_to_says_nobody_signed_in() -> None:
    """The half of the ask that is not the happy one. A run parked forever is
    a row that says `running` on a browser nobody is sitting at, so the wait
    has an end and the end says what was waited for."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1], parameters=[])
    channel = FakeChannel(
        {
            **_looks(8),
            "ui.perform": [Reply(ok=False, error_kind="no_tab_for_system", error_detail="none")]
            * 4,
        }
    )
    asker = _PerSchemaAsker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        approvals=_RecordsTheWait(),
    )

    assert run.outcome == "stopped"
    assert "nobody signed in" in run.steps[-1].reason, run.steps[-1].reason
    # And it was asked once, not once per rung of the ladder: a panel that
    # asks the same question three times is a panel arguing with the person
    # who just answered it.
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1


async def test_a_collapsed_write_that_will_not_go_does_not_press_the_button_instead() -> None:
    """The two halves of the design, fitted together into nonsense.

    Measured on the deployment 2026-09-16, and it is the reason this test
    exists. A run whose write goes out as a CALL collapses the steps that only
    put the form on the screen -- steps 0 to 4 recorded `not_needed`, "this run
    sends as a call". The call then failed. The ladder's next rung is a model
    planning from the evidence, and what the evidence says is "click Save", so
    the run pressed Save on a form an operator had half filled an HOUR earlier.
    The warehouse refused it for an empty required field, which is the only
    reason that is a failed run rather than a wrong record.

    Individually both decisions are right. Together they are a run that skipped
    the typing because it was going to post, and then posted nothing and
    pressed the button as if it had typed.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(8),
            # The call goes out and the warehouse refuses it.
            "http.send": [Reply(ok=True, result={"status": 422, "body": '{"errors":[]}'})] * 3,
            "ui.perform": [_performed()] * 3,
        }
    )
    asker = _PerSchemaAsker(
        plan=_plan("click"), verdict=Answer(data={"held": False, "why": "not saved"})
    )

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
    )

    assert run.outcome == "stopped"
    # The call was tried. The button was not.
    assert [one["kind"] for one in channel.sent].count("http.send") == 1
    assert not [one for one in channel.sent if one["kind"] == "ui.perform"], (
        "it pressed Save on a form this run never filled"
    )
    assert "the form was never filled" in run.steps[-1].reason, run.steps[-1].reason


async def test_a_gather_that_found_nothing_stops_the_run_rather_than_licensing_it() -> None:
    """The door lets a run start with a parameter unanswered ONLY because
    something can go and look for it. Until this, a look that came back with
    nothing was read as permission to carry on.

    Measured on the deployment 2026-09-16: the gather lost a round to a 5xx
    from the model, came back empty, and the run went on to press Save on a
    form somebody else had half filled an hour earlier.
    """
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()] * 3})
    asker = FakeAsker()

    async def _found_nothing(wanted: Sequence[str]) -> Gathered:
        return Gathered(missing=tuple(wanted), why="the mailbox holds none of the values")

    run = await _ran(
        uow,
        workflow,
        channel=channel,
        asker=asker,
        values={},
        earned=True,
        gather_values=_found_nothing,
    )

    assert run.outcome == "stopped"
    assert channel.sent == [], "it drove a browser for a job it had no values for"
    assert "nobody gave a value for clientCode" in run.steps[-1].reason
    # And what the looking said, so the sentence is about this mailbox rather
    # than about the idea of one.
    assert "the mailbox holds none of the values" in run.steps[-1].reason
    # And the names, machine-readably, beside the sentence: the question the
    # operator is about to be asked is built from these, one at a time, and a
    # name parsed back out of an English sentence breaks the first time the
    # sentence is reworded.
    assert run.needs == ["clientCode"]
