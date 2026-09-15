"""The press: what is refused, in what order, and what the claimed row says.

`run_workflow` itself is proved next door in `test_runner.py`. What is here is
everything between a request and that loop: which refusals happen before a
database is touched, which happen before the job is even looked up, what the
row says once it is claimed, that it is committed before anybody could act on
it, and that the row and the loop agree about what the run is doing.

**The ordering is the point and it is tested by making it fail.** Every refusal
test below asks for something that would ALSO be refused later -- a job that
does not exist, on a browser that is not connected -- so a route that looked
the job up first passes none of them.

Nothing here is dated today. `NOW` is a February 2025 evening, six months from
any wall clock this runs against, so a use case that reached for
`datetime.now(UTC)` stamps a row nothing below asserts.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.execution import workflow_runs as door
from sro.application.execution.approvals import Approvals
from sro.application.execution.run_workflow import run_workflow
from sro.application.execution.stops import Stops
from sro.application.execution.workflow_runs import RunRefused, StartWorkflowRun
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.gesture import Action, Gesture
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import FakeAsker, FakeChannel, FakeClock, FakeUnitOfWork

TENANT = TenantId("acme")
RIVAL = TenantId("rival")

LAPTOP = DeviceId("dev-1")
DESK = DeviceId("dev-2")

WHO = PrincipalId("supervisor-9")
"""Not "form", which is what the rig defaulted `started_by` to out of the body.
The name on a warehouse write is one this system checked."""

PLAN = "gemini-3.8-flash-preview"
RESCUE = "gemini-3.1-pro-preview-rig"
"""Deliberately neither shipped default, so a use case wired to a literal --
or to the wrong one of the two model settings -- fails here."""

NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
CAP = 5.0


def test_these_fixtures_are_nowhere_near_the_wall_clock() -> None:
    assert abs(datetime.now(UTC) - NOW) > timedelta(days=2)


class _Browsers(FakeChannel):
    """Which browsers are connected, per tenant.

    `FakeChannel.online` answers `dev-1` for every tenant that asks, which
    cannot tell a check scoped by tenant from one that is not -- and the browser
    check is the one refusal that decides whose hand is on whose window.
    """

    def __init__(self, connected: Mapping[str, tuple[DeviceId, ...]] | None = None) -> None:
        super().__init__()
        # `is None`, not `or`: an empty mapping is a browser that is not
        # connected, and `{} or default` is the default.
        self._connected = dict({TENANT.value: (LAPTOP,)} if connected is None else connected)

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return self._connected.get(tenant_id.value, ())


def _ctx(tenant: TenantId = TENANT, who: PrincipalId = WHO) -> RequestContext:
    return RequestContext(tenant_id=tenant, principal_id=who)


WMS = "https://wms.acme.test"


def _workflow(
    *,
    tenant: TenantId = TENANT,
    workflow_id: str = "wfl_1",
    steps: int = 5,
    parameters: list[dict[str, object]] | None = None,
) -> Workflow:
    """Every step cites one gesture, because a mined one does: `checks.validate`
    refuses an uncited step, so a fixture without citations is a job that could
    not have been stored -- and the press now reads the evidence.

    `system=None` on every step, which is the shape the store actually holds:
    the model is not required to name one and two of the tenant's nine jobs
    carry NULL on every step. Nothing about starting a run reads it."""
    return Workflow(
        id=workflow_id,
        tenant=tenant.value,
        title="create a work area",
        narrative="the operator created a work area",
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[f"ges-{n}"]) for n in range(steps)
        ],
        parameters=[{"name": "clientCode", "seen_values": ["NEWTESTS"]}]
        if parameters is None
        else parameters,
    )


def _gesture(gesture_id: str, *, tenant: TenantId = TENANT, kind: str = "click") -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=tenant.value,
        stream_id="str-1",
        batch_id="bat-1",
        at=1_739_314_800.0,
        url=f"{WMS}/work-areas",
        system=WMS,
        tab_id=7,
        frame_url=None,
        action=Action(kind=kind, at=1_739_314_800.0, url=f"{WMS}/work-areas"),
    )


async def _held(workflow: Workflow | None = None, *, evidence: bool = True) -> FakeUnitOfWork:
    """The job, and by default the evidence it cites. `evidence=False` is the
    job whose gestures have aged out from under it."""
    uow = FakeUnitOfWork()
    job = workflow or _workflow()
    await uow.workflows.save(job)
    if evidence:
        await uow.gestures.add_gestures(
            tuple(
                _gesture(cited, tenant=TenantId(job.tenant))
                for step in job.steps
                for cited in step.cites
            )
        )
    return uow


_A_MODEL = FakeAsker()
"""A configured model, for every test that is not about there being none.
Nothing below ever asks it anything: `execute` refuses when there is no model
and hands the asker to `perform`, and the loop's own model calls are
`test_runner.py`'s."""


