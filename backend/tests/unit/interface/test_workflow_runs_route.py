"""`POST /v1/workflow-runs` -- the door that starts a run in a live warehouse.

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
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Coroutine
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from sro.application.execution.pursuits import Pursuits
from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.app import create_app
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
    """The container's pursuits, recording what was handed over instead of
    running it -- and what the store had committed at the moment it was."""

    def __init__(self, uow: FakeUnitOfWork) -> None:
        super().__init__()
        self._uow = uow
        self.handed_over = 0
        self.commits_when_handed_over: list[int] = []

    def spawn(self, coroutine: Coroutine[object, object, None]) -> None:
        self.handed_over += 1
        self.commits_when_handed_over.append(self._uow.commits)
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


def _workflow(workflow_id: str = "wfl_1", *, steps: int = 5, tenant: TenantId = TENANT) -> Workflow:
    return Workflow(
        id=workflow_id,
        tenant=tenant.value,
        title="create a work area",
        narrative="the operator created a work area",
        steps=[Step(order=n, says=f"step {n}", system=None) for n in range(steps)],
        parameters=[{"name": "clientCode", "seen_values": ["NEWTESTS"]}],
    )


@pytest.fixture
async def held(uow: FakeUnitOfWork) -> Workflow:
    workflow = _workflow()
    await uow.workflows.save(workflow)
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
    landed = await client.post("/v1/workflow-runs", json=_body(workflow_id="wfl_nope"))

    assert landed.status_code == 404
    assert spawned.handed_over == 0


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
