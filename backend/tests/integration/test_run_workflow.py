"""`RunWorkflow` against the real Temporal server from `make up`
(`localhost:7233`), its activities stubbed by name on a task queue of its own.
Skipped when Temporal does not answer."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError
from temporalio.worker import Worker

from sro.application.ports.locks import AccountBusy
from sro.application.runtime.run_steps import Prepared, StepOutcome
from sro.application.runtime.step import NeedsAPerson
from sro.infrastructure.temporal.activities import RunRef
from sro.infrastructure.temporal.workflows import RunWorkflow

ADDRESS = "localhost:7233"
REF = RunRef(tenant_id="acme", principal_id="clerk", run_id="run_wf")


@pytest.fixture
async def client() -> Client:
    try:
        async with asyncio.timeout(5):
            return await Client.connect(ADDRESS)
    except Exception as exc:
        pytest.skip(f"Temporal is not reachable at {ADDRESS}: {exc}")


class Stubs:
    """The five activities by their contract names. `step` answers the next
    of `outcomes` (or runs it, when it is a callable) and every call is kept
    in `called` in the order it happened."""

    def __init__(self, *outcomes: StepOutcome | Callable[[], Any]) -> None:
        self.outcomes = list(outcomes)
        self.called: list[str] = []

    @activity.defn(name="run.prepare")
    async def prepare(self, ref: RunRef) -> Prepared:
        self.called.append("prepare")
        return Prepared(browser=True)

    @activity.defn(name="run.acquire")
    async def acquire(self, ref: RunRef) -> None:
        self.called.append("acquire")

    @activity.defn(name="run.step")
    async def step(self, ref: RunRef) -> StepOutcome:
        self.called.append("step")
        next_one = self.outcomes.pop(0)
        if isinstance(next_one, StepOutcome):
            return next_one
        answer: StepOutcome = await next_one()
        return answer

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
        activities=[stubs.prepare, stubs.acquire, stubs.step, stubs.finish, stubs.release],
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


async def test_a_step_that_asks_ends_the_loop_and_still_releases(client: Client) -> None:
    stubs = Stubs(StepOutcome(more=True, asking="q-1"))

    await _run(client, stubs)

    assert stubs.called == ["prepare", "acquire", "step", "finish", "release"]


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