def _starter(
    uow: FakeUnitOfWork,
    *,
    asker: FakeAsker | None = _A_MODEL,
    channel: FakeChannel | None = None,
    cap_usd: float = CAP,
    stops: Stops | None = None,
    approvals: Approvals | None = None,
) -> StartWorkflowRun:
    return StartWorkflowRun(
        uow,
        channel=channel or _Browsers(),
        asker=asker,
        plan_model=PLAN,
        rescue_model=RESCUE,
        clock=FakeClock(NOW),
        cap_usd=cap_usd,
        stops=stops or Stops(),
        approvals=approvals or Approvals(),
    )


async def _press(
    starter: StartWorkflowRun,
    *,
    ctx: RequestContext | None = None,
    workflow_id: str = "wfl_1",
    device_id: DeviceId = LAPTOP,
    values: Mapping[str, str] | None = None,
    live: bool = False,
    allow_focus: bool = True,
    from_step: int = 0,
) -> WorkflowRun:
    return await starter.execute(
        ctx or _ctx(),
        workflow_id=workflow_id,
        device_id=device_id,
        values={"clientCode": "NEWTESTS"} if values is None else values,
        live=live,
        allow_focus=allow_focus,
        from_step=from_step,
    )


async def _billed(uow: FakeUnitOfWork, *, cost_usd: float, tenant: TenantId = TENANT) -> None:
    await uow.chats.record(
        ChatReading(
            id=f"cht_{tenant.value}_{cost_usd}",
            tenant=tenant.value,
            at=NOW.replace(hour=10).isoformat(),
            cost_usd=cost_usd,
        )
    )


async def _driving(uow: FakeUnitOfWork, *, tenant: TenantId, device: DeviceId, run_id: str) -> None:
    """A row this browser is already running, as the last press left it."""
    await uow.workflow_runs.save(
        WorkflowRun(
            id=run_id,
            tenant=tenant.value,
            workflow_id="wfl_1",
            device_id=device.value,
            values={},
            started_by=WHO.value,
            live=False,
            allow_focus=True,
            started_at=NOW.isoformat(),
        )
    )


# --- the refusals, in the order they have to happen --------------------------


async def test_a_deployment_with_no_model_starts_nothing() -> None:
    """503, before a session is opened. A run plans every step on a model, so a
    deployment with none must not claim a row it can never drive."""
    uow = await _held()

    with pytest.raises(AskerUnavailable):
        await _press(_starter(uow, asker=None))

    assert uow.workflow_runs.rows == {}, "a run was claimed with nothing to plan it"
    assert uow.commits == 0


async def test_a_day_that_has_spent_its_cap_starts_no_run() -> None:
    """429, and before the browser is asked anything: a run plans every step on
    a model, and the numbers say which of the two facts stopped it."""
    uow = await _held()
    await _billed(uow, cost_usd=5.01)

    with pytest.raises(OverCap) as refused:
        await _press(_starter(uow))

    assert "5.0100" in str(refused.value) and "5.00" in str(refused.value)
    assert uow.workflow_runs.rows == {}


async def test_another_tenants_spending_does_not_stop_this_one() -> None:
    """The cap is summed per tenant. Crossed with the browser check below on
    purpose: two correct axes that never meet is how a hardcoded tenant
    survives a suite."""
    uow = await _held()
    await _billed(uow, cost_usd=99.0, tenant=RIVAL)

    claimed = await _press(_starter(uow))

    assert claimed.outcome == "running"


