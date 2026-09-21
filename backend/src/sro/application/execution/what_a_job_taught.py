"""What a job has changed its mind about, for somebody to read.

A job rewrites its own behaviour. A locator the recorded one could not find is
replaced by the one a run did; a box's limit is written down the first time a
value would not fit. Every one of those is stored as the CURRENT answer -- one
row per step, the last winning -- which is exactly right for the question a run
asks and leaves a job drifting with nothing anybody can read.

**Not an approval gate**, deliberately. What a run found is already what the
next run will try, and holding that behind a person would mean a job that
healed itself on Friday waits until Monday to say so. This is the reviewable
half: somebody can ask why a step is looking for a css path and get an answer
with a run id in it.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.learned_step import Taught


class ReadWhatAJobTaught:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, workflow_id: str) -> tuple[Taught, ...]:
        """Newest first, and bounded. A history nobody can read in one page is
        a log, and the console is where a log is read."""
        async with self._uow as uow:
            # The workflow first, so an unknown one is a 404 rather than an
            # empty history that reads as "this job has never learned
            # anything" -- which is a different and much more reassuring thing
            # to be told about a job that does not exist.
            await uow.workflows.get(ctx.tenant_id, workflow_id)
            return await uow.workflows.taught_itself(workflow_id)


__all__ = ["ReadWhatAJobTaught"]
