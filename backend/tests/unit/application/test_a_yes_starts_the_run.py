"""A yes starts the run on the backend, whichever door it came through (S2).

Measured on QA 2026-09-28, thread thr_fa6507fa: the operator typed "yes" in the
console, the thread said "Running Create a Customer Type now.", and nothing ran
-- only the extension started runs on that decision, and the console has no
extension. Every test here goes converse -> the start use case -> the run row.
"""

from __future__ import annotations

import pytest

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.converse import K_CLOSED, K_NOT_YOURS, Converse, StartThread
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.chat.asking import Pending, offered_job
from sro.domain.chat.thread import Message, ThreadId
from sro.domain.shared.identifiers import PrincipalId
from tests import factories as f
from tests.unit.application.rig.test_start_workflow_run import _starter
from tests.unit.application.test_converse import _PlacesTheJob, _understood
from tests.unit.fakes import (
    FakeClock,
    FakeDurableExecution,
    FakeEmbedder,
    FakeIdFactory,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import save_job

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
COLLEAGUE = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("colleague@acme.test"))
JOB = "wfl_1"


class _World:
    def __init__(self, *, steel: bool = True, cap_usd: float = 5.0) -> None:
        self.uow = FakeUnitOfWork()
        self.durable = FakeDurableExecution()
        self.start: StartWorkflowRun = _starter(
            self.uow,
            durable=self.durable,
            steel_tenants=frozenset({f.TENANT.value}) if steel else frozenset(),
            cap_usd=cap_usd,
        )
        self.title = ""

    async def ready(self) -> _World:
        self.title = (await save_job(self.uow, JOB)).title
        return self

    def converse(self) -> Converse:
        uow = self.uow
        return Converse(
            uow,
            ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder()))),
            FakeClock(),
            FakeIdFactory(),
            reads_jobs=_PlacesTheJob(_understood(JOB, values={"Customer Type": "GT2"})),
            start=self.start,
        )

    async def offered(self, converse: Converse) -> tuple[ThreadId, Message]:
        thread = await StartThread(self.uow, FakeClock(), FakeIdFactory()).execute(CTX)
        said = await converse.execute(CTX, thread_id=thread.id, text="create customer type GT2")
        offer = said.messages[-1]
        assert (offer.decision or {}).get("kind") == "job", offer
        return thread.id, offer

    async def runs(self) -> list[str]:
        return [one.id for one in await self.uow.workflow_runs.for_workflow(f.TENANT, JOB)]


async def test_a_typed_yes_in_the_console_starts_exactly_one_run() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None
    assert run.offer == offer.id.value, "a second start of this offer would not be refused"
    assert run.values == {"Customer Type": "GT2"}
    assert run.executor == "steel" and run.started_by == CTX.principal_id.value
    assert [started for started, _ in world.durable.runs_started] == [run_id]
    last = said.messages[-1]
    assert last.text == f"Running {world.title} now."
    assert last.decision is not None and last.decision["run_id"] == run_id


async def test_the_last_answer_to_a_question_starts_the_run() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread = await StartThread(world.uow, FakeClock(), FakeIdFactory()).execute(CTX)
    await AskAboutTheOffer(world.uow, FakeClock(), FakeIdFactory()).execute(
        CTX, Pending(workflow_id=JOB, title=world.title, values={}, missing=("Customer Type",))
    )

    said = await converse.execute(CTX, thread_id=thread.id, text="GT2")

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None and run.values == {"Customer Type": "GT2"}
    assert said.messages[-1].text == f"Running {world.title} now."
    assert (said.messages[-1].decision or {}).get("run_id") == run_id


async def test_a_second_yes_under_the_same_offer_starts_nothing_more() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)
    await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    again = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)
    typed = await converse.execute(CTX, thread_id=thread_id, text="yes")

    assert again.messages[-1].text == K_CLOSED
    assert len(await world.runs()) == 1
    assert len(world.durable.runs_started) == 1
    assert sum(m.text.startswith("Running ") for m in typed.messages) == 1


@pytest.mark.parametrize(
    ("steel", "cap_usd", "why"),
    [(False, 5.0, "needs a connected browser"), (True, 0.0, "daily cap reached")],
    ids=["no-browser", "over-cap"],
)
async def test_a_refused_start_says_why_and_never_that_it_is_running(
    steel: bool, cap_usd: float, why: str
) -> None:
    world = await _World(steel=steel, cap_usd=cap_usd).ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    assert await world.runs() == []
    assert world.durable.runs_started == []
    assert not any(m.text.startswith("Running ") for m in said.messages), said.messages[-1]
    last = said.messages[-1]
    assert last.text.startswith("Nothing was started: ") and why in last.text, last.text
    assert "run_id" not in (last.decision or {})
    assert offered_job(said.messages) is not None, "the offer is gone; a yes cannot retry it"


async def test_an_offer_that_already_started_a_run_is_said_and_not_started_again() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)
    await world.start.execute(
        CTX,
        workflow_id=JOB,
        device_id=None,
        values={"Customer Type": "GT2"},
        live=True,
        allow_focus=False,
        offer=offer.id.value,
    )

    said = await converse.execute(CTX, thread_id=thread_id, text="yes", answering=offer.id.value)

    assert len(await world.runs()) == 1
    assert said.messages[-1].text.startswith("Nothing was started: ")
    assert "already started a run" in said.messages[-1].text
    assert not any(m.text.startswith("Running ") for m in said.messages)


async def test_a_colleague_s_yes_in_the_opener_s_thread_starts_no_run() -> None:
    world = await _World().ready()
    converse = world.converse()
    thread_id, offer = await world.offered(converse)

    said = await converse.execute(
        COLLEAGUE, thread_id=thread_id, text="yes", answering=offer.id.value
    )

    assert said.messages[-1].text == K_NOT_YOURS
    assert await world.runs() == []
    assert offered_job(said.messages) is not None
