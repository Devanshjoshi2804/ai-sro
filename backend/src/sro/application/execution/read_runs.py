"""Read runs, and ask one to stop. The audit trail is only useful if it can be
looked at, and a run in somebody's own browser is only watchable if they can
also interrupt it."""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.stops import Stops
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.run import Run, RunId, RunStatus
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import SkillId


class GetRun:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, run_id: RunId) -> Run:
        async with self._uow as uow:
            return await uow.runs.get(ctx.tenant_id, run_id)


class ListRuns:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Run, ...]:
        async with self._uow as uow:
            return await uow.runs.list_for_tenant(
                ctx.tenant_id, skill_id=skill_id, limit=limit, offset=offset
            )


class CannotStop(Conflict):
    """This run is not one this process can stop.

    A `Conflict` rather than a plain domain error: the request is well formed
    and the run is real, it is just not in a state anybody can stop it from --
    which is 409, and is what tells a console to re-read the run rather than to
    change what it asked for.
    """

    code = "cannot_stop"


NOT_IN_A_BROWSER_HERE = "that run is not being performed in a browser this process is driving"
"""Said by both stop buttons, so it is said once.

`StopRun` below and `AbortWorkflowRun` in `workflow_runs.py` refuse the same
thing for the same reason -- a run nothing in this process is driving cannot be
stopped by this process -- and the two aggregates are the only difference
between them. Two literals is how the console ends up with two sentences for
one refusal, and a person told two different things about the same button reads
it as two different failures."""


class StopRun:
    """Ask a run being performed here to end at its next step.

    Only a run in somebody's own browser: that one is being driven by a task in
    this process, and the intention to stop is held in this process. A durable
    run belongs to the worker and would go on regardless -- answering "stopped"
    for it would be the console reporting something that did not happen, which
    is worse on this screen than not offering the button at all.
    """

    def __init__(self, uow: UnitOfWork, stops: Stops) -> None:
        self._uow = uow
        self._stops = stops

    async def execute(self, ctx: RequestContext, *, run_id: RunId) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
        if run.status is not RunStatus.RUNNING:
            raise CannotStop(f"that run already {run.status.value}")
        if run.device_id is None:
            raise CannotStop(NOT_IN_A_BROWSER_HERE)
        self._stops.ask(run.id.value)
        # ponytail: in-process only. A device run and its socket live in one
        # worker, so stopping must land there too -- sticky-route by device_id
        # if this is ever run with more than one.
        return run
