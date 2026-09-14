"""`/v1/workflow-runs` -- the door that starts a run in a live warehouse, and
the two reads of what it left behind.

The refusals and the claimed row are proved at their own layer in
`tests/unit/application/rig/test_start_workflow_run.py`. What is here is the
wire: that the path is not `/v1/runs`, that every field of the body reaches the
run rather than a constant, that every refusal lands on the status the rig gave
it, that the work is spawned only when a row was claimed, and that the row is
committed before the spawn rather than after it.

**The two booleans are why this file exists.** `live` and `allow_focus` reach a
real warehouse through a real browser. A route that hardcoded `live=False`
would look perfectly healthy and never write anything; one that hardcoded
`True` would write when the operator asked for a dry run. Both are pressed here
at the value that is NOT this system's default.

**Nothing spawned here is ever run.** `_Spawned` records the coroutine and
closes it: what this file asserts is that the work was handed over, and what it
would do is `test_start_workflow_run.py`'s and `test_runner.py`'s. A test that
let the task run would drive a socket that answers nothing, on a timer, after
the request it belongs to had finished.

**The reads are at the foot of the file**, and every query parameter of the
list has a test that dies if the route passes a constant instead: a door that
ignores `awaiting` and answers with everything looks perfectly fine on a
fixture where nothing is parked. The ordering is asserted on three rows, not
two -- a reversed pair agrees with a two-element assertion once in two, and
phase 4a shipped that defect twice.

**The stop button is under them**, and every refusal it makes is proved beside
a run stopped successfully in the same test. A 404 alone passes against a route
that was never registered -- same words, same `type`, same `title`, because
`_SLUGS[404]` is `NotFound.code` -- and seventeen tests in this repo had exactly
that defect. The effect asserted is `Stops.ask`, never the status code: a door
answering 202 having asked nothing is a stop button that does nothing.

**And the Yes under that**, which is the same shape and one more rule: every
refusal asserts that the wait is STILL parked, against a real `wait_for` task
rather than a spy. A door that answers 403 and releases the write anyway is
exactly what this route exists to prevent, and no status code can see it.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from contextlib import suppress
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from sro.application.execution.approvals import K_APPROVAL_WAIT_S
from sro.application.execution.pursuits import Pursuits
from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.run import Run, RunId
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Action, Gesture
from sro.domain.shared.identifiers import DeviceId, SkillId, TenantId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.app import create_app, on_start
from sro.interface.http.deps import get_container
from sro.interface.http.schemas import WorkflowRunModel
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

TENANT = TenantId("acme")
RIVAL = TenantId("rival")
LAPTOP = DeviceId("dev-1")
DESK = DeviceId("dev-2")

CAP = 3.25
"""Not the shipped 5.0, so a door wired to a default rather than to the
container's settings answers 200 where this expects 429."""

PLAN = "gemini-3.8-flash-preview-rig"
RESCUE = "gemini-3.1-pro-preview-rig"


class _Attached:
    """A browser holding a command channel. Nothing is sent down it here."""

    async def send_text(self, text: str) -> None:  # pragma: no cover - never called
        raise AssertionError("this route must not talk to a browser")


class _Spawned(Pursuits):
    """The container's pursuits, recording WHAT was handed over instead of
    running it -- and what the store had committed at the moment it was.

    Counting hand-overs is not enough and a review proved it: replacing
    `starter.perform(ctx, claimed)` with `starter._close(ctx, claimed.id, ...)`
    -- a route that claims a row, marks it failed and drives nothing -- passed
    32 tests. A coroutine that has not been started yet still carries its
    bound arguments in `cr_frame.f_locals`, so the call is readable without
    running it, which is the whole point: running it would drive a socket that
    answers nothing, after the request it belongs to has gone.
    """

    def __init__(self, uow: FakeUnitOfWork) -> None:
        super().__init__()
        self._uow = uow
        self.handed_over = 0
        self.commits_when_handed_over: list[int] = []
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def spawn(self, coroutine: Coroutine[object, object, None]) -> None:
        self.handed_over += 1
        self.commits_when_handed_over.append(self._uow.commits)
        frame = coroutine.cr_frame
        self.calls.append(
            (coroutine.__qualname__, dict(frame.f_locals) if frame is not None else {})
        )
        coroutine.close()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def spawned(uow: FakeUnitOfWork) -> _Spawned:
    return _Spawned(uow)


@pytest.fixture
def container(uow: FakeUnitOfWork, spawned: _Spawned) -> _FakeContainer:
    built = _FakeContainer(uow)
    built.settings = Settings(
        daily_usd_cap=CAP,
        gemini_plan_model=PLAN,
        gemini_rescue_model=RESCUE,
        _env_file=None,
    )
    # A deployment that has a model. `_FakeContainer` ships `None`, which is
    # what a deployment with no key gets and what most of this file is not
    # about.
    built.asker = FakeAsker()
    built.pursuits = spawned
    # Attached to the container's own sockets, which is what the route's channel
    # is built over: a test that handed the use case a fake channel would prove
    # the model and not the wiring.
    built.agent_sockets.attach(TENANT, LAPTOP, _Attached())
    return built


@pytest.fixture
async def client(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


WMS = "https://wms.acme.test"


def _workflow(workflow_id: str = "wfl_1", *, steps: int = 5, tenant: TenantId = TENANT) -> Workflow:
    """Every step cites one gesture, as a mined one does -- `checks.validate`
    refuses an uncited step -- because the press reads the evidence before it
    claims a row."""
    return Workflow(
        id=workflow_id,
        tenant=tenant.value,
        title="create a work area",
        narrative="the operator created a work area",
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[f"ges-{n}"]) for n in range(steps)
        ],
        parameters=[{"name": "clientCode", "seen_values": ["NEWTESTS"]}],
    )


def _gesture(gesture_id: str, *, tenant: TenantId = TENANT) -> Gesture:
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
        action=Action(kind="click", at=1_739_314_800.0, url=f"{WMS}/work-areas"),
    )


@pytest.fixture
async def held(uow: FakeUnitOfWork) -> Workflow:
    workflow = _workflow()
    await uow.workflows.save(workflow)
    await uow.gestures.add_gestures(
        tuple(_gesture(cited) for step in workflow.steps for cited in step.cites)
    )
    return workflow


def _body(**over: Any) -> dict[str, Any]:
    return {
        "workflow_id": "wfl_1",
        "device_id": LAPTOP.value,
        "values": {"clientCode": "NEWTESTS"},
        **over,
    }


# --- the path ---------------------------------------------------------------


