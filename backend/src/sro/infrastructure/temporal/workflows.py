from __future__ import annotations

import asyncio
import contextlib
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from sro.infrastructure.temporal.activities import (
        InductionRequest,
        InductionResult,
        ReapRequest,
        StartedRun,
        StartRunRequest,
        StepRequest,
        StepResult,
        TriggerRequest,
        TriggerResult,
    )

_INDUCTION_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_attempts=3,
    non_retryable_error_types=["InductionFailed"],
)


@workflow.defn
class InductionWorkflow:
    @workflow.run
    async def run(self, request: InductionRequest) -> InductionResult:
        result: InductionResult = await workflow.execute_activity(
            "induce_skill",
            request,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_INDUCTION_RETRY,
        )
        return result


@workflow.defn
class RecordingSessionWorkflow:
    def __init__(self) -> None:
        self._finished = False

    @workflow.signal
    def finished(self) -> None:
        self._finished = True

    @workflow.run
    async def run(self, request: ReapRequest, timeout_seconds: int = 3600) -> bool:
        with contextlib.suppress(asyncio.TimeoutError):
            await workflow.wait_condition(
                lambda: self._finished, timeout=timedelta(seconds=timeout_seconds)
            )
        if self._finished:
            return False

        abandoned: bool = await workflow.execute_activity(
            "abandon_stale_recording",
            request,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        await workflow.execute_activity(
            "close_browser_session",
            request.browser_session_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        return abandoned


_READ_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=3,
    non_retryable_error_types=["NotRunnable"],
)
_WRITE_RETRY = RetryPolicy(maximum_attempts=1)


@workflow.defn
class ExecutionWorkflow:
    @workflow.run
    async def run(self, request: StartRunRequest) -> str:
        started: StartedRun = await workflow.execute_activity(
            "start_run",
            request,
            result_type=StartedRun,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_READ_RETRY,
        )
        step = StepRequest(
            tenant_id=request.tenant_id,
            principal_id=request.principal_id,
            run_id=started.run_id,
            index=0,
        )

        index = 0
        while True:
            result: StepResult = await workflow.execute_activity(
                "execute_step",
                StepRequest(
                    tenant_id=request.tenant_id,
                    principal_id=request.principal_id,
                    run_id=started.run_id,
                    index=index,
                ),
                result_type=StepResult,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_WRITE_RETRY,
            )
            if not result.ok:
                break
            if not result.more:
                break
            index += 1

        await workflow.execute_activity(
            "finish_run",
            step,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_READ_RETRY,
        )
        run_id: str = started.run_id
        return run_id


@workflow.defn
class TriggerWorkflow:
    @workflow.run
    async def run(self, request: TriggerRequest) -> TriggerResult:
        fired: TriggerResult = await workflow.execute_activity(
            "fire_trigger",
            request,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        return fired
