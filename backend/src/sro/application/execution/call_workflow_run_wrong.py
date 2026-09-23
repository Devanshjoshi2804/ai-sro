from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.call_run_wrong import StillRunning
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.errors import NotFound


class CallWorkflowRunWrong:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, run_id: str, because: str) -> WorkflowRun:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
            if run is None:
                raise NotFound("no such run")
            if run.outcome == "running":
                raise StillRunning("this run is still going; stopping it is a different thing")
            run.wrong_because = because
            await uow.workflow_runs.save(run)
            await uow.workflows.forget_effects(run.workflow_id)
            await uow.commit()
        return run