async def test_the_press_does_not_live_at_the_skill_runs_path(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """`/v1/runs` already means a skill run, keyed on a `RunId`. Two aggregates
    and two id spaces cannot share a path, and phase 7 puts both on one host --
    which is the moment the collision would have become unresolvable."""
    landed = await client.post("/v1/runs", json=_body())

    assert landed.status_code != 201


# --- what a press answers with ----------------------------------------------


async def test_a_press_answers_201_with_the_row_it_claimed(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow, spawned: _Spawned
) -> None:
    """201 and the whole row, where the rig answered 202 and `{"run_id": ...}`:
    the row is committed by the time this returns, and a caller that had to poll
    for what it just created could show the operator nothing."""
    made = await client.post("/v1/workflow-runs", json=_body())

    assert made.status_code == 201
    body = made.json()
    assert body["outcome"] == "running" and body["finished_at"] is None
    assert body["id"] in uow.workflow_runs.rows
    assert spawned.handed_over == 1


async def test_the_work_handed_over_is_this_run_being_driven(
    client: httpx.AsyncClient, held: Workflow, spawned: _Spawned
) -> None:
    """Which coroutine, not how many. A route that spawned `_close` -- claim a
    row, mark it failed, drive nothing -- or `perform` with a fabricated run, a
    reset `from_step` or another caller's `ctx` would look exactly like this
    door working, and the suite counted hand-overs rather than reading them.

    The door would then be the shape this project ships repeatedly: alive on
    the wire, green in the suite, and nothing running behind it.
    """
    made = await client.post("/v1/workflow-runs", json=_body(from_step=4, live=True))

    (what, args) = spawned.calls[-1]
    assert what == "StartWorkflowRun.perform"
    handed = args["run"]
    assert handed.id == made.json()["id"]
    assert handed.from_step == 4 and handed.live is True
    assert args["ctx"].tenant_id == TENANT and args["ctx"].principal_id == f.OPERATOR


async def test_the_row_is_committed_before_the_work_is_handed_over(
    client: httpx.AsyncClient, held: Workflow, spawned: _Spawned
) -> None:
    """The ordering is the whole design, and it is asserted against a recorded
    commit count rather than against a sleep. A `running` row written inside the
    spawned task's first slice is a row a second press cannot see, and the two
    presses put two hands on one browser."""
    await client.post("/v1/workflow-runs", json=_body())

    assert spawned.commits_when_handed_over == [1]


async def test_which_job_comes_from_the_body(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """Two jobs, so a route naming the first one it found agrees with nothing."""
    await uow.workflows.save(_workflow("wfl_2"))

    made = await client.post("/v1/workflow-runs", json=_body(workflow_id="wfl_2"))

    assert made.json()["workflow_id"] == "wfl_2"


async def test_which_browser_comes_from_the_body(
    client: httpx.AsyncClient, container: _FakeContainer, held: Workflow
) -> None:
    """Two connected browsers, so a route hardcoding one of them still finds a
    socket and drives the wrong window."""
    container.agent_sockets.attach(TENANT, DESK, _Attached())

    made = await client.post("/v1/workflow-runs", json=_body(device_id=DESK.value))

    assert made.json()["device_id"] == DESK.value


async def test_the_values_come_from_the_body_trimmed(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """The body is the only source of values -- nothing the chat door understood
    is carried across on its own -- and a value padded by a form is stored the
    way it will be typed."""
    made = await client.post(
        "/v1/workflow-runs", json=_body(values={"clientCode": "  THIRD  ", "zone": "4"})
    )

    assert made.json()["values"] == {"clientCode": "THIRD", "zone": "4"}


async def test_a_live_press_claims_a_live_run(client: httpx.AsyncClient, held: Workflow) -> None:
    """The one field that decides whether a warehouse is written to. A route
    that hardcoded `live=False` looks healthy and never writes anything."""
    made = await client.post("/v1/workflow-runs", json=_body(live=True))

    assert made.json()["live"] is True


async def test_a_press_that_did_not_say_live_is_dry(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """A missing `live` is not a caller who forgot; it is the default this
    system promises. And a route hardcoding `True` would write when the operator
    asked for a dry run."""
    made = await client.post("/v1/workflow-runs", json=_body())

    assert made.json()["live"] is False


async def test_a_press_may_refuse_the_run_the_operators_screen(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """`allow_focus` defaults true and this presses the other way: a run that
    may not take focus reaches the browser as a command that declines rather
    than as one that steals the window somebody is typing in."""
    made = await client.post("/v1/workflow-runs", json=_body(allow_focus=False))

    assert made.json()["allow_focus"] is False


async def test_a_press_that_did_not_say_otherwise_may_take_focus(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    made = await client.post("/v1/workflow-runs", json=_body())

    assert made.json()["allow_focus"] is True


async def test_the_step_the_operator_reached_is_the_step_the_row_carries(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """The extension offers to finish a job somebody has already begun, and its
    Yes says how far they got. Asserted on the stored row as well as on the
    answer: `run_workflow` refuses a re-press whose `from_step` disagrees with
    the row, so a route that claims 0 while the body carries 4 refuses every
    mid-job re-press and nothing at the loop's layer would see it."""
    made = await client.post("/v1/workflow-runs", json=_body(from_step=4))

    assert made.json()["from_step"] == 4
    assert uow.workflow_runs.rows[made.json()["id"]].from_step == 4


async def test_who_started_it_is_the_credential_and_never_the_body(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """A request that says who authorised it is a signature nobody checked, and
    the audit trail on a warehouse write is worth more than that. The body names
    somebody else and the row does not believe it."""
    made = await client.post(
        "/v1/workflow-runs", json=_body(started_by="somebody-else", tenant="rival")
    )

    assert made.json()["started_by"] == f.OPERATOR.value
    assert made.json()["tenant"] == TENANT.value


async def test_a_press_by_another_tenants_credential_finds_no_job(
    container: _FakeContainer, held: Workflow
) -> None:
    """The job, the browser and the run in flight are all read per tenant. Here
    the whole door is asked as somebody else and answers about none of them."""
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant=RIVAL.value)}"},
    ) as http:
        landed = await http.post("/v1/workflow-runs", json=_body())

    # The browser, not the job: `dev-1` holds a socket for `acme` and none for
    # `rival`, and the browser is answered first.
    assert landed.status_code == 409


# --- the refusals, and the status each of them lands on ----------------------


async def test_a_deployment_with_no_model_answers_503(
    client: httpx.AsyncClient, container: _FakeContainer, held: Workflow, spawned: _Spawned
) -> None:
    container.asker = None

    landed = await client.post("/v1/workflow-runs", json=_body())

    assert landed.status_code == 503
    assert landed.headers["content-type"].startswith("application/problem+json")
    assert spawned.handed_over == 0


async def test_a_tenant_over_its_cap_answers_429(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow, spawned: _Spawned
) -> None:
    """The container's cap, not the shipped default: `CAP` is 3.25 and this day
    has spent 3.30, which a door wired to 5.0 lets through."""
    await uow.chats.record(
        ChatReading(id="cht_1", tenant=TENANT.value, at=f.T0.isoformat(), cost_usd=3.30)
    )

    landed = await client.post("/v1/workflow-runs", json=_body())

    assert landed.status_code == 429
    assert "3.25" in landed.json()["detail"]
    assert spawned.handed_over == 0


async def test_a_browser_that_is_not_connected_answers_409(
    client: httpx.AsyncClient, held: Workflow, spawned: _Spawned
) -> None:
    landed = await client.post("/v1/workflow-runs", json=_body(device_id=DESK.value))

    assert landed.status_code == 409
    assert DESK.value in landed.json()["detail"]
    assert spawned.handed_over == 0


async def test_an_unplugged_browser_is_answered_before_the_job_is_looked_up(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """Ruling R4's ordering, on the wire. The job asked for does not exist
    either; "your browser is not connected" is the answer a person can act on
    and it holds whatever they asked for."""
    landed = await client.post(
        "/v1/workflow-runs", json=_body(device_id=DESK.value, workflow_id="wfl_nope")
    )

    assert landed.status_code == 409 and DESK.value in landed.json()["detail"]


async def test_a_second_press_on_a_busy_browser_answers_409_and_starts_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow, spawned: _Spawned
) -> None:
    """One browser, one hand. Not just the status: a refusal that still spawned
    the work is the exact race the claim-before-answer exists to close, and a
    status-only assertion cannot see it."""
    first = await client.post("/v1/workflow-runs", json=_body())

    landed = await client.post("/v1/workflow-runs", json=_body())

    assert landed.status_code == 409
    assert first.json()["id"] in landed.json()["detail"]
    assert spawned.handed_over == 1
    assert len(uow.workflow_runs.rows) == 1


async def test_a_job_this_tenant_does_not_have_answers_404(
    client: httpx.AsyncClient, held: Workflow, spawned: _Spawned
) -> None:
    """The reachable job is pressed in the same test on purpose.

    Proved by deregistering the router: this test PASSED without the route
    existing at all. An unregistered path answers 404 in the same words, and
    `handed_over == 0` is equally true of a door that refused and a door that
    was never there -- so the assertions below said nothing about either.

    The same shape was found in `test_a_run_of_another_tenant_is_a_404`, which
    now reads a reachable row for the same reason. Any test whose whole claim
    is a 404 needs a second request that succeeds, or it proves a door is
    private and absent at once.
    """
    landed = await client.post("/v1/workflow-runs", json=_body(workflow_id="wfl_nope"))

    assert landed.status_code == 404
    assert spawned.handed_over == 0

    pressed = await client.post("/v1/workflow-runs", json=_body(workflow_id=held.id))

    assert pressed.status_code == 201, "the route itself is not reachable"
    assert spawned.handed_over == 1


async def test_a_declared_value_that_is_only_whitespace_answers_400(
    client: httpx.AsyncClient, held: Workflow, spawned: _Spawned
) -> None:
    """`required` on the page passes a space, and a job run with " " as its
    client code is a job run with somebody else's. 400 and not the 422 a
    malformed body gets: the body parsed and its shape was right."""
    landed = await client.post("/v1/workflow-runs", json=_body(values={"clientCode": " "}))

    assert landed.status_code == 400
    assert "clientCode" in landed.json()["detail"]
    assert spawned.handed_over == 0


async def test_a_step_that_is_not_a_step_of_this_job_answers_400(
    client: httpx.AsyncClient, held: Workflow, spawned: _Spawned
) -> None:
    landed = await client.post("/v1/workflow-runs", json=_body(from_step=5))

    assert landed.status_code == 400 and "0..4" in landed.json()["detail"]
    assert spawned.handed_over == 0


async def test_from_step_true_does_not_become_step_one(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow, spawned: _Spawned
) -> None:
    """`True` is an `int` in Python and pydantic coerces it to 1 outside strict
    mode. `{"from_step": true}` would otherwise pass every range check and skip
    the operator's first step -- recorded `done_by_operator` and never sent --
    on a job nobody started. This is the only layer where the guard can be made:
    by the time the use case sees it, `1` and `true` are the same value."""
    landed = await client.post("/v1/workflow-runs", json=_body(from_step=True))

    assert landed.status_code == 422
    assert uow.workflow_runs.rows == {}
    assert spawned.handed_over == 0


async def test_a_nested_object_in_values_is_refused_and_not_stringified(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """Coerced values, not checked ones, would turn `{"clientCode": {...}}` into
    the string `"{...}"` and type it into somebody's form."""
    landed = await client.post(
        "/v1/workflow-runs", json=_body(values={"clientCode": {"deep": "no"}})
    )

    assert landed.status_code == 422
    assert landed.headers["content-type"].startswith("application/problem+json")
    assert uow.workflow_runs.rows == {}


async def test_a_number_in_values_is_refused_rather_than_typed_as_one(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """The same rule, at the value most likely to arrive from a form: `4` is not
    `"4"`, and a wire type that coerced it would decide silently which."""
    landed = await client.post("/v1/workflow-runs", json=_body(values={"zone": 4}))

    assert landed.status_code == 422


async def test_a_browser_that_proves_itself_may_still_press(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """The auth decision, pinned rather than argued in a docstring.

    This router deliberately takes the tenant credential and NOT `/v1/chat`'s
    `TenantOnly`, because the extension sends `X-Device-Secret` on every call
    it makes (`api.js:40`) and `asking_device` answers a secret with no
    `?device_id=` beside it with a 404 before it reaches a repository
    (`asking.py:63-71`). Adding `dependencies=[TenantOnly]` tomorrow would 404
    every press from the one caller this door exists for -- and every other
    test in this file would stay green, because none of them sends the header.

    No registered device is needed to make the point: the half-pair refusal
    happens before any lookup, so a secret of any value is enough.
    """
    made = await client.post(
        "/v1/workflow-runs", json=_body(), headers={"X-Device-Secret": "whatever-this-is"}
    )

    assert made.status_code == 201, made.text


async def test_a_press_with_no_credential_is_refused(
    container: _FakeContainer, held: Workflow
) -> None:
    """A door that writes to a warehouse, registered without `ContextDep`,
    would be a public one."""
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        landed = await http.post("/v1/workflow-runs", json=_body())

    assert landed.status_code == 401


# --- the wire type the reads will share --------------------------------------


def test_a_finished_run_reaches_the_wire_whole() -> None:
    """Every field of `WorkflowRunModel` at a value that is not its default, so
    a mapping that dropped one -- or filled it with a literal -- fails here
    rather than in phase 5 against a panel.

    The backend's own field names, deliberately: the extension's `rigRun()`
    maps `outcome` onto a panel `status` and `{order, says, verdict}` onto
    `{index, outcome}`, and phase 5 deletes that layer against this rather than
    this growing rig-shaped aliases to meet it.
    """
    run = WorkflowRun(
        id="run_abc",
        tenant=TENANT.value,
        workflow_id="wfl_1",
        device_id=DESK.value,
        values={"clientCode": "THIRD"},
        started_by="night-shift",
        live=True,
        allow_focus=False,
        started_at="2025-02-11T23:00:00+00:00",
        finished_at="2025-02-11T23:04:00+00:00",
        outcome="held",
        from_step=2,
        steps=[
            RunStep(
                order=2,
                says="click Save",
                verdict="awaiting",
                verdict_by="state",
                reason="waiting on a person",
                planned_by="gemini-plan",
                sent={"kind": "ui.perform", "payload": {"value": "THIRD"}},
                result={"ok": True},
                matched_by="text",
                stale=True,
                before_url="https://wms.example/a",
                after_url="https://wms.example/b",
                in_tokens=11,
                out_tokens=22,
                thought_tokens=33,
                cost_usd=0.44,
                unpriced=True,
            )
        ],
        withheld=[{"step": 2, "planned": {"kind": "http.send"}}],
        in_tokens=11,
        out_tokens=22,
        thought_tokens=33,
        cost_usd=0.44,
        unpriced=True,
    )

    on_the_wire = WorkflowRunModel.of(run).model_dump()

    assert on_the_wire == {
        "id": "run_abc",
        "tenant": TENANT.value,
        "workflow_id": "wfl_1",
        "device_id": DESK.value,
        "values": {"clientCode": "THIRD"},
        "started_by": "night-shift",
        "live": True,
        "allow_focus": False,
        "started_at": "2025-02-11T23:00:00+00:00",
        "finished_at": "2025-02-11T23:04:00+00:00",
        "outcome": "held",
        "from_step": 2,
        "steps": [
            {
                "order": 2,
                # Where in the run, which step of the job, and which thing on
                # the list -- the last two being the same step and no list at
                # all for a job that does one thing once.
                "of_step": 0,
                "item": None,
                "says": "click Save",
                "verdict": "awaiting",
                "verdict_by": "state",
                "reason": "waiting on a person",
                "planned_by": "gemini-plan",
                "sent": {"kind": "ui.perform", "payload": {"value": "THIRD"}},
                "result": {"ok": True},
                "matched_by": "text",
                "stale": True,
                "before_url": "https://wms.example/a",
                "after_url": "https://wms.example/b",
                "in_tokens": 11,
                "out_tokens": 22,
                "thought_tokens": 33,
                "cost_usd": 0.44,
                "unpriced": True,
            }
        ],
        # Empty: this job does one thing once, which is most of them.
        "items": [],
        "withheld": [{"step": 2, "planned": {"kind": "http.send"}}],
        "in_tokens": 11,
        "out_tokens": 22,
        "thought_tokens": 33,
        "cost_usd": 0.44,
        "unpriced": True,
    }


def test_the_container_plans_on_one_model_and_rescues_on_the_other(
    container: _FakeContainer,
) -> None:
    """A clean step never touches the expensive model, and the two settings are
    one letter apart in the container. Read off the built use case rather than
    driven through a run, because which model plans is only visible on a model
    call and every one of those is `test_runner.py`'s.
    """
    starter = container.start_workflow_run()

    assert starter._plan_model == PLAN
    assert starter._rescue_model == RESCUE
    assert starter._cap_usd == CAP
    # The process-wide registers, not new ones: a tap or a stop arriving on
    # another route sets the register this run is waiting on.
    assert starter._stops is container.stops
    assert starter._approvals is container.approvals


# --- the two reads: the list to pick from, and the run itself ----------------
#
# The order these serve is the RIG's -- newest first, capped -- and it is not
# `for_workflow`'s. `for_workflow` is oldest first because `proofs` reads a
# job's writes forward through time; a person opening a list wants what
# happened last at the top, and the extension and console are written against
# the rig's shape. The port docstring used to justify its ascending order by
# citing the rig, which says the opposite; that citation is now corrected and
# this is the read that keeps the rig's promise.


def _planted(
    run_id: str,
    *,
    workflow_id: str = "wfl_1",
    tenant: TenantId = TENANT,
    device: DeviceId = LAPTOP,
    at: str = "2026-03-01T09:00:00+00:00",
    outcome: str = "held",
    steps: list[RunStep] | None = None,
) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        tenant=tenant.value,
        workflow_id=workflow_id,
        device_id=device.value,
        values={"clientCode": "NEWTESTS"},
        started_by=f.OPERATOR.value,
        live=True,
        allow_focus=False,
        started_at=at,
        finished_at=None if outcome == "running" else at,
        outcome=outcome,
        steps=steps or [],
    )


def _parked(order: int, says: str) -> RunStep:
    """A step waiting on a person, as the runner leaves it."""
    return RunStep(order=order, says=says, verdict="awaiting", sent={"kind": "ui.perform"})


async def _plant(uow: FakeUnitOfWork, *runs: WorkflowRun) -> None:
    for run in runs:
        await uow.workflow_runs.save(run)


# --- the list ---------------------------------------------------------------


async def test_the_list_is_newest_first_and_the_test_would_notice_the_reverse(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Three rows, not two: a reversed pair agrees with a two-element ordering
    assertion once in two, and phase 4a shipped exactly that defect twice.

    Newest first is the rig's order (`ORDER BY started_at DESC LIMIT ?`) and
    deliberately not `for_workflow`'s. A person opening this list is looking
    for what happened last.
    """
    await _plant(
        uow,
        _planted("run_middle", at="2026-03-01T10:00:00+00:00"),
        _planted("run_oldest", at="2026-03-01T09:00:00+00:00"),
        _planted("run_newest", at="2026-03-01T11:00:00+00:00"),
    )

    listed = await client.get("/v1/workflow-runs")

    assert listed.status_code == 200, listed.text
    assert [one["id"] for one in listed.json()] == ["run_newest", "run_middle", "run_oldest"]


async def test_which_job_to_list_comes_from_the_query(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """A route that ignored `workflow_id` and answered with everything looks
    healthy on a fixture holding one job."""
    await _plant(uow, _planted("run_mine"), _planted("run_other", workflow_id="wfl_2"))

    listed = await client.get("/v1/workflow-runs", params={"workflow_id": "wfl_2"})

    assert [one["id"] for one in listed.json()] == ["run_other"]


async def test_no_job_named_lists_every_job_of_the_tenant(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The rig's default is the empty string, which meant every job. A route
    that always narrowed to something would answer an empty list to the console
    opening cold."""
    await _plant(uow, _planted("run_mine"), _planted("run_other", workflow_id="wfl_2"))

    listed = await client.get("/v1/workflow-runs")

    assert {one["id"] for one in listed.json()} == {"run_mine", "run_other"}


async def test_the_limit_is_the_callers_and_it_keeps_the_newest(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Three rows and a limit of two, so a route passing a constant limit --
    or none -- answers three where this expects the two most recent."""
    await _plant(
        uow,
        _planted("run_middle", at="2026-03-01T10:00:00+00:00"),
        _planted("run_oldest", at="2026-03-01T09:00:00+00:00"),
        _planted("run_newest", at="2026-03-01T11:00:00+00:00"),
    )

    listed = await client.get("/v1/workflow-runs", params={"limit": 2})

    assert [one["id"] for one in listed.json()] == ["run_newest", "run_middle"]


async def test_a_limit_that_is_not_a_page_is_refused_rather_than_clamped(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The rig clamped to `max(1, min(limit, 200))`. A caller asking for 5000
    and silently getting 200 cannot tell a cap from a truncated answer, and
    FastAPI already says this once, in the place the generated client reads."""
    await _plant(uow, _planted("run_1"))

    assert (await client.get("/v1/workflow-runs", params={"limit": 0})).status_code == 422
    assert (await client.get("/v1/workflow-runs", params={"limit": 5000})).status_code == 422


async def test_the_list_holds_only_this_tenants_runs(
    container: _FakeContainer, uow: FakeUnitOfWork
) -> None:
    """Two tenants and the same job id in both: a read that dropped the tenant
    would answer with somebody else's warehouse."""
    await _plant(uow, _planted("run_mine"), _planted("run_theirs", tenant=RIVAL))

    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant=RIVAL.value)}"},
    ) as http:
        listed = await http.get("/v1/workflow-runs")

    assert [one["id"] for one in listed.json()] == ["run_theirs"]


async def test_a_run_reaches_the_list_whole_and_not_as_a_summary(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The rig's list was one line each with the full record a second request
    away. This answers with the row, so what a panel needs to render a parked
    run is already on the wire -- pinned at values that are not defaults."""
    planted = _planted("run_1", steps=[_parked(0, "click Save")])
    planted.values = {"clientCode": "THIRD"}
    planted.withheld = [{"step": 0, "planned": {"kind": "http.send"}}]
    planted.cost_usd, planted.unpriced, planted.from_step = 0.44, True, 2
    await _plant(uow, planted)

    (row,) = (await client.get("/v1/workflow-runs")).json()

    assert row == WorkflowRunModel.of(planted).model_dump()
    assert row["values"] == {"clientCode": "THIRD"} and row["from_step"] == 2
    assert row["cost_usd"] == 0.44 and row["unpriced"] is True
    assert row["withheld"] == [{"step": 0, "planned": {"kind": "http.send"}}]
    assert [step["says"] for step in row["steps"]] == ["click Save"]


# --- awaiting: the supervisor's queue ----------------------------------------


async def test_awaiting_narrows_the_list_to_the_runs_parked_on_a_person(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Two tenants x two jobs x parked-against-running, because a route that
    ignores `awaiting` and answers with everything looks perfectly fine on a
    fixture where nothing is parked.

    A second browser for the second running run: one browser holds one running
    run, and the parked steps this list is for are the ones across browsers.
    """
    await _plant(
        uow,
        _planted("run_parked", outcome="running", steps=[_parked(1, "confirm the write")]),
        _planted("run_going", outcome="running", device=DESK),
        _planted("run_done", steps=[_parked(0, "left awaiting on a finished run")]),
        _planted(
            "run_parked_elsewhere",
            workflow_id="wfl_2",
            outcome="running",
            device=DeviceId("dev-3"),
            steps=[_parked(0, "approve the move")],
        ),
        _planted(
            "run_parked_theirs",
            tenant=RIVAL,
            outcome="running",
            steps=[_parked(0, "not this tenant's queue")],
        ),
    )

    listed = await client.get("/v1/workflow-runs", params={"awaiting": "true"})

    assert {one["id"] for one in listed.json()} == {"run_parked", "run_parked_elsewhere"}


async def test_awaiting_and_a_job_narrow_together(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The rig applied both in one WHERE clause, and a route that dropped
    either would answer a supervisor about work that is not theirs to clear."""
    await _plant(
        uow,
        _planted("run_parked", outcome="running", steps=[_parked(0, "confirm")]),
        _planted(
            "run_parked_elsewhere",
            workflow_id="wfl_2",
            outcome="running",
            device=DESK,
            steps=[_parked(0, "approve")],
        ),
    )

    listed = await client.get(
        "/v1/workflow-runs", params={"awaiting": "true", "workflow_id": "wfl_2"}
    )

    assert [one["id"] for one in listed.json()] == ["run_parked_elsewhere"]


async def test_the_queue_is_narrowed_before_it_is_capped(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The rig put `id IN (...)` in the WHERE and the cap after it. A route
    that took the newest two runs and then kept the parked ones among them
    answers "nothing is waiting" to a supervisor with a queue -- the busiest
    tenant being the one it fails for."""
    await _plant(
        uow,
        _planted(
            "run_parked",
            outcome="running",
            at="2026-03-01T09:00:00+00:00",
            steps=[_parked(0, "confirm")],
        ),
        _planted("run_newer_1", at="2026-03-01T10:00:00+00:00"),
        _planted("run_newer_2", at="2026-03-01T11:00:00+00:00"),
    )

    listed = await client.get("/v1/workflow-runs", params={"awaiting": "true", "limit": 2})

    assert [one["id"] for one in listed.json()] == ["run_parked"]


async def test_awaiting_returns_every_parked_step_and_not_only_the_deepest(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The divergence this plan settles.

    The rig reported the deepest parked step of each run -- `ORDER BY ord DESC
    LIMIT 1` -- and this returns every one of them, `ord` ascending, matching
    the repository. Anyone may answer a parked run, and a queue that hides all
    but the deepest step hides work from the person who could clear it.
    """
    await _plant(
        uow,
        _planted(
            "run_parked",
            outcome="running",
            steps=[
                _parked(1, "confirm the write"),
                RunStep(order=2, says="a step nobody is waiting on", verdict="done"),
                _parked(3, "and let the second one out"),
            ],
        ),
    )

    (row,) = (await client.get("/v1/workflow-runs", params={"awaiting": "true"})).json()

    waiting = [step for step in row["steps"] if step["verdict"] == "awaiting"]
    assert [step["order"] for step in waiting] == [1, 3]
    assert [step["says"] for step in waiting] == ["confirm the write", "and let the second one out"]


async def test_a_tenant_with_nothing_parked_is_answered_with_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The rig returned `{"runs": []}` without touching the runs table. A route
    that fell through to an unfiltered query here would show a supervisor every
    run of the tenant as work waiting on them."""
    await _plant(uow, _planted("run_done"), _planted("run_going", outcome="running"))

    listed = await client.get("/v1/workflow-runs", params={"awaiting": "true"})

    assert listed.json() == []


# --- one run ----------------------------------------------------------------


async def test_the_run_asked_for_is_the_one_answered(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Two rows, so a route reading the first one it found agrees with this
    once in two."""
    await _plant(uow, _planted("run_1"), _planted("run_2", workflow_id="wfl_2"))

    read = await client.get("/v1/workflow-runs/run_2")

    assert read.status_code == 200, read.text
    assert read.json()["id"] == "run_2" and read.json()["workflow_id"] == "wfl_2"


async def test_a_run_is_read_back_whole(client: httpx.AsyncClient, uow: FakeUnitOfWork) -> None:
    """Every field at a value that is not its default, so a mapping that
    dropped one -- or a model built off a stale row -- fails here."""
    planted = _planted("run_1", steps=[_parked(2, "click Save")])
    planted.values = {"clientCode": "THIRD"}
    planted.withheld = [{"step": 2, "planned": {"kind": "http.send"}}]
    planted.in_tokens, planted.out_tokens, planted.thought_tokens = 11, 22, 33
    planted.cost_usd, planted.unpriced, planted.from_step = 0.44, True, 2
    await _plant(uow, planted)

    read = await client.get("/v1/workflow-runs/run_1")

    assert read.json() == WorkflowRunModel.of(planted).model_dump()
    assert read.json()["live"] is True and read.json()["allow_focus"] is False
    assert read.json()["in_tokens"] == 11 and read.json()["cost_usd"] == 0.44


async def test_a_run_of_another_tenant_is_a_404_and_not_a_403(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """A 403 confirms the id exists. Run ids are unguessable and the answer to
    "is this yours" must not differ from the answer to "does this exist".

    The reachable row is read in the same test on purpose: a 404 test alone
    passes against a path that was never registered, which is how a door can be
    proved private and absent at the same time.
    """
    await _plant(uow, _planted("run_mine"), _planted("run_theirs", tenant=RIVAL))

    read = await client.get("/v1/workflow-runs/run_theirs")

    assert read.status_code == 404
    assert read.headers["content-type"].startswith("application/problem+json")
    assert (await client.get("/v1/workflow-runs/run_mine")).status_code == 200


async def test_a_run_that_never_existed_is_the_same_404(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Byte for byte the answer above, which is the whole point of it."""
    await _plant(uow, _planted("run_mine"), _planted("run_theirs", tenant=RIVAL))

    missing = await client.get("/v1/workflow-runs/run_nope")
    theirs = await client.get("/v1/workflow-runs/run_theirs")

    assert missing.status_code == 404
    assert missing.json()["detail"] == theirs.json()["detail"]
    assert (await client.get("/v1/workflow-runs/run_mine")).status_code == 200


# --- who may read them -------------------------------------------------------


async def test_a_browser_that_proves_itself_may_read_the_runs(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The same auth ruling the press is pinned on, at the two reads.

    The extension sends `X-Device-Secret` on every call it makes
    (`api.js:40`), and `asking_device` answers a secret with no `?device_id=`
    beside it with a 404 before it reaches a repository. `TenantOnly` on these
    would 404 every call from the panel that shows a run -- and every other
    test in this file would stay green, because none of them sends the header.
    """
    await _plant(uow, _planted("run_1"))
    proving = {"X-Device-Secret": "whatever-this-is"}

    listed = await client.get("/v1/workflow-runs", headers=proving)
    read = await client.get("/v1/workflow-runs/run_1", headers=proving)

    assert listed.status_code == 200, listed.text
    assert read.status_code == 200, read.text


async def test_the_reads_are_refused_with_no_credential(container: _FakeContainer) -> None:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        assert (await http.get("/v1/workflow-runs")).status_code == 401
        assert (await http.get("/v1/workflow-runs/run_1")).status_code == 401


# --- the stop button --------------------------------------------------------
#
# Carried item 1 of phase 4a, closed: the loop has asked `Stops` between every
# step since it was written, and until this route existed nothing outside the
# process could set it. `StopRun` next door sets the same register for a SKILL
# run and resolves through `uow.runs`, so a workflow run's id handed to it is a
# string looked up in the wrong repository -- which is why this is a sibling and
# not an extra branch on that one.


def _running(run_id: str, *, device: DeviceId = LAPTOP, tenant: TenantId = TENANT) -> WorkflowRun:
    """A run this process is driving right now, which is the only kind that can
    be stopped."""
    return _planted(run_id, outcome="running", device=device, tenant=tenant)


async def test_the_stop_asks_for_the_run_in_the_path_and_no_other(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """Two runs the operator could be watching, so a route that asks to stop
    the first row it found -- or a literal id -- agrees with this once in two.

    The register is the assertion and the status code is not: `Stops.ask` is
    the entire effect of this door, and a route that answered 202 having asked
    nothing is a stop button that does nothing to a run driving a warehouse.
    """
    await _plant(uow, _running("run_watched"), _running("run_other", device=DESK))

    landed = await client.post("/v1/workflow-runs/run_other/abort")

    assert landed.status_code == 202, landed.text
    assert container.stops.asked("run_other")
    assert not container.stops.asked("run_watched")


async def test_the_stopped_run_is_answered_whole_and_still_says_running(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Every field at a value that is not its default, and the outcome NOT
    rewritten here.

    The row is closed by the loop, which is the only thing that knows whether
    the gesture it was mid-way through landed. A route that wrote `aborted`
    itself would be racing the task it just interrupted, and the console would
    read a finished run whose browser is still clicking.
    """
    planted = _running("run_1", device=DESK)
    planted.values = {"clientCode": "THIRD"}
    planted.withheld = [{"step": 2, "planned": {"kind": "http.send"}}]
    planted.in_tokens, planted.out_tokens, planted.thought_tokens = 11, 22, 33
    planted.cost_usd, planted.unpriced, planted.from_step = 0.44, True, 2
    planted.steps = [_parked(2, "click Save")]
    await _plant(uow, planted)

    landed = await client.post("/v1/workflow-runs/run_1/abort")

    assert landed.json() == WorkflowRunModel.of(planted).model_dump()
    assert landed.json()["outcome"] == "running" and landed.json()["finished_at"] is None
    assert landed.json()["live"] is True and landed.json()["allow_focus"] is False
    assert landed.json()["device_id"] == DESK.value and landed.json()["from_step"] == 2
    assert landed.json()["cost_usd"] == 0.44 and landed.json()["unpriced"] is True
    assert uow.workflow_runs.rows["run_1"].outcome == "running"


async def test_a_run_parked_on_a_person_wakes_now_rather_than_in_five_minutes(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The half of the seam `application/execution/approvals.py` says is
    missing: the stop sets the flag AND releases the wait.

    Without the release a stopped run sits out `K_APPROVAL_WAIT_S` and then
    fails for want of an answer -- safe, and five minutes of a person watching
    a button they already pressed. The release is not a yes: the flag is set
    first and `run_workflow` asks `Stops` on the way out of the wait, which is
    what stops this releasing a write nobody approved.
    """
    await _plant(uow, _running("run_parked"))
    container.approvals.register("run_parked")
    waiting = asyncio.ensure_future(container.approvals.wait_for("run_parked", timeout=5.0))
    await asyncio.sleep(0)

    landed = await client.post("/v1/workflow-runs/run_parked/abort")

    assert landed.status_code == 202, landed.text
    assert await waiting is True
    assert container.stops.asked("run_parked")


async def test_aborting_an_already_aborted_run_says_so_rather_than_succeeding(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """An idempotent-looking success here is a console reporting something that
    did not happen, which `StopRun`'s docstring says is worse on this screen
    than not offering the button at all.

    The reachable run is stopped in the same test: a refusal proved on its own
    passes against a door that refuses everything, and against one that was
    never registered.
    """
    await _plant(uow, _planted("run_done", outcome="aborted"), _running("run_going"))

    landed = await client.post("/v1/workflow-runs/run_done/abort")

    assert landed.status_code == 409
    assert landed.headers["content-type"].startswith("application/problem+json")
    assert "aborted" in landed.json()["detail"]
    assert not container.stops.asked("run_done")
    assert (await client.post("/v1/workflow-runs/run_going/abort")).status_code == 202


async def test_a_run_in_no_browser_is_not_one_this_process_can_stop(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The intention to stop is held in this process and honoured by the task
    driving that browser. A `running` row naming no browser is not being driven
    by one, and answering "stopping" for it is the one thing a stop control
    must never do.
    """
    homeless = _running("run_nowhere")
    homeless.device_id = ""
    await _plant(uow, homeless, _running("run_going"))

    landed = await client.post("/v1/workflow-runs/run_nowhere/abort")

    assert landed.status_code == 409
    assert "browser" in landed.json()["detail"]
    assert not container.stops.asked("run_nowhere")
    assert (await client.post("/v1/workflow-runs/run_going/abort")).status_code == 202


async def test_a_skill_runs_id_is_not_found_here_rather_than_type_confused(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The two id spaces look alike -- `run_` plus 32 hex on both sides. Pass a
    real skill run's id and get a 404, not a 500 and not somebody else's run.

    Same tenant, and `running`, so nothing but the repository tells them apart:
    a door resolving through `uow.runs` would find this row and answer about it.
    The workflow run is stopped in the same test, because a 404 alone is what an
    unregistered path answers -- in the same words, with the same `type` and
    `title`, since `_SLUGS[404]` is `NotFound.code`.
    """
    twin = "run_" + "ab" * 16
    await uow.runs.add(
        Run(
            id=RunId(twin),
            tenant_id=TENANT,
            skill_id=SkillId("some-skill"),
            skill_version=1,
            stage=PromotionStage.ASSISTED,
            parameters={},
            requested_by=f.OPERATOR,
            started_at=f.at(0),
            authorized_by=f.OPERATOR,
        )
    )
    await _plant(uow, _running("run_going"))

    landed = await client.post(f"/v1/workflow-runs/{twin}/abort")

    assert landed.status_code == 404, landed.text
    assert not container.stops.asked(twin)
    assert (await client.post("/v1/workflow-runs/run_going/abort")).status_code == 202


async def test_another_tenants_run_cannot_be_stopped_and_is_the_same_404(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The tenant is a predicate of the lookup, not a filter afterwards. A 403
    would confirm the id exists, and run ids are unguessable -- so a run of
    another tenant answers exactly what a run that never existed answers.
    """
    await _plant(uow, _running("run_theirs", tenant=RIVAL), _running("run_going"))

    theirs = await client.post("/v1/workflow-runs/run_theirs/abort")
    missing = await client.post("/v1/workflow-runs/run_nope/abort")

    assert theirs.status_code == 404 and missing.status_code == 404
    assert theirs.json()["detail"] == missing.json()["detail"]
    assert not container.stops.asked("run_theirs")
    assert (await client.post("/v1/workflow-runs/run_going/abort")).status_code == 202


async def test_a_browser_that_proves_itself_may_press_stop(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The same auth ruling as the press and the two reads, pinned here too.

    The extension sends `X-Device-Secret` on every call it makes
    (`api.js:40`), and `asking_device` answers a secret with no `?device_id=`
    beside it with a 404 before it reaches a repository. `TenantOnly` on this
    door would 404 the stop button of the one caller it exists for -- and every
    other test in this section would stay green, because none of them sends the
    header.
    """
    await _plant(uow, _running("run_going"))

    landed = await client.post(
        "/v1/workflow-runs/run_going/abort", headers={"X-Device-Secret": "whatever-this-is"}
    )

    assert landed.status_code == 202, landed.text


async def test_the_stop_is_refused_with_no_credential(
    container: _FakeContainer, uow: FakeUnitOfWork
) -> None:
    """A door that reaches into a run driving a warehouse, registered without
    `ContextDep`, would be a public one."""
    await _plant(uow, _running("run_going"))
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        landed = await http.post("/v1/workflow-runs/run_going/abort")

    assert landed.status_code == 401
    assert not container.stops.asked("run_going")


# --- and the Yes under it ----------------------------------------------------
#
# The other half of the pair the stop button opened. Without this door a run
# that parks on a person waits out `K_APPROVAL_WAIT_S` and fails for want of an
# answer -- and pressing the panel's approve button did nothing at all.
#
# Two halves must both happen and the order is the argument: the durable row
# first, committed, and only then the in-process event the parked task is
# waiting on. Event first and a failed write is a live warehouse write with no
# record of who authorised it; row first and a failed release is a run that
# times out and a tap the operator makes again. A lost tap is recoverable.
#
# Every refusal is proved beside an approval that lands in the same test, and
# every one of them asserts the EFFECT and not the status: a door that answers
# 403 and releases the wait anyway is the bug this route exists to prevent, and
# a status code cannot see it.

APPROVER = "the-secret-the-laptop-was-minted"


def _parked_run(
    run_id: str, *ords: int, device: DeviceId = LAPTOP, tenant: TenantId = TENANT
) -> WorkflowRun:
    """A `running` run with one step parked on a person per `ord` given."""
    return _planted(
        run_id,
        outcome="running",
        device=device,
        tenant=tenant,
        steps=[_parked(order, f"click Save at step {order}") for order in ords],
    )


async def _waiting_on(container: _FakeContainer, run_id: str) -> asyncio.Task[bool]:
    """A run really waiting on the register, as `run_workflow` leaves it.

    A real `wait_for` task and not a spy: this file's job is to prove the wait
    was released, and a spy asserting `Approvals.approve` was called passes
    against a route that calls it on the wrong run id.
    """
    container.approvals.register(run_id)
    # The production wait, not a short one. At `timeout=5.0` this file failed
    # 3/3 when run on its own and passed inside `tests/unit`: a park that
    # expires on the wall clock is `done()` exactly like a park the route
    # released, so `_still_waiting` read a timeout as a release and the one
    # test pinning "row before event" failed for a reason that had nothing to
    # do with the ordering it proves. Five minutes is longer than any test in
    # this suite can live, and it is the number the register itself writes
    # down.
    task = asyncio.ensure_future(container.approvals.wait_for(run_id, timeout=K_APPROVAL_WAIT_S))
    await asyncio.sleep(0)
    return task


async def _still_waiting(task: asyncio.Task[bool]) -> bool:
    """Whether the parked task is STILL parked, and tidied up either way.

    A wait that TIMED OUT is refused rather than reported: `wait_for` answers
    `False` for a park that gave up and `True` for one the route released, and
    both are `done()`. Without this the helper fails in one direction and
    passes for the wrong reason in the other -- a suite where every park had
    quietly expired would assert "not still waiting" on a door that never
    released anything and call it proof.
    """
    await asyncio.sleep(0)
    if task.done() and task.result() is False:
        raise AssertionError("the park timed out on the wall clock; this test proves nothing")
    parked = not task.done()
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    return parked


async def test_the_waiting_task_is_released_and_not_only_the_row_written(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """Both halves. A route that writes the row and never fires the event
    leaves the run parked forever with an audit trail saying it was approved --
    the worst of the three possible bugs here."""
    await _plant(uow, _parked_run("run_parked", 3))
    waiting = await _waiting_on(container, "run_parked")

    landed = await client.post("/v1/workflow-runs/run_parked/approve")

    assert landed.status_code == 200, landed.text
    assert await waiting is True
    assert ("run_parked", 3) in uow.workflow_runs.approved


async def test_an_approval_that_woke_nothing_says_so_rather_than_answering_200_and_silence(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The case an operator actually hit.

    They tapped Approve on a live login step, got a 200, and watched the
    browser sit on the same screen until they gave up: the process holding
    that run had restarted, so there was no event to set. The authorisation is
    real and the row is committed -- refusing would be a lie about that -- but
    nothing resumed, and the answer has to be able to say which.

    No `_waiting_on` here, and that absence IS the fixture: a run parked in the
    store with nobody waiting on the register is exactly a run whose process
    is gone.
    """
    await _plant(uow, _parked_run("run_abandoned", 2))

    landed = await client.post("/v1/workflow-runs/run_abandoned/approve")

    assert landed.status_code == 200, landed.text
    assert landed.json()["resumed"] is False
    assert landed.json()["first"] is True, "the authorisation still happened"
    assert ("run_abandoned", 2) in uow.workflow_runs.approved


async def test_an_approval_that_released_a_real_wait_says_it_resumed(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    await _plant(uow, _parked_run("run_held", 1))
    waiting = await _waiting_on(container, "run_held")

    landed = await client.post("/v1/workflow-runs/run_held/approve")

    assert landed.json()["resumed"] is True
    assert await waiting is True


async def test_the_approval_names_the_run_in_the_path_and_the_deepest_parked_step(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """Which run and which step, because a door that authorises SOME step of
    SOME run answers 200 exactly like this one.

    The deepest parked step, `ORDER BY ord DESC LIMIT 1`, and that is NOT the
    `awaiting` queue's rule: `WorkflowRunRepository.awaiting` returns every
    parked step of every run, `ord` ascending, because anyone may answer a
    parked run and a queue hiding all but the deepest hides work. Which step
    ONE tap authorises is a different question, and the run is parked at its
    deepest.
    """
    await _plant(uow, _parked_run("run_watched", 0, 2, 5), _parked_run("run_other", 9, device=DESK))
    waiting = await _waiting_on(container, "run_watched")
    # Off the run's own `started_at`, which `FakeClock`'s default matches
    # exactly: a route recording the row's instant instead of the clock's would
    # otherwise agree with this.
    container.clock.advance(1800)

    landed = await client.post("/v1/workflow-runs/run_watched/approve")

    assert landed.status_code == 200, landed.text
    assert landed.json()["order"] == 5
    assert await waiting is True
    assert ("run_watched", 5) in uow.workflow_runs.approved
    # WHEN the write was let out, which is the second thing an audit asks and
    # the reason the container injects a clock at all. A fixed instant here
    # passed 69 unit and 18 integration tests.
    assert uow.workflow_runs.approved[("run_watched", 5)][0] == container.clock.now().isoformat()
    assert ("run_watched", 0) not in uow.workflow_runs.approved
    assert ("run_watched", 2) not in uow.workflow_runs.approved
    assert ("run_other", 9) not in uow.workflow_runs.approved


async def test_a_browser_that_is_not_driving_this_run_cannot_release_its_write(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The check `approve`'s tenant-blindness is predicated on. Without it the
    docstring at ports/repositories.py:705 is describing a guarantee nothing
    provides.

    One compromised browser must not be able to satisfy every other browser's
    human-in-the-loop gate. Checked BEFORE the event is set, which is why the
    task is still parked below -- a 403 that released the wait anyway would be
    a warehouse write let out by a browser with no business in this run, and
    the status code alone cannot see it.
    """
    await uow.devices.add(f.device(id=DESK, secret=APPROVER))
    await _plant(uow, _parked_run("run_theirs", 1, device=LAPTOP))
    waiting = await _waiting_on(container, "run_theirs")

    landed = await client.post(
        "/v1/workflow-runs/run_theirs/approve",
        params={"device_id": DESK.value},
        headers={"X-Device-Secret": APPROVER},
    )

    assert landed.status_code == 403, landed.text
    assert landed.headers["content-type"].startswith("application/problem+json")
    # The sentence and the `type`, not just the status: a console tells "that is
    # another browser's run" from "that is another person's run" by the `type`,
    # and `NotDrivingThisRun` having no `code` of its own would answer
    # `.../error` -- which is what every unmapped refusal in the system answers.
    assert landed.json()["type"].endswith("/not_driving_this_run")
    assert "driving" in landed.json()["detail"]
    assert await _still_waiting(waiting)
    assert uow.workflow_runs.approved == {}
    # The same door, the browser that IS driving it: a refusal proved alone
    # passes against a route that refuses everything and one never registered.
    await uow.devices.add(f.device(id=LAPTOP, secret=APPROVER))
    allowed = await client.post(
        "/v1/workflow-runs/run_theirs/approve",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": APPROVER},
    )
    assert allowed.status_code == 200, allowed.text
    assert ("run_theirs", 1) in uow.workflow_runs.approved


async def test_a_step_that_is_not_awaiting_is_refused(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """Approving a step nobody parked releases nothing and records a person
    authorising a write that was never withheld."""
    walking = _planted(
        "run_walking",
        outcome="running",
        steps=[RunStep(order=0, says="open it", verdict="done", verdict_by="agent")],
    )
    await _plant(uow, walking, _parked_run("run_parked", 4, device=DESK))
    waiting = await _waiting_on(container, "run_walking")

    landed = await client.post("/v1/workflow-runs/run_walking/approve")

    assert landed.status_code == 409, landed.text
    assert "awaiting" in landed.json()["detail"]
    assert await _still_waiting(waiting)
    assert uow.workflow_runs.approved == {}
    assert (await client.post("/v1/workflow-runs/run_parked/approve")).status_code == 200


async def test_a_step_left_awaiting_on_a_finished_run_is_refused_too(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The same predicate `WorkflowRunRepository.awaiting` carries: a step left
    `awaiting` on a run that was aborted or failed is not waiting on anybody,
    and a tap on it records a person letting out a write nothing is holding."""
    stale = _planted("run_done", outcome="aborted", steps=[_parked(1, "click Save")])
    await _plant(uow, stale, _parked_run("run_going", 1, device=DESK))

    landed = await client.post("/v1/workflow-runs/run_done/approve")

    assert landed.status_code == 409, landed.text
    assert uow.workflow_runs.approved == {}
    assert (await client.post("/v1/workflow-runs/run_going/approve")).status_code == 200


async def test_the_second_tap_does_not_overwrite_the_first_authorisation(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """`approve` returns whether this tap was the one. A write rescued to the
    second rung parks at the same step and takes a second tap, and the first
    authorisation stands -- it is the one in the audit.

    The second tap still releases the wait: the run really is parked again, and
    a 409 there would leave it sitting out its five minutes.
    """
    await uow.devices.add(f.device(id=LAPTOP, secret=APPROVER))
    await _plant(uow, _parked_run("run_rescued", 2))
    container.clock.advance(1800)
    tapped_at = container.clock.now().isoformat()
    first = await client.post(
        "/v1/workflow-runs/run_rescued/approve",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": APPROVER},
    )
    # A different instant for the second tap, so "the row was overwritten" and
    # "the row stood" are two different values here and not one.
    container.clock.advance(1800)
    waiting = await _waiting_on(container, "run_rescued")

    second = await client.post("/v1/workflow-runs/run_rescued/approve")

    assert first.status_code == 200 and first.json()["first"] is True
    assert second.status_code == 200, second.text
    assert second.json()["first"] is False
    assert second.json()["order"] == 2
    assert await waiting is True
    # Both halves of the row are the first tapper's: the browser and the moment.
    assert uow.workflow_runs.approved[("run_rescued", 2)] == (tapped_at, LAPTOP.value)


async def test_the_browser_written_down_is_the_one_that_proved_itself(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Who tapped is what an audit asks first, and this row is the answer.

    The browser comes off the credential's own pair -- `?device_id=` beside
    `X-Device-Secret` -- and never off a field in a body. A request that says
    who authorised it is a signature nobody checked, which is the ruling
    `StartWorkflowRunRequest` already made about `started_by`.
    """
    await uow.devices.add(f.device(id=LAPTOP, secret=APPROVER))
    await _plant(uow, _parked_run("run_tapped", 7))

    landed = await client.post(
        "/v1/workflow-runs/run_tapped/approve",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": APPROVER},
        json={"device_id": DESK.value},
    )

    assert landed.status_code == 200, landed.text
    assert uow.workflow_runs.approved[("run_tapped", 7)][1] == LAPTOP.value


async def test_a_tap_from_the_tenants_own_credential_names_no_browser(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """A supervisor's console holds the tenant's credential and no extension of
    its own. It may answer a parked run -- anyone may -- and the row says no
    browser rather than naming one nobody proved."""
    await _plant(uow, _parked_run("run_parked", 1))

    landed = await client.post("/v1/workflow-runs/run_parked/approve", json={"device_id": "dev-9"})

    assert landed.status_code == 200, landed.text
    assert uow.workflow_runs.approved[("run_parked", 1)][1] is None


async def test_the_row_is_written_before_the_wait_is_released(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The ordering ruling, made observable: a store that cannot record the tap
    releases nothing.

    The rig fires the event first and writes the row after. Written that way, a
    failed write is a live warehouse write with no record of who authorised it
    -- and `routers/runs.py:52-60` already ruled that the audit trail on a
    warehouse write is worth more than that. Written this way the run stays
    parked, times out and aborts, and the operator taps again. A lost tap is
    recoverable; an unauthorised-looking write is not.
    """
    await _plant(uow, _parked_run("run_parked", 1))
    waiting = await _waiting_on(container, "run_parked")
    uow.commit_raises = RuntimeError("the store went away mid-tap")

    with pytest.raises(RuntimeError, match="went away"):
        await client.post("/v1/workflow-runs/run_parked/approve")

    assert await _still_waiting(waiting)
    # And not that the row is gone: `FakeUnitOfWork` does not simulate rollback
    # at all, by its own docstring. That half is the store's and is proved
    # against real Postgres in `test_workflow_runs_against_postgres.py`.


async def test_another_tenants_parked_run_cannot_be_approved_and_is_the_same_404(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """`WorkflowRunRepository.approve` is tenant-blind and the run id is the
    only thing it takes: this lookup is the whole of what keeps one tenant's
    tap off another tenant's run.

    A 403 would confirm the id exists, and run ids are unguessable -- so a run
    of another tenant answers exactly what a run that never existed answers.
    """
    await _plant(uow, _parked_run("run_theirs", 1, tenant=RIVAL), _parked_run("run_mine", 1))
    waiting = await _waiting_on(container, "run_theirs")

    theirs = await client.post("/v1/workflow-runs/run_theirs/approve")
    missing = await client.post("/v1/workflow-runs/run_nope/approve")

    assert theirs.status_code == 404 and missing.status_code == 404
    assert theirs.json()["detail"] == missing.json()["detail"]
    assert await _still_waiting(waiting)
    assert uow.workflow_runs.approved == {}
    assert (await client.post("/v1/workflow-runs/run_mine/approve")).status_code == 200


async def test_a_bare_post_is_a_tap(client: httpx.AsyncClient, uow: FakeUnitOfWork) -> None:
    """No body at all, and no `Content-Type`. A route that 422s one is a
    Stop-shaped button that sometimes does nothing.

    There is no request model here for the same reason `abort` has none: the
    row already says which browser is driving the run, and the browser that
    tapped is the one that proved itself. A `device_id` in a body would be a
    third answer to a question two things already answer.
    """
    await _plant(uow, _parked_run("run_parked", 1))

    landed = await client.post("/v1/workflow-runs/run_parked/approve", content=b"")

    assert landed.status_code == 200, landed.text


async def test_the_tap_is_refused_with_no_credential(
    container: _FakeContainer, uow: FakeUnitOfWork
) -> None:
    """A door that lets a withheld warehouse write out, registered without
    `ContextDep`, would be a public one."""
    await _plant(uow, _parked_run("run_parked", 1))
    waiting = await _waiting_on(container, "run_parked")
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        landed = await http.post("/v1/workflow-runs/run_parked/approve")

    assert landed.status_code == 401
    assert await _still_waiting(waiting)
    assert uow.workflow_runs.approved == {}


async def test_a_secret_with_no_browser_named_beside_it_is_the_usual_404(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The one place this door differs from the stop button next to it, pinned
    so nobody has to discover it from a support ticket.

    `abort` reads no browser at all, so the `X-Device-Secret` the extension
    sends on every call (`api.js:40`) is ignored there. This door has to know
    which browser is tapping, so it takes `asking_device` -- and half a pair is
    a 404 there, exactly as it is at `/v1/shapes` and `/v1/offers`. **A tap
    from a browser must send `?device_id=` AND the secret.**

    Which is not what `rigApprove` sends today, and the failure it would get is
    not this one. It sends `rigHeaders()` -- "none of the backend's headers",
    so no secret -- and no `?device_id=` either, so it resolves to no browser
    at all and gets a silent 200 with a NULL approver and the 403 skipped. The
    router's module docstring carries that hand-off; this test pins only the
    half-pair rule, which is the shape `api.js:254` would produce if phase 5
    copied it.
    """
    await uow.devices.add(f.device(id=LAPTOP, secret=APPROVER))
    await _plant(uow, _parked_run("run_parked", 1))

    half = await client.post(
        "/v1/workflow-runs/run_parked/approve", headers={"X-Device-Secret": APPROVER}
    )

    assert half.status_code == 404, half.text
    assert uow.workflow_runs.approved == {}
    whole = await client.post(
        "/v1/workflow-runs/run_parked/approve",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": APPROVER},
    )
    assert whole.status_code == 200, whole.text


# What a fresh process does about the runs the last one was driving


async def test_a_process_starting_fails_the_runs_the_last_one_left_running(
    uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """The defect behind an operator watching Approve do nothing.

    `fail_orphans` has said "called once at startup" since it was written, and
    nothing called it. So a run whose task died -- a reload in development, a
    deploy in production -- stayed `running` forever: the console kept it on
    "Needs a person", the extension kept asking after it every heartbeat, and
    an Approve on it wrote a person's name against a write nobody would send.
    """
    await _plant(uow, _parked_run("run_abandoned", 2))

    swept = await on_start(container)

    assert swept == 1
    left = uow.workflow_runs.rows["run_abandoned"]
    assert left.outcome == "failed"
    assert left.steps[-1].reason == "the process driving this run stopped"


async def test_a_process_starting_on_a_clean_store_sweeps_nothing(
    uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    # The ordinary start. A sweep that reported work it did not do would teach
    # everybody to ignore the line it logs.
    assert await on_start(container) == 0
