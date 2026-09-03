"""The operator changes a value while the run is still going.

The panel draws a run as it happens, a row per step, and a step that has not
been sent can still be argued with: the address was wrong, or the mail that
started this never said which one. What has already gone to the warehouse has
gone -- steps record what they sent and nothing here rewrites them -- and what
is still to come renders from the new value.

That works because a step is a fresh read: `PerformStep` loads the run before
each one, so a value saved between two steps is the value the second uses. It
is the same property durability rests on, used for a different purpose.

Only the person the run is being performed for. A run drives their browser and
they are the one watching it; `CallRunWrong` refuses on the same grounds, and
for the same reason.
"""

from __future__ import annotations

from collections.abc import Mapping

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run, RunId


class NotYours(Exception):
    """This caller is not the person this run is being performed for."""


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
            # Every refusal below this line is the domain's: a finished run, a
            # name the skill never declared, a change that names nothing. They
            # are invariants of the run rather than rules about the request, so
            # they live where anything else that touches a run will meet them.
            run.revise(values, at=self._clock.now())
            await uow.runs.save(run)
            await uow.commit()
        return run
