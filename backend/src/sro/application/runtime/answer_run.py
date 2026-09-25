from __future__ import annotations

from typing import Literal

from sro.application.context import RequestContext
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.progress import Progress
from sro.domain.shared.errors import Conflict, NotFound

K_ANSWER = 500

WriteVerdict = Literal["", "done", "not_done"]


class AnswerRun:
    def __init__(self, uow: UnitOfWork, durable: DurableExecution) -> None:
        self._uow = uow
        self._durable = durable

    async def execute(
        self,
        ctx: RequestContext,
        *,
        run_id: str,
        question_id: str,
        value: str,
        verdict: WriteVerdict = "",
    ) -> None:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
        if run is None:
            raise NotFound("no such run")
        if run.outcome != "running":
            raise Conflict("that run is no longer running")
        progress = Progress.of(run.progress)
        asking = progress.asking
        if not asking:
            await self._durable.answer_run(run_id, question_id, "", "")
            return
        if asking.get("id") != question_id:
            raise Conflict("that is not the question this run is waiting on")
        kind = asking.get("kind")
        if kind in ("password", "code") and value:
            raise Conflict(
                "a secret is never sent as an answer: a password is stored with "
                "PUT /v1/secrets and a one-time code is typed on the page"
            )
        if verdict and kind != "step":
            raise Conflict("only a question about a step takes a verdict")
        if kind == "step" and not verdict and progress.in_doubt(int(asking.get("step") or -1)):
            raise Conflict("say whether the write was done: its verdict is done or not_done")
        await self._durable.answer_run(run_id, question_id, value, verdict)
