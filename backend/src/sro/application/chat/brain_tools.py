from __future__ import annotations

from collections.abc import Callable, Coroutine, Mapping, Sequence
from typing import ClassVar, Protocol

from sro.application.chat.candidates import rank_jobs, real_jobs
from sro.application.chat.from_the_mail import FromTheMail
from sro.application.chat.mailbox import SERVER
from sro.application.chat.read_threads import ReadThreads
from sro.application.chat.understand import held_runs
from sro.application.connection.sign_in import logins_of
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import (
    GetWorkflowRun,
    ListWorkflowRuns,
    StartWorkflowRun,
)
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.pursue import Pursuit, compose
from sro.application.lookup.look_it_up import LookItUp, what_was_found
from sro.application.lookup.run_lookups import K_WHILE_TALKING
from sro.application.ports.model import AskerUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap, RunRefused
from sro.application.skill.job_facts import JobFacts, job_facts
from sro.domain.chat.asking import standing
from sro.domain.chat.brain_turn import ToolResult
from sro.domain.chat.request import refusal
from sro.domain.chat.thread import Said
from sro.domain.execution.compiled import why_not
from sro.domain.execution.field_classes import FieldLimits
from sro.domain.execution.mail_job import built_in, built_ins
from sro.domain.execution.workflow_run import SETTLED, OfferTaken, WorkflowRun
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import PrincipalId

K_RECENT_RUNS = 20

K_TEXT = 2000

K_SHOWN_JOBS = 5

Spawn = Callable[[Coroutine[object, object, None]], None]


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


async def _launch(
    start: StartWorkflowRun,
    spawn: Spawn,
    ctx: RequestContext,
    *,
    workflow_id: str,
    values: Mapping[str, str],
    offer: str = "",
    undoes_run: str = "",
) -> ToolResult:
    """The one way a brain tool starts a run: the chat's own start, once.

    A refusal comes back as data for the model to say or ask about; nothing
    here retries it.
    """
    try:
        run = await start.execute(
            ctx,
            workflow_id=workflow_id,
            device_id=None,
            values=values,
            live=True,
            allow_focus=True,
            conversation=(SERVER, ""),
            offer=offer,
            undoes_run=undoes_run,
        )
    except OfferTaken as taken:
        return ToolResult(ok=True, data={"run_id": taken.run_id, "state": "already running"})
    except (DomainError, RunRefused, OverCap, AskerUnavailable) as why:
        return ToolResult(ok=False, error=_bounded(str(why)))
    if run.executor == "steel":
        if not await start.start_on_steel(ctx, run):
            return ToolResult(ok=False, error="it could not be handed on; nothing was done")
    else:
        spawn(start.perform(ctx, run))
    return ToolResult(
        ok=True,
        data={"run_id": run.id, "state": run.outcome},
        decision={"kind": Said.RUN.value, "run_id": run.id},
    )


class StartJob:
    name = "start_job"
    about = (
        "Start a job at once with the values given for its parameters. Refused, with the "
        "reason, when a value is too long or not allowed or a required one is missing: "
        "ask the operator, never retry the same values."
    )
    args: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {
            "job_id": {"type": "string"},
            "values": {"type": "object"},
        },
        "required": ["job_id"],
    }

    def __init__(
        self, uow: UnitOfWork, clock: Clock, start: StartWorkflowRun, spawn: Spawn, offer: str = ""
    ) -> None:
        # The offer a run is made under is the caller's (a mail's id), never the model's:
        # it is what makes a second start answer the first run.
        self._uow, self._clock, self._start, self._spawn = uow, clock, start, spawn
        self._offer = offer

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult:
        job_id = str(args.get("job_id") or "")
        given = args.get("values") or {}
        if not isinstance(given, Mapping):
            return ToolResult(ok=False, error="values is an object of parameter name to value")
        values = {str(k): str(v).strip() for k, v in given.items() if str(v).strip()}
        async with self._uow as uow:
            known = await uow.workflows.known(ctx.tenant_id)
            facts = await job_facts(uow, ctx.tenant_id, known, now=self._clock.now())
            held = await held_runs(uow, ctx.tenant_id)
        logins = await logins_of(self._uow, ctx.tenant_id)
        real = real_jobs(((one.workflow, one.by_id) for one in facts), held=held)
        job = next((one for one in facts if one.workflow.id == job_id and job_id in real), None)
        if job is None and built_in(job_id, ctx.tenant_id.value) is None:
            return ToolResult(ok=False, error="that is not a job this team has; use find_jobs")
        # A built-in takes its values from the conversation: it has no fields to check them by.
        fields = (
            {one.name: one for one in job.compiled.fields if one.kind != "never"} if job else {}
        )
        wrong = [
            f"{name} is a secret: never give a password, code or token"
            for name in values
            if is_secret_field(name)
        ]
        if job is not None:
            unknown = sorted(n for n in values if n not in fields and not is_secret_field(n))
            wrong += [f"this job has no {name}" for name in unknown]
        wrong += [
            f"the {name} you gave is {why}"
            for name, value in values.items()
            if (
                why := refusal(
                    value, value, fields[name].limits if name in fields else FieldLimits(), logins
                )
            )
        ]
        absent = sorted(
            n for n, one in fields.items() if one.kind == "required" and n not in values
        )
        if absent:
            wrong.append(f"missing: {', '.join(absent)}")
        if wrong:
            return ToolResult(ok=False, error="; ".join(wrong))
        return await _launch(
            self._start,
            self._spawn,
            ctx,
            workflow_id=job_id,
            values=values,
            offer=self._offer,
        )