async def test_an_unplugged_browser_is_answered_before_the_workflow_is_looked_up() -> None:
    """Ruling R4's ordering, made to fail rather than asserted in prose.

    The job asked for does not exist either. "your browser is not connected" is
    the answer a person can act on, and it holds whatever they asked for.
    """
    uow = await _held()

    with pytest.raises(Conflict) as refused:
        await _press(_starter(uow, channel=_Browsers({})), workflow_id="wfl_nope")

    assert LAPTOP.value in str(refused.value) and "not connected" in str(refused.value)
    assert "wfl_nope" not in str(refused.value)


async def test_the_cap_is_answered_before_the_browser_is_asked_anything() -> None:
    """The second position in the refusal order, made to fail rather than
    asserted in prose.

    The browser is unplugged too, and the job does not exist either -- so a
    door that checked the cap after the browser answers "dev-1 is not
    connected" to a tenant whose real problem is that the day is paid out, and
    a door that checked it after the workflow lookup answers a 404. Moving the
    cap check to either position passed 1630 tests: the only cap test above
    presses a connected browser at an existing job, which every ordering
    survives.
    """
    uow = await _held()
    await _billed(uow, cost_usd=5.01)

    with pytest.raises(OverCap) as refused:
        await _press(
            _starter(uow, channel=_Browsers({})),
            workflow_id="wfl_nope",
        )

    assert "5.0100" in str(refused.value)
    assert "not connected" not in str(refused.value)


class _CountsOpens(FakeUnitOfWork):
    """A unit of work that says how many times a session was taken from it."""

    def __init__(self) -> None:
        super().__init__()
        self.opens = 0

    async def __aenter__(self) -> FakeUnitOfWork:
        self.opens += 1
        return await super().__aenter__()


async def test_the_missing_model_is_answered_without_taking_a_session() -> None:
    """The first position, and the half `test_a_deployment_with_no_model...`
    above cannot see.

    That test asserts no row was claimed and nothing committed, both of which
    are true with the guard moved INSIDE `async with self._uow` -- which is why
    that mutation passed 1630 tests. The module's own argument is about the
    connection and not the row: "a 503 that first took a connection is a 503
    that made the outage slightly worse", and a pool exhausted by an outage is
    exactly when this door is pressed most.
    """
    uow = _CountsOpens()
    await uow.workflows.save(_workflow())

    with pytest.raises(AskerUnavailable):
        await _press(_starter(uow, asker=None))

    assert uow.opens == 0, "a 503 for a missing model took a session on the way out"


async def test_a_browser_connected_for_another_tenant_is_not_connected_here() -> None:
    """`online` is asked per tenant, and a check that ignored the tenant would
    let one tenant's credential reach another's browser."""
    uow = await _held()

    with pytest.raises(Conflict):
        await _press(_starter(uow, channel=_Browsers({RIVAL.value: (LAPTOP,)})))


async def test_a_browser_already_driving_a_run_is_refused_before_the_lookup() -> None:
    """One browser, one hand: two runs driving the same window interleave their
    clicks into a form neither of them can then read back.

    The job asked for does not exist either, for the ordering's sake.
    """
    uow = await _held()
    await _driving(uow, tenant=TENANT, device=LAPTOP, run_id="run_already")

    with pytest.raises(Conflict) as refused:
        await _press(_starter(uow), workflow_id="wfl_nope")

    assert "run_already" in str(refused.value), "the refusal never named the run in the way"
    assert LAPTOP.value in str(refused.value)


async def test_a_second_press_on_a_busy_browser_claims_nothing() -> None:
    """Not just "raises". A refusal that still wrote a row is a second `running`
    row on one browser, which is the exact state the check reads."""
    uow = await _held()
    starter = _starter(uow)

    first = await _press(starter)
    with pytest.raises(Conflict):
        await _press(starter)

    assert list(uow.workflow_runs.rows) == [first.id]


