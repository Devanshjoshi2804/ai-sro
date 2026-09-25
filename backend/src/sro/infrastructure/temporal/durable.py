from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from datetime import timedelta

from temporalio.client import Client, WorkflowFailureError
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import NotRunnable
from sro.domain.execution.progress import K_BUDGET_MARGIN_S
from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import SkillId
from sro.infrastructure.temporal.activities import RunRef, StartRunRequest
from sro.infrastructure.temporal.queues import DEFAULT_QUEUE, RUNS_QUEUE
from sro.infrastructure.temporal.workflows import ExecutionWorkflow, RunWorkflow

logger = logging.getLogger(__name__)


class TemporalDurableExecution:
    def __init__(
        self,
        *,
        address: str,
        namespace: str = "default",
        default_queue: str = DEFAULT_QUEUE,
    ) -> None:
        self._address = address
        self._namespace = namespace
        self._default_queue = default_queue
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    async def _connect(self) -> Client:
        async with self._lock:
            if self._client is None:
                self._client = await Client.connect(self._address, namespace=self._namespace)
            return self._client

    async def execute_skill(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        version: int | None = None,
        authorized_by: str | None = None,
        medium: str = "network",
        run_id: RunId | None = None,
        wait: bool = True,
    ) -> RunId:
        client = await self._connect()
        request = StartRunRequest(
            tenant_id=ctx.tenant_id.value,
            principal_id=ctx.principal_id.value,
            skill_id=skill_id.value,
            parameters=dict(parameters),
            version=version,
            authorized_by=authorized_by,
            medium=medium,
            run_id=run_id.value if run_id else "",
        )
        handle = await client.start_workflow(
            ExecutionWorkflow.run,
            request,
            id=f"run-{skill_id}-{uuid.uuid4().hex[:8]}",
            task_queue=self._default_queue,
        )
        if not wait and run_id is not None:
            return run_id

        try:
            finished: str = await handle.result()
        except WorkflowFailureError as exc:
            raise NotRunnable(_root_message(exc)) from exc
        return RunId(finished)

    async def start_run(self, ctx: RequestContext, *, run_id: str, budget_s: float) -> None:
        client = await self._connect()
        with contextlib.suppress(WorkflowAlreadyStartedError):
            await client.start_workflow(
                RunWorkflow.run,
                RunRef(
                    tenant_id=ctx.tenant_id.value,
                    principal_id=ctx.principal_id.value,
                    run_id=run_id,
                    budget_s=budget_s,
                ),
                id=f"workflow-run-{run_id}",
                task_queue=RUNS_QUEUE,
                execution_timeout=timedelta(seconds=budget_s + K_BUDGET_MARGIN_S),
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )

    async def answer_run(self, run_id: str, question_id: str) -> None:
        handle = (await self._connect()).get_workflow_handle(f"workflow-run-{run_id}")
        await handle.signal(RunWorkflow.answer, question_id)


def _root_message(error: BaseException) -> str:
    current: BaseException = error
    while current.__cause__ is not None:
        current = current.__cause__
    message = getattr(current, "message", None)
    return str(message or current) or str(error)
