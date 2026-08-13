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
