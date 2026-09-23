from __future__ import annotations

from collections.abc import Mapping

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run, RunId


class NotYours(Exception):
    code = "not_yours"


class ReviseRun:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self, ctx: RequestContext, *, run_id: RunId, values: Mapping[str, str]
    ) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            if run.requested_by != ctx.principal_id:
                raise NotYours("only the person this run is being performed for can change it")
            run.revise(values, at=self._clock.now())
            await uow.runs.save(run)
            await uow.commit()
        return run
