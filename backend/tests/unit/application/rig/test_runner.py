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
from collections.abc import Mapping
from dataclasses import replace

import pytest

from sro.application.execution import run_workflow as runner_module
from sro.application.execution.approvals import K_APPROVAL_WAIT_S, Approvals
from sro.application.execution.run_workflow import (
    K_STEP_SLACK,
    _bill,
    _fell_over,
    _look,
    _now,
    _result,
    _saw_nothing,
    _target_origin,
    _withheld,
    fail_orphans,
    run_workflow,
)
from sro.application.execution.stops import Stops
from sro.application.ports.agent import DeviceUnreachable
from sro.application.ports.channel import Reply
from sro.domain.execution.belts import K_EARNED_RUNS, SCREEN_SCHEMA
from sro.domain.execution.planning import PLAN_SCHEMA, Look, Planned
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import (
    FakeAsker,
    FakeChannel,
    FakeGestureRepository,
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


async def _one_step(uow: FakeUnitOfWork, cite: str, says: str = "save") -> Workflow:
    workflow = Workflow(
        id="wfl_one",
        tenant=ELSEWHERE,
        title=says,
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[Step(order=0, says=says, system=None, cites=[cite], parameters=["clientCode"])],
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
        await super().ask(**asked)  # type: ignore[arg-type]
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
    started_by: str = "form",
    tenant_id: TenantId = TENANT,
    device_id: DeviceId = DEVICE,
    stops: Stops | None = None,
    approvals: Approvals | None = None,
    run_id: str | None = None,
    plan_model: str = "flash",
    rescue_model: str = "pro",
    earned: bool = False,
    from_step: int = 0,
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
            started_by=started_by,
            stops=stops or Stops(),
            approvals=approvals or Approvals(),
            run_id=run_id,
            from_step=from_step,
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
    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()]})
    asker = FakeAsker(
        Answer(
            data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""},
            cost_usd=0.002,
            in_tokens=100,
            out_tokens=10,
        ),
        Answer(data={"held": True, "why": ""}, cost_usd=0.001, in_tokens=50, out_tokens=5),
        _plan("click"),
    )

    run = await _ran(uow, workflow, channel=channel, asker=asker, live=False)

    assert run.steps[0].cost_usd == pytest.approx(0.003) and run.steps[0].in_tokens == 150
    assert run.cost_usd == pytest.approx(sum(s.cost_usd for s in run.steps))
    stored = await uow.workflow_runs.get(TENANT, run.id)
    assert stored is not None and stored.cost_usd == pytest.approx(run.cost_usd), "and it is saved"


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
    """The step in flight is the one that failed -- with the order the workflow
    gave it and the tokens its plan already cost -- not a fabricated one whose
    order collides with a real step's."""
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
    assert [s.order for s in run.steps] == [1, 2], "the step in flight kept its own order"
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
            "http.send": [Reply(ok=True, result={"status": 200, "body": "{}", "headers": {}})],
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
            "http.send": [Reply(ok=True, result={"status": 500, "body": "", "headers": {}})] * 2,
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
    workflow = await _one_step(uow, _ids(uow)[-1])
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


async def test_every_command_a_run_sends_names_the_caller_the_browser_and_the_run() -> None:
    """One envelope rule for the whole loop. A leaked device id must not reach a
    browser that is not the caller's, and a command with no run on it is a
    command the extension cannot show beside the tab it is driving."""
    uow = await _fixture()
    workflow = await _one_step(uow, _ids(uow)[-1])
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

    for _ in range(2):
        channel = FakeChannel(
            {**_looks(4), "ui.perform": [_performed("component"), _performed("css_path")]}
        )
        run = await _ran(uow, workflow, channel=channel, asker=asker, earned=True)
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
        await super().ask(**asked)  # type: ignore[arg-type]
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
    workflow = await _one_step(uow, _ids(uow)[-1])
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
    workflow = await _one_step(uow, _silent_click(uow), says="press Save")
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
    workflow = await _one_step(uow, "ges_read_click", says="open the tab")
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


async def test_a_dry_run_records_no_effect_even_for_a_click_it_does_send() -> None:
    """`writes()` is False for a Save whose call the recorder never saw, so a
    dry run performs it -- and a dry run's evidence earns nothing."""
    uow = await _fixture()
    workflow = await _one_step(uow, _silent_click(uow), says="press Save")
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
    workflow = await _one_step(uow, _silent_click(uow), says="press Save")
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
    assert starts == ["http://127.0.0.1:63319/"] * 2, "both steps are aimed at where the run began"


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
    so a rung planned on `{}` fills the control with what the picture said."""
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
