from __future__ import annotations

import asyncio
import logging
import uuid

from temporalio.client import Client, WorkflowFailureError

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import NotRunnable
from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import SkillId
from sro.infrastructure.temporal.activities import StartRunRequest
from sro.infrastructure.temporal.queues import DEFAULT_QUEUE
from sro.infrastructure.temporal.workflows import ExecutionWorkflow

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


def _root_message(error: BaseException) -> str:
    current: BaseException = error
    while current.__cause__ is not None:
        current = current.__cause__
    message = getattr(current, "message", None)
    return str(message or current) or str(error)