class UndoRun:
    name = "undo_run"
    about = (
        "Take back what one of the operator's own runs made, by starting the job that deletes it."
    )
    args: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {"run_id": {"type": "string"}},
        "required": ["run_id"],
    }

    def __init__(self, runs: GetWorkflowRun, start: StartWorkflowRun, spawn: Spawn) -> None:
        self._runs, self._start, self._spawn = runs, start, spawn

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult:
        try:
            run = await self._runs.execute(ctx, run_id=str(args.get("run_id") or ""))
        except DomainError as why:
            return ToolResult(ok=False, error=str(why))
        if run.started_by != ctx.principal_id.value:
            return ToolResult(ok=False, error="that run is not yours to take back")
        back = await self._runs.undo_for(ctx, run)
        if back is None:
            return ToolResult(ok=False, error="nothing this run did can be taken back")
        undo_job, asks, names = back
        return await _launch(
            self._start,
            self._spawn,
            ctx,
            workflow_id=undo_job,
            values={asks: names},
            undoes_run=run.id,
        )


class AskOperator:
    name = "ask_operator"
    about = "Ask the operator one question and wait for the answer; ends this turn."
    args: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {"question": {"type": "string"}},
        "required": ["question"],
    }

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult:
        question = str(args.get("question") or "").strip()
        if not question:
            return ToolResult(ok=False, error="say what to ask")
        return ToolResult(
            ok=True, ends_turn=True, decision={"kind": "brain_asks", "question": _bounded(question)}
        )


class WorkItOut:
    name = "work_it_out"
    about = (
        "Plan a task on the screen; only for a real task in the operator's warehouse system "
        "that no job covers, never for mail, status or chat questions."
    )
    args: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {"task": {"type": "string"}},
        "required": ["task"],
    }

    def __init__(self, plan: PlanTask) -> None:
        self._plan = plan

    async def run(self, ctx: RequestContext, args: Mapping[str, object]) -> ToolResult:
        task = str(args.get("task") or "").strip()
        if not task:
            return ToolResult(ok=False, error="say what the task is")
        proposal = await self._plan.execute(ctx, utterance=task)
        pursuit = Pursuit.of(ctx, compose(task, proposal))
        return ToolResult(
            ok=True,
            data={
                "plan": _bounded(pursuit.goal.brief()),
                "changes_the_system": pursuit.goal.changes_the_system,
                "say": pursuit.question or "",
            },
        )


def brain_tools(
    *,
    uow: UnitOfWork,
    clock: Clock,
    runs: ListWorkflowRuns,
    run: GetWorkflowRun,
    threads: ReadThreads,
    look_mail: FromTheMail,
    look_up: LookItUp,
    start: StartWorkflowRun,
    plan: PlanTask,
    spawn: Spawn,
    offer: str = "",
) -> tuple[Tool, ...]:
    return (
        FindJobs(uow, clock),
        StartJob(uow, clock, start, spawn, offer),
        RunStatus(runs, threads),
        CheckMail(look_mail),
        UndoRun(run, start, spawn),
        Lookup(look_up),
        AskOperator(),
        WorkItOut(plan),
    )
