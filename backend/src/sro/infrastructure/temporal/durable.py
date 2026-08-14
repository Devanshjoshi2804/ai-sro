"""Temporal behind the ``DurableExecution`` port.

The client connects lazily and is cached: building the container is synchronous,
and a Temporal outage at boot must not stop the API from serving reads.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta

from temporalio.client import Client, WorkflowFailureError
from temporalio.service import RPCError

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import NotRunnable
from sro.application.induction.errors import InductionFailed
from sro.application.induction.induce_skill import InducedSkill
from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import BrowserSessionId, RecordingId, SkillId
from sro.infrastructure.temporal.activities import (
    InductionRequest,
    ReapRequest,
    StartRunRequest,
)
from sro.infrastructure.temporal.queues import BROWSER_QUEUE, DEFAULT_QUEUE
from sro.infrastructure.temporal.workflows import (
    ExecutionWorkflow,
    InductionWorkflow,
    RecordingSessionWorkflow,
)

logger = logging.getLogger(__name__)


class TemporalDurableExecution:
    def __init__(
        self,
        *,
        address: str,
        namespace: str = "default",
        default_queue: str = DEFAULT_QUEUE,
        browser_queue: str = BROWSER_QUEUE,
    ) -> None:
        # Queues are overridable so a test can have its own. Two workers on one
        # queue must be looking at the same data; a worker pointed at another
        # database will happily accept the work and fail to find the recording.
        self._address = address
        self._namespace = namespace
        self._default_queue = default_queue
        self._browser_queue = browser_queue
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    async def _connect(self) -> Client:
        async with self._lock:
            if self._client is None:
                self._client = await Client.connect(self._address, namespace=self._namespace)
            return self._client

    async def induce_skill(
        self,
        ctx: RequestContext,
        *,
        first: RecordingId,
        second: RecordingId,
        name: str | None = None,
    ) -> InducedSkill:
        client = await self._connect()
        request = InductionRequest(
            tenant_id=ctx.tenant_id.value,
            principal_id=ctx.principal_id.value,
            first_recording_id=first.value,
            second_recording_id=second.value,
            name=name,
        )

        try:
            result = await client.execute_workflow(
                InductionWorkflow.run,
                request,
                # Unique per attempt: re-inducing the same pair is a legitimate
                # request that produces a new version, not a duplicate to fold
                # into the previous run's history.
                id=f"induct-{first}-{second}-{uuid.uuid4().hex[:8]}",
                task_queue=self._default_queue,
            )
        except WorkflowFailureError as exc:
            # The workflow marks a bad pair non-retryable. Unwrap it so the
            # caller sees why induction was refused rather than the scheduler's
            # own wrapper, which says only "Activity task failed".
            raise InductionFailed(_root_message(exc)) from exc

        return InducedSkill(
            skill_id=SkillId(result.skill_id),
            version=result.version,
            step_count=result.step_count,
            input_parameter_count=result.input_parameter_count,
            derived_parameter_count=result.derived_parameter_count,
        )

    async def execute_skill(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        version: int | None = None,
        authorized_by: str | None = None,
        medium: str = "network",
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
        )
        handle = await client.start_workflow(
            ExecutionWorkflow.run,
            request,
            # Unique per attempt: running the same skill again with the same
            # parameters is a second, deliberate act -- not a duplicate to be
            # folded into the first run's history.
            id=f"run-{skill_id}-{uuid.uuid4().hex[:8]}",
            task_queue=self._default_queue,
        )
        try:
            run_id: str = await handle.result()
        except WorkflowFailureError as exc:
            raise NotRunnable(_root_message(exc)) from exc
        return RunId(run_id)

    async def watch_recording(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        browser_session_id: BrowserSessionId,
        timeout_seconds: int,
    ) -> bool:
        request = ReapRequest(
            tenant_id=ctx.tenant_id.value,
            recording_id=recording_id.value,
            browser_session_id=browser_session_id.value,
        )
        try:
            client = await self._connect()
            await client.start_workflow(
                RecordingSessionWorkflow.run,
                args=[request, timeout_seconds],
                id=_watch_id(recording_id),
                task_queue=self._browser_queue,
                execution_timeout=timedelta(seconds=timeout_seconds * 2),
            )
        except Exception:
            # Deliberately broad: the demonstration is already durable, and no
            # scheduler problem is worth refusing to record a human's work.
            logger.exception("could not start the session deadline for %s", recording_id)
            return False
        return True

    async def recording_finished(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        try:
            client = await self._connect()
            handle = client.get_workflow_handle(_watch_id(recording_id))
            await handle.signal(RecordingSessionWorkflow.finished)
        except RPCError:
            # No deadline was running -- it was never started, or it already
            # fired. Either way there is nothing to cancel.
            logger.debug("no session deadline to signal for %s", recording_id)
        except Exception:
            logger.exception("could not signal the session deadline for %s", recording_id)


def _root_message(error: BaseException) -> str:
    """The deepest message in a Temporal failure chain.

    Temporal wraps a failure once per layer it crossed, and every wrapper reads
    "Activity task failed". The message worth showing a supervisor is at the
    bottom: the reason the pair could not be induced.
    """
    current: BaseException = error
    while current.__cause__ is not None:
        current = current.__cause__
    # ApplicationError carries the original message without the class name
    # str() would prepend; the supervisor reads this, not a Python type.
    message = getattr(current, "message", None)
    return str(message or current) or str(error)


def _watch_id(recording_id: RecordingId) -> str:
    """One deadline per recording, addressable without storing a handle."""
    return f"recording-{recording_id}"
