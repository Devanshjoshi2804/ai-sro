from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Literal

from sro.application.context import RequestContext
from sro.application.execution.mail_job import MAIL_BODY
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.mail_job import mailboxes
from sro.domain.execution.progress import Progress
from sro.domain.execution.workflow_run import answers_for
from sro.domain.shared.errors import Conflict, NotFound

K_ANSWER = 500

WriteVerdict = Literal["", "done", "not_done"]


class AnswerRun:
    def __init__(
        self,
        uow: UnitOfWork,
        durable: DurableExecution,
        *,
        resume: Callable[[RequestContext, str], Awaitable[None]] | None = None,
    ) -> None:
        self._uow = uow
        self._durable = durable
        self._resume = resume

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
        if not answers_for(run, ctx.principal_id.value):
            raise Conflict("only the operator who started this run answers its questions")
        progress = Progress.of(run.progress)
        asking = progress.asking
        kind = asking.get("kind")
        drafted = run.executor != "steel" and kind in ("recipient", MAIL_BODY)
        if run.outcome != ("stopped" if drafted else "running"):
            raise Conflict("that run is no longer running")
        if not asking or asking.get("id") != question_id:
            raise Conflict("that is not the question this run is waiting on")
        if value and kind not in ("value", "field", "recipient", MAIL_BODY):
            raise Conflict(
                "only a question for a value takes one: a password is stored with "
                "PUT /v1/secrets, a one-time code is typed on the page, and a step "
                "is answered by its verdict"
            )
        chosen = value.strip()
        if kind == "field" and chosen and chosen not in json.loads(asking.get("choices") or "[]"):
            raise Conflict("a field is answered by one of the choices it offered, or left out")
        if verdict and kind != "step":
            raise Conflict("only a question about a step takes a verdict")
        if kind == "step" and not verdict and progress.in_doubt(int(asking.get("step") or -1)):
            raise Conflict("say whether the write was done: its verdict is done or not_done")
        answer = {"answered": "yes", "verdict": verdict}
        if kind == "field":
            answer |= {"choice": chosen, "by": ctx.principal_id.value}
        if kind == "recipient":
            named = mailboxes(chosen)
            if not named:
                raise Conflict("who a mail goes to is answered with one or more addresses")
            answer |= {"address": ", ".join(named), "by": ctx.principal_id.value}
        if kind == MAIL_BODY:
            if not chosen:
                raise Conflict("what a mail says is answered with its words")
            answer |= {"said": chosen, "by": ctx.principal_id.value}
        if asking.get("answered"):
            if any(asking.get(key, "") != said for key, said in answer.items()):
                raise Conflict("that question was already answered")
        else:
            progress.asking = {**asking, **answer}
            async with self._uow as uow:
                kept = await uow.workflow_runs.record_progress(
                    ctx.tenant_id, run_id, progress.as_json(), was=run.progress
                )
                if kept:
                    await uow.commit()
            if not kept:
                raise Conflict("that question was answered, or the run moved on, meanwhile")
        if drafted and self._resume is not None:
            await self._resume(ctx, run_id)
            return
        await self._durable.answer_run(run_id, question_id)
