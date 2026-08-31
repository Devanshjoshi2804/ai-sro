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
from sro.domain.execution.verdict import judge
from sro.domain.skill.promotion import PromotionStage


class NotYours(Exception):
    """This is not a run this caller may pass judgement on."""


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
                raise NotYours("this run is still going; stopping it is a different thing")

            run.called_wrong(because)
            await uow.runs.save(run)

            # Reaches the track record exactly the way `FinishRun` does: get the
            # version this run was performed at, re-judge it now that
            # `wrong_because` is set, and let the ladder climb or fall on its
            # own. A second, differently-shaped call site here would let this
            # verdict reach the skill by a different door than every other one.
            now = self._clock.now()
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            version = skill.version(run.skill_version)
            verdict = judge(run)
            version.record_run(verdict, now)
            version.earn(verdict, now)
            if version.track_record.should_demote and version.stage.rung > (
                PromotionStage.SHADOW.rung
            ):
                version.demote(
                    PromotionStage.SHADOW,
                    now,
                    f"{version.track_record.consecutive_failures} runs failed in a row",
                )
            await uow.skills.save(skill)
            await uow.commit()
        return run