async def test_a_run_in_flight_on_another_browser_does_not_block_this_one() -> None:
    """Per browser, not per tenant: a warehouse worked by two people is two
    browsers, and a check scoped to the tenant would let one of them work."""
    uow = await _held()
    await _driving(uow, tenant=TENANT, device=DESK, run_id="run_elsewhere")

    claimed = await _press(_starter(uow, channel=_Browsers({TENANT.value: (LAPTOP, DESK)})))

    assert claimed.outcome == "running" and claimed.device_id == LAPTOP.value


async def test_another_tenants_run_on_the_same_browser_id_does_not_block_this_one() -> None:
    """Device ids are not global. `in_flight` is asked per tenant, and the two
    axes are crossed here rather than in two tests that never meet."""
    uow = await _held()
    await _driving(uow, tenant=RIVAL, device=LAPTOP, run_id="run_theirs")

    claimed = await _press(_starter(uow))

    assert claimed.outcome == "running"


async def test_a_workflow_id_naming_nothing_is_a_404() -> None:
    uow = await _held()

    with pytest.raises(NotFound):
        await _press(_starter(uow), workflow_id="wfl_nope")


async def test_another_tenants_workflow_is_not_this_tenants_job() -> None:
    uow = await _held(_workflow(tenant=RIVAL))

    with pytest.raises(NotFound):
        await _press(_starter(uow))


# --- the values -------------------------------------------------------------


async def test_a_value_that_is_only_whitespace_is_no_value() -> None:
    """`required` on the page passes a space, and a job run with " " as its
    client code is a job run with somebody else's. Refused as the absent value
    it is, and the refusal names the parameter without echoing what came in."""
    uow = await _held()

    with pytest.raises(RunRefused) as refused:
        await _press(_starter(uow), values={"clientCode": "   "})

    assert "clientCode" in str(refused.value)
    assert uow.workflow_runs.rows == {}


async def test_a_value_that_arrived_padded_is_stored_trimmed() -> None:
    """The whitespace rule's other half: a value with something in it is kept,
    and it is kept without the padding a form put around it."""
    uow = await _held()

    claimed = await _press(_starter(uow), values={"clientCode": "  NEWTESTS \n"})

    assert claimed.values == {"clientCode": "NEWTESTS"}


async def test_a_declared_parameter_with_no_value_at_all_is_refused() -> None:
    """The planner falls back to whatever the recording contained when a step
    has no value, which for a declared parameter is somebody else's client
    code."""
    uow = await _held()

    with pytest.raises(RunRefused) as refused:
        await _press(_starter(uow), values={})

    assert "clientCode" in str(refused.value)


async def test_a_value_the_job_never_declared_is_carried_anyway() -> None:
    """The body is the only source of values and the job's parameter list is a
    floor, not a whitelist: a step parameterised after the row was mined would
    otherwise lose its value on the way in."""
    uow = await _held()

    claimed = await _press(_starter(uow), values={"clientCode": "NEWTESTS", "zone": "4"})

    assert claimed.values == {"clientCode": "NEWTESTS", "zone": "4"}


# --- which step to start on -------------------------------------------------


@pytest.mark.parametrize("asked", [-1, 5, 99])
async def test_a_step_that_is_not_a_step_of_this_job_is_refused(asked: int) -> None:
    """Five steps, so 0..4. The bound is the job's own and not a constant."""
    uow = await _held()

    with pytest.raises(RunRefused) as refused:
        await _press(_starter(uow), from_step=asked)

    assert "0..4" in str(refused.value)
    assert uow.workflow_runs.rows == {}


async def test_from_step_true_does_not_become_step_one() -> None:
    """`True` is an `int` in Python. A caller that is not a request body -- and
    so has not been through `StartWorkflowRunRequest` -- would otherwise skip
    the operator's first step, recorded `done_by_operator` and never sent, on a
    job nobody started."""
    uow = await _held()

    with pytest.raises(RunRefused):
        await _press(_starter(uow), from_step=True)


