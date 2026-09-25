"""`RunWorkflow` against the real Temporal server from `make up`
(`localhost:7233`), its activities stubbed by name on a task queue of its own.
Skipped when Temporal does not answer."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import timedelta
from typing import Any

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowExecutionStatus, WorkflowFailureError
from temporalio.worker import Worker

from sro.application.context import RequestContext
from sro.application.ports.locks import AccountBusy
from sro.application.runtime.run_steps import Prepared, StepOutcome
from sro.application.runtime.step import NeedsAPerson
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.infrastructure.temporal.activities import RunAnswer, RunRef
from sro.infrastructure.temporal.durable import TemporalDurableExecution
from sro.infrastructure.temporal.worker import until_signalled
from sro.infrastructure.temporal.workflows import RunWorkflow

ADDRESS = "localhost:7233"
REF = RunRef(tenant_id="acme", principal_id="clerk", run_id="run_wf", budget_s=600.0)


@pytest.fixture
async def client() -> Client:
    try:
        async with asyncio.timeout(5):
            return await Client.connect(ADDRESS)
    except Exception as exc:
        pytest.skip(f"Temporal is not reachable at {ADDRESS}: {exc}")


class Stubs:
    """The six activities by their contract names. `step` answers the next
    of `outcomes` (or runs it, when it is a callable) and every call is kept
    in `called` in the order it happened. An answer stops `prepare` asking,
    as the real one stops once the question it raised is answered."""

    def __init__(
        self,
        *outcomes: StepOutcome | Callable[[], Any],
        prepared: Prepared = Prepared(browser=True),
        acquire: Callable[[], Any] | None = None,
    ) -> None:
        self.outcomes = list(outcomes)
        self.called: list[str] = []
        self.prepared = prepared
        self.acquiring = acquire

    @activity.defn(name="run.prepare")
    async def prepare(self, ref: RunRef) -> Prepared:
        self.called.append("prepare")
        return self.prepared

    @activity.defn(name="run.acquire")
    async def acquire(self, ref: RunRef) -> str:
        self.called.append("acquire")
        if self.acquiring is None:
            return ""
        asked: str = await self.acquiring()
        return asked

    @activity.defn(name="run.step")
    async def step(self, ref: RunRef) -> StepOutcome:
        self.called.append("step")
        next_one = self.outcomes.pop(0)
        if isinstance(next_one, StepOutcome):
            return next_one
        answer: StepOutcome = await next_one()
        return answer

    @activity.defn(name="run.answered")
    async def answered(self, answer: RunAnswer) -> None:
        self.called.append(f"answered {answer.question_id}")
        self.prepared = Prepared(browser=self.prepared.browser)

    @activity.defn(name="run.finish")
    async def finish(self, ref: RunRef) -> str:
        self.called.append("finish")
        return "held"

    @activity.defn(name="run.release")
    async def release(self, ref: RunRef) -> None:
        self.called.append("release")


@contextlib.asynccontextmanager
async def _worker(client: Client, stubs: Stubs) -> AsyncIterator[str]:
    queue = f"runs-test-{uuid.uuid4().hex}"
    async with Worker(
        client,
        task_queue=queue,
        workflows=[RunWorkflow],
        activities=[
            stubs.prepare,
            stubs.acquire,
            stubs.step,
            stubs.answered,
            stubs.finish,
            stubs.release,
        ],
    ):
        yield queue


async def _run(client: Client, stubs: Stubs) -> str:
    async with _worker(client, stubs) as queue:
        result: str = await client.execute_workflow(
            RunWorkflow.run, REF, id=f"workflow-run-{uuid.uuid4().hex}", task_queue=queue
        )
    return result


async def test_the_step_activity_loops_until_nothing_is_left_then_finishes_and_releases(
    client: Client,
) -> None:
    stubs = Stubs(StepOutcome(more=True), StepOutcome(more=True), StepOutcome(more=False))

    assert await _run(client, stubs) == REF.run_id

    assert stubs.called == ["prepare", "acquire", "step", "step", "step", "finish", "release"]


async def _answered(client: Client, stubs: Stubs, question_id: str) -> None:
    async with _worker(client, stubs) as queue:
        handle = await client.start_workflow(
            RunWorkflow.run, REF, id=f"workflow-run-{uuid.uuid4().hex}", task_queue=queue
        )
        await handle.signal(RunWorkflow.answer, question_id)
        await handle.result()


async def test_a_step_that_asks_lets_go_waits_for_the_answer_and_carries_on(
    client: Client,
) -> None:
    stubs = Stubs(StepOutcome(more=True, asking="q-1"), StepOutcome(more=False))

    await _answered(client, stubs, "q-1")

    assert stubs.called == [
        "prepare",
        "acquire",
        "step",
        "release",
        "answered q-1",
        "prepare",
        "acquire",
        "step",
        "finish",
        "release",
    ]


async def test_a_question_nobody_answers_before_the_budget_ends_still_finishes_and_releases(
    client: Client,
) -> None:
    stubs = Stubs(StepOutcome(more=True, asking="q-1"))
    short = RunRef(tenant_id="acme", principal_id="clerk", run_id="run_short", budget_s=2.0)

    async with _worker(client, stubs) as queue:
        await client.execute_workflow(
            RunWorkflow.run, short, id=f"workflow-run-{uuid.uuid4().hex}", task_queue=queue
        )

    assert stubs.called == ["prepare", "acquire", "step", "release", "finish", "release"]


async def test_a_step_that_needs_a_person_is_not_retried(client: Client) -> None:
    async def asks() -> StepOutcome:
        raise NeedsAPerson("who signs in?", kind="password")

    stubs = Stubs(asks, StepOutcome(more=False))

    with pytest.raises(WorkflowFailureError):
        await _run(client, stubs)

    assert stubs.called == ["prepare", "acquire", "step", "finish", "release"]


async def test_a_busy_account_is_retried(client: Client) -> None:
    async def busy() -> StepOutcome:
        raise AccountBusy("another run's sign-in is waiting for a person")

    stubs = Stubs(busy, StepOutcome(more=False))

    await _run(client, stubs)

    assert stubs.called == ["prepare", "acquire", "step", "step", "finish", "release"]


async def test_a_cancelled_run_waits_for_its_step_then_finishes_and_releases(
    client: Client,
) -> None:
    started, wound_down = asyncio.Event(), asyncio.Event()

    async def until_cancelled() -> StepOutcome:
        started.set()
        try:
            while True:
                activity.heartbeat()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            wound_down.set()
            raise

    stubs = Stubs(until_cancelled)
    async with _worker(client, stubs) as queue:
        handle = await client.start_workflow(
            RunWorkflow.run, REF, id=f"workflow-run-{uuid.uuid4().hex}", task_queue=queue
        )
        await started.wait()
        await handle.cancel()
        with pytest.raises(WorkflowFailureError):
            await handle.result()

    assert wound_down.is_set()
    assert stubs.called == ["prepare", "acquire", "step", "finish", "release"]


async def _until_cancelled() -> StepOutcome:
    while True:
        activity.heartbeat()
        await asyncio.sleep(0.1)


async def test_a_run_past_its_budget_still_finishes_and_releases(client: Client) -> None:
    stubs = Stubs(_until_cancelled)
    short = RunRef(tenant_id="acme", principal_id="clerk", run_id="run_short", budget_s=2.0)

    async with _worker(client, stubs) as queue:
        with pytest.raises(WorkflowFailureError):
            await client.execute_workflow(
                RunWorkflow.run, short, id=f"workflow-run-{uuid.uuid4().hex}", task_queue=queue
            )

    assert stubs.called == ["prepare", "acquire", "step", "finish", "release"]


async def test_a_question_at_prepare_or_acquire_runs_no_step_until_it_is_answered(
    client: Client,
) -> None:
    asked_early = Stubs(
        StepOutcome(more=False), prepared=Prepared(browser=True, asking="q-prepare")
    )
    await _answered(client, asked_early, "q-prepare")

    questions = ["q-acquire", ""]

    async def asks() -> str:
        return questions.pop(0)

    asked_at_acquire = Stubs(StepOutcome(more=False), acquire=asks)
    await _answered(client, asked_at_acquire, "q-acquire")

    assert asked_early.called == [
        "prepare",
        "release",
        "answered q-prepare",
        "prepare",
        "acquire",
        "step",
        "finish",
        "release",
    ]
    assert asked_at_acquire.called == [
        "prepare",
        "acquire",
        "release",
        "answered q-acquire",
        "prepare",
        "acquire",
        "step",
        "finish",
        "release",
    ]


async def test_a_stop_during_acquire_waits_for_it_before_releasing(client: Client) -> None:
    started = asyncio.Event()

    async def signs_in() -> str:
        started.set()
        try:
            while True:
                activity.heartbeat()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            stubs.called.append("acquired")
            raise

    stubs = Stubs(acquire=signs_in)
    async with _worker(client, stubs) as queue:
        handle = await client.start_workflow(
            RunWorkflow.run, REF, id=f"workflow-run-{uuid.uuid4().hex}", task_queue=queue
        )
        await started.wait()
        await handle.cancel()
        with pytest.raises(WorkflowFailureError):
            await handle.result()

    assert stubs.called == ["prepare", "acquire", "acquired", "finish", "release"]


async def test_a_finished_run_is_never_started_again(client: Client) -> None:
    durable = TemporalDurableExecution(address=ADDRESS)
    ctx = RequestContext(TenantId("acme"), PrincipalId("clerk"))
    run_id = f"run_{uuid.uuid4().hex}"
    await durable.start_run(ctx, run_id=run_id, budget_s=600.0)
    handle = client.get_workflow_handle(f"workflow-run-{run_id}")
    first = (await handle.describe()).run_id
    await handle.terminate("the test is done with it")

    await durable.start_run(ctx, run_id=run_id, budget_s=600.0)

    described = await handle.describe()
    assert described.run_id == first
    assert described.status is WorkflowExecutionStatus.TERMINATED


async def test_a_sigterm_mid_step_lets_the_step_finish_before_the_worker_exits(
    client: Client,
) -> None:
    started = asyncio.Event()
    finished: list[str] = []

    async def finishes_on_shutdown() -> StepOutcome:
        started.set()
        await activity.wait_for_worker_shutdown()
        finished.append("finished, not cancelled")
        return StepOutcome(more=False)

    stubs = Stubs(finishes_on_shutdown)
    queue = f"runs-test-{uuid.uuid4().hex}"
    worker = Worker(
        client,
        task_queue=queue,
        workflows=[RunWorkflow],
        activities=[
            stubs.prepare,
            stubs.acquire,
            stubs.step,
            stubs.answered,
            stubs.finish,
            stubs.release,
        ],
        graceful_shutdown_timeout=timedelta(seconds=30),
        # The workflow is left mid-run when this worker stops; uncached, its
        # instance is closed by the worker instead of by the garbage collector
        # in some later test.
        max_cached_workflows=0,
    )
    serving = asyncio.create_task(until_signalled(worker))
    handle = await client.start_workflow(
        RunWorkflow.run, REF, id=f"workflow-run-{uuid.uuid4().hex}", task_queue=queue
    )
    try:
        await started.wait()

        os.kill(os.getpid(), signal.SIGTERM)
        await serving

        assert finished == ["finished, not cancelled"]
        assert signal.getsignal(signal.SIGTERM) is signal.SIG_DFL
    finally:
        await handle.terminate("the test is done with it")
