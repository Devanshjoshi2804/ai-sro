from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.progress import Progress
from sro.domain.shared.errors import Conflict, NotFound

K_ANSWER = 500


class AnswerRun:
    def __init__(self, uow: UnitOfWork, durable: DurableExecution) -> None:
        self._uow = uow
        self._durable = durable

    async def execute(
        self, ctx: RequestContext, *, run_id: str, question_id: str, value: str
    ) -> None:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
        if run is None:
            raise NotFound("no such run")
        if run.outcome != "running":
            raise Conflict("that run is no longer running")
        asking = Progress.of(run.progress).asking
        if not asking:
            await self._durable.answer_run(run_id, question_id, "")
            return
        if asking.get("id") != question_id:
            raise Conflict("that is not the question this run is waiting on")
        if asking.get("kind") == "password" and value:
            raise Conflict("a password is stored with PUT /v1/secrets, never sent as an answer")
        await self._durable.answer_run(run_id, question_id, value)