async def test_a_job_with_no_steps_cannot_be_started() -> None:
    """`0..-1` is not a range, and a run of nothing would answer `held` having
    done nothing at all."""
    uow = await _held(_workflow(steps=0))

    with pytest.raises(RunRefused) as refused:
        await _press(_starter(uow))

    assert "no steps" in str(refused.value)


# --- the evidence the job stands on -----------------------------------------


async def test_a_job_whose_evidence_is_gone_is_refused_rather_than_started() -> None:
    """A workflow row outlives the gestures it cites, so a job that could be run
    the day it was mined can stop being one without anything rewriting it. The
    runner asks this per step, mid-run -- by which point a browser is open, the
    steps before it have been sent to a warehouse and the task is half done."""
    uow = await _held(evidence=False)

    with pytest.raises(RunRefused) as refused:
        await _press(_starter(uow))

    assert "step 0" in str(refused.value)
    assert uow.workflow_runs.rows == {}


async def test_the_refusal_names_the_step_a_person_has_to_go_and_look_at() -> None:
    """Not "this job cannot run". A job of twenty-five steps refused without a
    number is a person reading twenty-five rows of evidence to find the one the
    store lost."""
    uow = await _held()
    uow.gestures.rows.pop("ges-3")

    with pytest.raises(RunRefused) as refused:
        await _press(_starter(uow))

    assert "step 3" in str(refused.value)


async def test_a_step_citing_nothing_but_a_scroll_is_not_a_step_a_browser_can_do() -> None:
    """Present evidence is not actionable evidence: a scroll has no target, so
    it yields no locator ladder and no control to aim at. `primary_gesture`
    already says so, one step at a time, after the run has started."""
    uow = await _held()
    uow.gestures.rows["ges-2"] = _gesture("ges-2", kind="scroll")

    with pytest.raises(RunRefused) as refused:
        await _press(_starter(uow))

    assert "step 2" in str(refused.value)


async def test_a_job_whose_every_step_has_evidence_is_started() -> None:
    """The other half, and the one that makes the refusal above worth having:
    nine of nine stored jobs cite gestures that are all still there, and a guard
    that refused any of them would have shut the door on the whole tenant."""
    uow = await _held()

    claimed = await _press(_starter(uow))

    assert claimed.workflow_id == "wfl_1"
    assert uow.workflow_runs.rows != {}


async def test_evidence_missing_from_a_step_the_operator_already_did_stops_nothing() -> None:
    """The steps before `from_step` are recorded `done_by_operator` and never
    sent, so evidence they no longer have costs this run nothing. A guard that
    read the whole job would refuse every mid-job re-press of an ageing one."""
    uow = await _held()
    uow.gestures.rows.pop("ges-0")

    claimed = await _press(_starter(uow), from_step=1)

    assert claimed.from_step == 1


# --- the claimed row --------------------------------------------------------


async def test_the_claimed_row_says_everything_the_press_asked_for() -> None:
    """Every field of the press, at a value that is not this system's default:
    live where dry is the default, focus refused where it is allowed, a step
    that is not zero, a browser that is not the first one and a value that is
    not the one the recording held."""
    uow = await _held()

    claimed = await _press(
        _starter(uow, channel=_Browsers({TENANT.value: (LAPTOP, DESK)})),
        device_id=DESK,
        values={"clientCode": "THIRD"},
        live=True,
        allow_focus=False,
        from_step=4,
    )

    assert claimed.workflow_id == "wfl_1"
    assert claimed.device_id == DESK.value
    assert claimed.values == {"clientCode": "THIRD"}
    assert claimed.live is True
    assert claimed.allow_focus is False
    assert claimed.from_step == 4
    assert claimed.tenant == TENANT.value
    assert claimed.outcome == "running"
    assert claimed.finished_at is None
    assert claimed.steps == [] and claimed.withheld == []


async def test_who_started_it_is_the_authenticated_caller() -> None:
    """Never a name in a body. A request that says who authorised it is a
    signature nobody checked, and the audit trail on a warehouse write is worth
    more than that."""
    uow = await _held()

    claimed = await _press(_starter(uow), ctx=_ctx(who=PrincipalId("night-shift")))

    assert claimed.started_by == "night-shift"


