from __future__ import annotations

from datetime import datetime, timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from sro.application.runtime.run_steps import Prepared, StepOutcome
    from sro.domain.execution.progress import K_STEP_HEARTBEAT_S, K_STEP_LIMIT_S
    from sro.infrastructure.temporal.activities import (
        RunAnswer,
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
_PREPARE_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=3,
    non_retryable_error_types=_NEVER_AGAIN,
)
_SHORT = timedelta(seconds=60)
_AT_LEAST = timedelta(seconds=1)


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
    def __init__(self) -> None:
        self._answers: dict[str, tuple[str, str]] = {}

    @workflow.run
    async def run(self, ref: RunRef) -> str:
        deadline = workflow.info().start_time + timedelta(seconds=ref.budget_s)
        try:
            while True:
                prepared: Prepared = await workflow.execute_activity(
                    "run.prepare",
                    ref,
                    result_type=Prepared,
                    start_to_close_timeout=_SHORT,
                    retry_policy=_PREPARE_RETRY,
                )
                asking = prepared.asking
                if prepared.browser and not asking:
                    asking = await self._driven(ref, "run.acquire", deadline, str, _QUEUE_RETRY)
                while not asking and deadline > workflow.now():
                    outcome = await self._driven(
                        ref, "run.step", deadline, StepOutcome, _STEP_RETRY
                    )
                    if not outcome.more:
                        break
                    asking = outcome.asking
                if not asking or not await self._answered(ref, asking, deadline):
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

    @workflow.signal
    def answer(self, question_id: str, value: str, verdict: str = "") -> None:
        self._answers[question_id] = (value, verdict)

    async def _answered(self, ref: RunRef, asking: str, deadline: datetime) -> bool:
        await workflow.execute_activity(
            "run.release", ref, start_to_close_timeout=_SHORT, retry_policy=_READ_RETRY
        )
        try:
            await workflow.wait_condition(
                lambda: asking in self._answers, timeout=max(deadline - workflow.now(), _AT_LEAST)
            )
        except TimeoutError:
            return False
        await workflow.execute_activity(
            "run.answered",
            RunAnswer(ref.tenant_id, ref.principal_id, ref.run_id, asking, *self._answers[asking]),
            start_to_close_timeout=_SHORT,
            retry_policy=_READ_RETRY,
        )
        return True

    async def _driven[T](
        self,
        ref: RunRef,
        name: str,
        deadline: datetime,
        answer: type[T],
        retry: RetryPolicy,
    ) -> T:
        done: T = await workflow.execute_activity(
            name,
            ref,
            result_type=answer,
            schedule_to_close_timeout=max(deadline - workflow.now(), _AT_LEAST),
            start_to_close_timeout=timedelta(seconds=K_STEP_LIMIT_S),
            heartbeat_timeout=timedelta(seconds=K_STEP_HEARTBEAT_S),
            retry_policy=retry,
            cancellation_type=workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )
        return done
