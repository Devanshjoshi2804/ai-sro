from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from sro.application.runtime.run_steps import Prepared, StepOutcome
    from sro.domain.execution.progress import K_STEP_HEARTBEAT_S, K_STEP_LIMIT_S
    from sro.infrastructure.temporal.activities import (
        RunRef,
        StartedRun,
        StartRunRequest,
        StepRequest,
        StepResult,
        TriggerRequest,
        TriggerResult,
    )


_READ_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=3,
    non_retryable_error_types=["NotRunnable"],
)
_WRITE_RETRY = RetryPolicy(maximum_attempts=1)
_NEVER_AGAIN = ["NeedsAPerson", "WaitingForAPerson", "Stopped"]
_STEP_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=0,
    non_retryable_error_types=_NEVER_AGAIN,
)
_QUEUE_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=0,
    non_retryable_error_types=_NEVER_AGAIN,
)
_SHORT = timedelta(seconds=60)


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


@workflow.defn
class RunWorkflow:
    @workflow.run
    async def run(self, ref: RunRef) -> str:
        try:
            prepared: Prepared = await workflow.execute_activity(
                "run.prepare",
                ref,
                result_type=Prepared,
                start_to_close_timeout=_SHORT,
                retry_policy=_READ_RETRY,
            )
            if prepared.browser:
                await workflow.execute_activity(
                    "run.acquire",
                    ref,
                    start_to_close_timeout=timedelta(seconds=K_STEP_LIMIT_S),
                    retry_policy=_QUEUE_RETRY,
                )
            while True:
                outcome = await self._step(ref)
                if outcome.asking or not outcome.more:
                    break
        finally:
            try:
                await workflow.execute_activity(
                    "run.finish", ref, start_to_close_timeout=_SHORT, retry_policy=_READ_RETRY
                )
            finally:
                await workflow.execute_activity(
                    "run.release", ref, start_to_close_timeout=_SHORT, retry_policy=_READ_RETRY
                )
        return ref.run_id

    async def _step(self, ref: RunRef) -> StepOutcome:
        outcome: StepOutcome = await workflow.execute_activity(
            "run.step",
            ref,
            result_type=StepOutcome,
            start_to_close_timeout=timedelta(seconds=K_STEP_LIMIT_S),
            heartbeat_timeout=timedelta(seconds=K_STEP_HEARTBEAT_S),
            retry_policy=_STEP_RETRY,
            cancellation_type=workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )
        return outcome
