from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run, RunId, RunStatus
from sro.domain.execution.verdict import apply_verdict, judge
from sro.domain.shared.errors import Conflict


class NotYours(Exception):
    code = "not_yours"


class StillRunning(Conflict):
    code = "still_running"


class CallRunWrong:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, run_id: RunId, because: str) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            if run.requested_by != ctx.principal_id:
                raise NotYours("only the person this ran for can say how it came out")
            if run.status is RunStatus.RUNNING:
                raise StillRunning("this run is still going; stopping it is a different thing")

            already = judge(run)
            run.called_wrong(because)
            await uow.runs.save(run)

            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            apply_verdict(skill, run, self._clock.now(), revising=already)
            await uow.skills.save(skill)
            await uow.commit()
        return run