async def test_the_row_is_stamped_by_the_containers_clock() -> None:
    """A use case that reached for `datetime.now(UTC)` stamps a run six months
    from the day this fixture bills."""
    uow = await _held()

    claimed = await _press(_starter(uow))

    assert claimed.started_at.startswith("2025-02-11T23:00")


async def test_the_row_is_committed_before_the_caller_is_answered() -> None:
    """The whole design. A `running` row that exists only inside the spawned
    task's first slice is a row a second press cannot see, and the two presses
    put two hands on one browser."""
    uow = await _held()

    claimed = await _press(_starter(uow))

    assert uow.commits == 1, "the claim was never committed"
    stored = await uow.workflow_runs.get(TENANT, claimed.id)
    assert stored is not None and stored.outcome == "running"


async def test_two_presses_get_two_ids() -> None:
    """A run id minted per press. Two runs sharing one id is one row overwritten
    by the other and an audit that reads as a single run."""
    uow = await _held()
    first = await _press(_starter(uow))
    first.outcome = "held"
    await uow.workflow_runs.save(first)

    second = await _press(_starter(uow))

    assert second.id != first.id and second.id.startswith("run_")


# --- the hand-off to the loop -----------------------------------------------


async def test_a_run_claimed_at_step_four_is_driven_from_step_four() -> None:
    """Task 4's field, earning itself, and the one case no test in task 4 could
    reach: `run_workflow` refuses a re-press whose `from_step` disagrees with
    the row, so a route that claims the default 0 while the body carries 4
    refuses every mid-job re-press -- and nothing at the loop's own layer would
    see it, because a claim of 0 driven at 0 agrees with itself.

    So: the row is asserted to carry 4, and the loop is then re-pressed at 4 and
    must accept it.
    """
    uow = await _held()
    starter = _starter(uow)

    claimed = await _press(starter, from_step=4)

    assert claimed.from_step == 4, "the claim did not carry the step the press asked for"
    run = await run_workflow(
        uow,
        _workflow(),
        tenant_id=TENANT,
        values=claimed.values,
        channel=FakeChannel(),
        device_id=LAPTOP,
        asker=FakeAsker(),
        plan_model=PLAN,
        rescue_model=RESCUE,
        live=claimed.live,
        allow_focus=claimed.allow_focus,
        started_by=claimed.started_by,
        stops=Stops(),
        approvals=Approvals(),
        run_id=claimed.id,
        from_step=4,
        cap_usd=-1.0,
    )
    # The four the operator did, and a fifth that was attempted rather than
    # assumed. Which verdict the fake's plan earns for it is `test_runner.py`'s
    # question; this one is about the step the loop began at.
    assert [step.verdict for step in run.steps[:4]] == ["done_by_operator"] * 4
    assert len(run.steps) == 5


async def test_a_re_press_that_moves_the_step_is_refused_by_the_loop() -> None:
    """The other side of the same guard: a re-press at a different step finishes
    a different job under this run's id."""
    uow = await _held()
    claimed = await _press(_starter(uow), from_step=4)

    with pytest.raises(ValueError, match="from step 4"):
        await run_workflow(
            uow,
            _workflow(),
            tenant_id=TENANT,
            values=claimed.values,
            channel=FakeChannel(),
            device_id=LAPTOP,
            asker=FakeAsker(),
            plan_model=PLAN,
            rescue_model=RESCUE,
            live=claimed.live,
            allow_focus=claimed.allow_focus,
            started_by=claimed.started_by,
            stops=Stops(),
            approvals=Approvals(),
            cap_usd=-1.0,
            run_id=claimed.id,
            from_step=3,
        )


async def test_perform_drives_the_run_the_row_describes() -> None:
    """`perform` takes everything off the claimed row rather than off its own
    frame, so there is one answer to "what is this run doing" -- and
    `run_workflow` reads the same row back and refuses the pair if they
    disagree. A `perform` that rebuilt the arguments would raise that
    disagreement here."""
    uow = await _held()
    starter = _starter(uow)
    claimed = await _press(starter, from_step=4, live=True, allow_focus=False)

    await starter.perform(_ctx(), claimed)

    stored = await uow.workflow_runs.get(TENANT, claimed.id)
    assert stored is not None
    assert stored.outcome == "stopped", "the run never got past the claim"
    assert [step.verdict for step in stored.steps[:4]] == ["done_by_operator"] * 4
    assert len(stored.steps) == 5
    assert stored.live is True and stored.allow_focus is False


