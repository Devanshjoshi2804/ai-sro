from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import ClassVar, Protocol

from sro.application.chat.candidates import rank_jobs
from sro.application.chat.from_the_mail import FromTheMail
from sro.application.chat.read_threads import ReadThreads
from sro.application.chat.understand import held_runs
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import ListWorkflowRuns
from sro.application.lookup.look_it_up import LookItUp, what_was_found
from sro.application.lookup.run_lookups import K_WHILE_TALKING
from sro.application.ports.model import AskerUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap
from sro.application.skill.job_facts import JobFacts, job_facts
from sro.domain.chat.asking import standing
from sro.domain.chat.brain_turn import ToolResult
from sro.domain.execution.compiled import why_not
from sro.domain.execution.mail_job import built_ins
from sro.domain.execution.workflow_run import SETTLED, WorkflowRun
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import PrincipalId

K_RECENT_RUNS = 20

K_TEXT = 2000

K_SHOWN_JOBS = 5


class Tool(Protocol):
    name: str
    about: str
    args: ClassVar[dict[str, object]]

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult: ...


def described(tools: Sequence[Tool]) -> list[dict[str, object]]:
    return [{"name": one.name, "does": one.about, "args": one.args} for one in tools]


def _bounded(text: str) -> str:
    return text if len(text) <= K_TEXT else text[: K_TEXT - 1] + "…"


def _job(one: JobFacts) -> dict[str, object]:
    return {
        "id": one.workflow.id,
        "title": one.workflow.title,
        "parameters": [
            {
                "name": field.name,
                "required": field.kind == "required",
                "max_length": field.limits.max_length,
                "options": list(field.limits.options) if field.limits.options else None,
            }
            for field in one.compiled.fields
            if field.kind != "never"
        ],
        "runnable": one.compiled.runnable,
        **({} if one.compiled.runnable else {"cannot_run": why_not(one.compiled.reasons)}),
    }


class FindJobs:
    name = "find_jobs"
    about = (
        "Find the jobs this team has that could do what was asked (mail jobs included); "
        "returns each one's parameters and limits."
    )
    args: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
    }

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow, self._clock = uow, clock

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult:
        async with self._uow as uow:
            known = await uow.workflows.known(ctx.tenant_id)
            facts = await job_facts(uow, ctx.tenant_id, known, now=self._clock.now())
            held = await held_runs(uow, ctx.tenant_id)
        # The reader's own ranking: real jobs only, the same limits it checks.
        ranked = rank_jobs(str(args.get("query") or ""), facts, held=held, k=K_SHOWN_JOBS)
        jobs = [_job(one) for one in ranked]
        # A built-in takes its values from the conversation, as the reader treats it: no fields.
        jobs += [
            {"id": one.id, "title": one.title, "parameters": [], "runnable": True}
            for one in built_ins(ctx.tenant_id.value)
        ]
        return ToolResult(ok=True, data={"jobs": jobs})


def _stopped(run: WorkflowRun) -> str:
    last = max(run.steps, key=lambda one: one.order, default=None)
    return _bounded(last.reason) if last is not None and last.verdict not in SETTLED else ""


class RunStatus:
    name = "run_status"
    about = (
        "What the operator's recent runs did: job, values, state, why one stopped, "
        "whether it came from mail, and any question waiting on an answer."
    )
    args: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {"run_id": {"type": "string"}},
    }

    def __init__(self, runs: ListWorkflowRuns, threads: ReadThreads) -> None:
        self._runs, self._threads = runs, threads

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult:
        found = await self._runs.execute(
            ctx, workflow_id=None, limit=K_RECENT_RUNS, awaiting=False, mine=True
        )
        wanted = str(args.get("run_id") or "")
        rows = [await self._row(ctx, one) for one in found if not wanted or one.id == wanted]
        return ToolResult(ok=True, data={"runs": rows})

    async def _row(self, ctx: RequestContext, run: WorkflowRun) -> dict[str, object]:
        return {
            "id": run.id,
            "job": run.workflow_id,
            "values": {k: v for k, v in run.values.items() if not is_secret_field(k)},
            "state": run.outcome,
            "stopped_because": _stopped(run),
            "from_mail": bool(run.mail),
            "question": await self._question(ctx, run),
        }

    async def _question(self, ctx: RequestContext, run: WorkflowRun) -> str:
        # The run's own ask chat, keyed as the run keys it when it asks.
        owner = RequestContext(ctx.tenant_id, PrincipalId(run.started_by or ctx.principal_id.value))
        chat = await self._threads.asking(owner, (run.mail or {}).get("thread") or run.id)
        asked = standing(chat.messages) if chat is not None else None
        if asked is None or (asked.decision or {}).get("from_run", run.id) != run.id:
            return ""
        return _bounded(asked.text)


class CheckMail:
    name = "check_mail"
    about = "Look in the mailbox now for new work; says, per mail, what happened to it."
    args: ClassVar[dict[str, object]] = {"type": "object", "properties": {}}

    def __init__(self, look: FromTheMail) -> None:
        self._look = look

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult:
        try:
            looked = await self._look.execute(ctx)
        except (OverCap, AskerUnavailable, DomainError) as stopped:
            return ToolResult(ok=False, error=str(stopped))
        return ToolResult(ok=True, data={"said": _bounded(looked.said()), "read": looked.read})


class Lookup:
    name = "lookup"
    about = "Answer a question about a system from what this team's systems hold; read-only."
    args: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {"question": {"type": "string"}},
        "required": ["question"],
    }

    def __init__(self, look: LookItUp) -> None:
        self._look = look

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult:
        try:
            found = await self._look.execute(
                ctx, str(args.get("question") or ""), within=K_WHILE_TALKING
            )
        except (OverCap, AskerUnavailable) as stopped:
            return ToolResult(ok=False, error=str(stopped))
        if found is None:
            return ToolResult(ok=False, error="nothing here knows how to look that up")
        said = _bounded(what_was_found(found))
        if not found.any_answered:
            return ToolResult(ok=False, error=said)
        source = sorted({one.lookup.target for one in found.looked if one.ok})
        return ToolResult(ok=True, data={"answer": said, "source": source})
