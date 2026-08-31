"""The person a run was performed for says its result was wrong.

Not a survey. This is reached by an operator pressing "undo that" or "it's
wrong, I'll fix it", both of which are things they wanted anyway -- which is why
the answer can be trusted. A question they answer to help us is a question they
stop answering.

The skill hears about it the same way it hears about a crash, because the
distinction it cares about is "did this still work", and a run that made the
wrong record did not.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run, RunId, RunStatus
from sro.domain.execution.verdict import apply_verdict, judge
from sro.domain.shared.errors import Conflict


class NotYours(Exception):
    """This caller is not the one person who may pass judgement on this run."""


class StillRunning(Conflict):
    """This run has not finished; there is no result yet for anyone to judge.

    A `Conflict`, not a `NotYours`: the caller is exactly the right person and
    the request is well formed, the run just is not in a state anybody can
    call wrong yet -- 409, the same as `StopRun`'s `CannotStop`, so a console
    reads it as "try again once it's stopped" rather than "not allowed"."""

    code = "still_running"


class CallRunWrong:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, run_id: RunId, because: str) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            if run.requested_by != ctx.principal_id:
                # A run drives one operator's browser and they are the only
                # person who saw what it produced.
                raise NotYours("only the person this ran for can say how it came out")
            if run.status is RunStatus.RUNNING:
                raise StillRunning("this run is still going; stopping it is a different thing")

            # Judged before the record is written, not after: this is the
            # verdict `FinishRun` already counted for this run when it ended,
            # and it is only recoverable while `wrong_because` is still unset
            # -- `judge` reads that field before anything the steps say. Passed
            # to `apply_verdict` below so the operator's answer replaces that
            # entry instead of adding a second one for the same run, which had
            # `total_runs` and `clean_runs` permanently overstating and let
            # `earn` promote on a clean run the operator was in the middle of
            # taking back.
            already = judge(run)
            run.called_wrong(because)
            await uow.runs.save(run)

            # The one place a verdict reaches a skill's track record and
            # stage -- `FinishRun` reaches the same function when a run ends on
            # its own. A skill's rung must not depend on which of them ran.
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            apply_verdict(skill, run, self._clock.now(), revising=already)
            await uow.skills.save(skill)
            await uow.commit()
        return run