async def test_perform_plans_on_the_plan_model_and_rescues_on_the_other(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Which model goes in which slot, read at the call rather than off the
    built object.

    Swapping the two survived 63 tests: every step would then plan on the
    rescue model -- the expensive one, the one measured at $2.00 for a
    truncated answer -- forever, on a door that runs against a live warehouse,
    while `gemini_plan_model`'s own docstring exists because a slow plan is
    felt by an operator standing at a screen. Nothing about the run's outcome
    changes, so no assertion on a finished run can see it.

    The whole keyword set is captured, not just the two, because four of these
    arguments are overwritten from the row inside `run_workflow` and so decide
    nothing -- this is the only place that says what was actually handed over,
    which is what a reader of `perform` needs to be able to check.
    """
    uow = await _held()
    starter = _starter(uow)
    claimed = await _press(starter, from_step=4, live=True, allow_focus=False)
    seen: dict[str, object] = {}

    async def _recorded(_uow: object, workflow: Workflow, **given: object) -> WorkflowRun:
        seen.update(given, workflow_id=workflow.id)
        return claimed

    monkeypatch.setattr(door, "run_workflow", _recorded)

    await starter.perform(_ctx(), claimed)

    assert seen["plan_model"] == PLAN, "every step would plan on the rescue model"
    assert seen["rescue_model"] == RESCUE
    assert seen["workflow_id"] == "wfl_1"
    assert seen["tenant_id"] == TENANT
    assert seen["run_id"] == claimed.id
    assert seen["from_step"] == 4
    assert seen["device_id"] == LAPTOP
    assert seen["asker"] is _A_MODEL
    assert seen["stops"] is starter._stops and seen["approvals"] is starter._approvals
    # The four `run_workflow` overwrites from the row. Asserted anyway, so the
    # docstring's claim that they are the ROW's values and not the request's is
    # a fact a test holds rather than a sentence.
    assert seen["values"] == claimed.values
    assert seen["live"] is True and seen["allow_focus"] is False
    assert seen["started_by"] == WHO.value


async def test_a_run_that_could_not_be_driven_at_all_does_not_stay_running() -> None:
    """Nobody is awaiting `perform`, so nobody would see it raise. A row left
    `running` is swept only by `fail_orphans` at the next process start -- a
    restart away, not a moment away -- and the panel watching it counts the
    seconds forever.

    The job is deleted between the claim and the drive, which is what a re-mine
    that dropped it does: `run_workflow` is never reached, so its own `finally`
    cannot be what closes this.
    """
    uow = await _held()
    starter = _starter(uow)
    claimed = await _press(starter)
    del uow.workflows.rows["wfl_1"]

    await starter.perform(_ctx(), claimed)

    stored = await uow.workflow_runs.get(TENANT, claimed.id)
    assert stored is not None
    assert stored.outcome == "failed" and stored.finished_at is not None
    assert stored.steps[-1].verdict == "failed"
    assert "NotFound" in stored.steps[-1].reason


async def test_a_row_the_loop_already_closed_is_left_as_the_loop_left_it() -> None:
    """`run_workflow` closes its own row in its `finally`. A second close would
    overwrite the verdict it wrote with "something raised", which is the one
    thing a reader most wants to keep."""
    uow = await _held()
    starter = _starter(uow)
    claimed = await _press(starter)
    await starter.perform(_ctx(), claimed)
    finished = await uow.workflow_runs.get(TENANT, claimed.id)
    assert finished is not None

    await starter._close(_ctx(), claimed.id, "something else went wrong")

    again = await uow.workflow_runs.get(TENANT, claimed.id)
    assert again is not None and again.outcome == finished.outcome
    assert again.steps[-1].reason == finished.steps[-1].reason
