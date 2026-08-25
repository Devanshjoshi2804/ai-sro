"""Workflows: deterministic plans. No I/O, no clock, no randomness, no LLM.

Everything effectful is an activity call. A workflow that read the database
directly would replay differently after a restart and lose the durability that
is the only reason Temporal is here.
"""

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
    # A malformed pair fails the same way every time; retrying it wastes the
    # supervisor's attention rather than fixing anything.
    non_retryable_error_types=["InductionFailed"],
)


@workflow.defn
class InductionWorkflow:
    """Two sealed recordings to a skill version.

    Durable so a failed induction never costs the demonstrations: the recordings
    are already sealed, and a retry starts from them rather than from a session.
    """

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
    """Watches one demonstration and reaps it if the operator walks away.

    The capture session itself lives in the API process, attached to CDP. What
    is durable here is the deadline: a browser session left open costs money and
    holds a scarce slot.
    """

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


# A read that failed to connect is worth another attempt. A write is not: the
# first attempt may have arrived, and the target system has no way to tell us.
_READ_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=3,
    # A skill that may not be run is refused the same way every time.
    non_retryable_error_types=["NotRunnable"],
)
_WRITE_RETRY = RetryPolicy(maximum_attempts=1)


@workflow.defn
class ExecutionWorkflow:
    """Perform a skill, one step per activity.

    The step is the unit of durability because it is the unit of damage. If this
    process dies after step 7, the workflow resumes at step 8 -- and because the
    run already records step 7, an activity asked to repeat it returns what
    happened rather than doing it again.
    """

    @workflow.run
    async def run(self, request: StartRunRequest) -> str:
        """Returns the run id. What happened is on the run itself, which is the
        record everything else reads."""
        started: StartedRun = await workflow.execute_activity(
            "start_run",
            request,
            # Named activities carry no type information, so the converter
            # hands back a dict unless the shape is stated here.
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

        # Positions rather than a count of steps: a skill whose body runs once
        # per thing in a list does not know how long it is until the system
        # answers, so how far to go is asked of each step rather than decided
        # here. Determinism is unaffected -- what the activity answered is in
        # the history, and a replay reads the same answers.
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
                # Chosen per step: whether this one writes is known only after
                # the first attempt, so the conservative policy applies to every
                # step and the read-only ones lose a retry they rarely need.
                retry_policy=_WRITE_RETRY,
            )
            if not result.ok:
                # Later steps depend on this one having worked. Continuing would
                # send calls built from values the system never returned.
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
    """One firing of one trigger.

    Thin on purpose: everything it could decide -- whether the trigger is still
    enabled, whether the skill still runs, whose authorisation applies -- is a
    fact about now, and a workflow replays. It asks once and reports what it was
    told.
    """

    @workflow.run
    async def run(self, request: TriggerRequest) -> TriggerResult:
        fired: TriggerResult = await workflow.execute_activity(
            "fire_trigger",
            request,
            start_to_close_timeout=timedelta(minutes=10),
            # Started, not retried. A trigger that fired and whose run went bad
            # has a run to look at; a second firing would be a second set of
            # writes against the same records, minutes apart, with nobody there.
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
        return fired
