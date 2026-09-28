"""A press in the panel starts its run on the backend, on Steel, once (E2).

On QA (2026-09-28) one "yes" made three runs: the chat's yes and the panel's own
card each started one, under different names for one offer. The panel's cards
are back, so every press goes through `POST /v1/workflow-runs` and says which
offer it answers; the store holds one run per offer, and a second start of the
same offer -- a second panel, the chat's yes, a double press -- is answered
with the run the first one made. And a Steel tenant's press runs on Steel even
though the browser says who it is: the device only records who pressed.

Every test here goes through the real route and the real use case, over the
in-memory store, whose offer rule is the index's (`uq_workflow_runs_one_per_offer`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from httpx import ASGITransport

from sro.application.context import RequestContext
from sro.domain.execution.account import Account, Lease, LeaseState
from sro.domain.execution.progress import Progress
from sro.domain.skill.workflow import MAIN, Workflow
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for
from tests.unit.interface.test_workflow_runs_route import (
    LAPTOP,
    TENANT,
    _Attached,
    _body,
    _gesture,
    _Spawned,
    _workflow,
)


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def spawned(uow: FakeUnitOfWork) -> _Spawned:
    return _Spawned(uow)


@pytest.fixture
def container(uow: FakeUnitOfWork, spawned: _Spawned) -> _FakeContainer:
    built = _FakeContainer(uow)
    built.settings = built.settings.model_copy(update={"steel_tenants": (TENANT.value,)})
    built.asker = FakeAsker()
    built.pursuits = spawned
    # Connected, so a press that fell back to the extension executor would
    # find its browser and pass -- the executor is what these tests read.
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


@pytest.fixture
async def held(uow: FakeUnitOfWork) -> Workflow:
    workflow = _workflow()
    await uow.workflows.save(workflow)
    await uow.gestures.add_gestures(
        tuple(_gesture(cited) for step in workflow.steps for cited in step.cites)
    )
    return workflow


async def test_a_steel_tenant_s_press_from_a_browser_runs_on_steel(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow, spawned: _Spawned
) -> None:
    made = await client.post("/v1/workflow-runs", json=_body())

    assert made.status_code == 201, made.text
    run = uow.workflow_runs.rows[made.json()["id"]]
    assert run.executor == "steel", "the browser's name forced the extension executor"
    assert run.device_id == ""
    ((what, args),) = spawned.calls
    assert what == "StartWorkflowRun.perform" and args["run"].executor == "steel"


async def test_two_presses_of_one_offer_answer_one_run(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow, spawned: _Spawned
) -> None:
    first = await client.post("/v1/workflow-runs", json=_body(offer="n_1_wfl_1"))
    second = await client.post("/v1/workflow-runs", json=_body(offer="n_1_wfl_1"))

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["id"] == first.json()["id"]
    assert len(uow.workflow_runs.rows) == 1
    assert spawned.handed_over == 1, "the second press started the run a second time"


async def test_a_press_after_the_chat_s_yes_answers_the_run_the_yes_started(
    client: httpx.AsyncClient, container: _FakeContainer, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """The chat's yes starts through the same use case under the offer the
    thread's decision names; the card for that reply carries that name."""
    ctx = RequestContext(tenant_id=TENANT, principal_id=f.OPERATOR)
    by_the_yes = await container.start_workflow_run().execute(
        ctx,
        workflow_id="wfl_1",
        device_id=None,
        values={"clientCode": "NEWTESTS"},
        live=True,
        allow_focus=True,
        offer="msg_question",
    )

    pressed = await client.post("/v1/workflow-runs", json=_body(offer="msg_question"))

    assert pressed.status_code == 200, pressed.text
    assert pressed.json()["id"] == by_the_yes.id
    assert len(uow.workflow_runs.rows) == 1


async def test_presses_that_name_no_offer_are_not_one_offer(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """The rule is per offer, never per job: two presses with no offer make two
    runs, so a missing name cannot fold unrelated work together."""
    await client.post("/v1/workflow-runs", json=_body())
    await client.post("/v1/workflow-runs", json=_body())

    assert len(uow.workflow_runs.rows) == 2


async def test_a_steel_run_under_way_says_where_to_watch_it(
    client: httpx.AsyncClient, container: _FakeContainer, uow: FakeUnitOfWork, held: Workflow
) -> None:
    made = (await client.post("/v1/workflow-runs", json=_body())).json()
    lease = Lease(
        id="lse_1",
        account=Account.of(TENANT.value, "https://wms.acme.test", "clerk"),
        container_url="http://steel.local",
        steel_session_id="sess-1",
        context_id="ctx-1",
        holder=made["id"],
        heartbeat_at=datetime(2026, 1, 1, tzinfo=UTC),
        expires_at=datetime(2999, 1, 1, tzinfo=UTC),
        state=LeaseState.READY,
    )
    await uow.browser_sessions.lease(TENANT, lease)
    await uow.workflow_runs.record_progress(
        TENANT, made["id"], Progress(lease="lse_1", tabs={MAIN: "tab-9"}).as_json()
    )
    container.pool.viewers["http://steel.local"] = "https://steel.example/v1/sessions/debug"

    read = (await client.get(f"/v1/workflow-runs/{made['id']}")).json()

    assert read["live_view_url"] == (
        "https://steel.example/v1/sessions/debug?pageId=tab-9&interactive=false"
    )


async def test_a_run_with_no_live_browser_has_nothing_to_watch(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    made = (await client.post("/v1/workflow-runs", json=_body())).json()

    read = (await client.get(f"/v1/workflow-runs/{made['id']}")).json()

    assert read["live_view_url"] is None
