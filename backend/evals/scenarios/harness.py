"""The scenario harness: the real chat brain and the real model over a fake world.

`chat_scenarios.py` describes what operators typed and what could break the brain; this
module plays it. One THREAD per scenario, its turns in order, each through the real `Brain.turn`
(`dry=False`) with the real asker, over tools that implement the real `Tool` protocol and
record instead of launch. A checker scores each turn against its expectations and the
invariants I1-I7, and a report says what failed. It is a probe, not a gate.

How each fake mirrors the real tool (`application/chat/brain_tools.py`), and where it cannot:

* find_jobs: the eval's three jobs (`evals.suites.chat`) plus `world.jobs`, in the real `_job`
  shape. Not ranked by the query (the real one ranks and shows 5; the world has fewer).
  An extra job is a delete-by-code job: one required `Customer Type`, at most 4 characters.
* start_job: the REAL `StartJob.run` and the real `_launch`. Only `check` is replaced, and it
  reuses `values_of`, `what_is_wrong` and the built-in mail-job refusal; the start port is a
  fake whose `execute` raises the real `OfferTaken` for a repeated offer key, or for a job and
  values that a run in `world.runs` or an earlier start in this thread already holds
  ("already running"). The real tool has no thread-wide dedupe; the fake adds it because the
  real start would answer an identical running run. The tenant's sign-in names (`Logins`) are
  not held, so "a sign-in name is never a value" is not checked.
* undo_run: the REAL `UndoRun`, over a fake run port: only a done run of the operator's whose
  job is a Create one can be taken back, once, by the Delete a Customer Type job.
* run_status: the real row shape from `world.runs`; `job` is the job's id, as the real one.
* check_mail: the real tool asks a model to read each mail and says only what happened to it
  (a job offered or started); the body never reaches the brain. The fake cannot read a mail
  without a model, so it shows each non-automated mail's subject, sender and body (bounded
  as the real tool bounds its text), which is stricter for the injection scenarios. An
  automated mail (`domain/chat/automated_mail.is_automated`) is read and ignored, as the real
  one does. A second look finds nothing new. `mail_down` is a failed tool.
* lookup: `world.lookup`, or "nothing found". The real one drives a Steel session.
* ask_operator: the real tool. work_it_out: records the task and returns a plan, never runs.
* An open offer: the real converse answers a yes or a no to a standing offer itself, before
  the brain sees it. The runner does the same (`said_yes`, `let_go`), and any other first
  message reaches the brain with the offer's own text (`of_the_offer`) in its history.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from types import SimpleNamespace
from typing import Any, cast

from evals.suites.chat import _FIELDS, _JOBS, _Day, _job, _Nowhere
from sro.application.chat.brain import Brain
from sro.application.chat.brain_tools import (
    AskOperator,
    CheckMail,
    FindJobs,
    Lookup,
    RunStatus,
    StartJob,
    Tool,
    UndoRun,
    WorkItOut,
    _bounded,
    values_of,
    what_is_wrong,
)
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import GetWorkflowRun, StartWorkflowRun
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.asking import Pending, let_go, of_the_offer, said_yes
from sro.domain.chat.automated_mail import is_automated
from sro.domain.chat.brain_turn import K_HISTORY, Origin, ToolResult, Turn
from sro.domain.execution.field_classes import FieldClass, FieldLimits
from sro.domain.execution.mail_job import built_in
from sro.domain.execution.workflow_run import OfferTaken
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.signing_in import Logins

DELETE = "Delete a Customer Type"
_CODE = "Customer Type"

_HOLDING = frozenset({"running", "waiting"})


@dataclass(frozen=True)
class Launch:
    """A run the brain (or the operator's yes) started: recorded, never executed."""

    job: str
    job_id: str
    values: dict[str, str]
    run_id: str
    via: str  # "start" | "undo" | "offer"

    @property
    def key(self) -> tuple[str, tuple[tuple[str, str], ...]]:
        return self.job_id, tuple(sorted(self.values.items()))


def _extra_id(title: str) -> str:
    return "wfl_" + hashlib.sha256(title.encode()).hexdigest()[:32]


def _held(job_id: str, values: Mapping[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
    return job_id, tuple(
        sorted((str(k), str(v).strip()) for k, v in values.items() if str(v).strip())
    )


class World:
    """One scenario's world: jobs, runs, mail and what the thread has started so far."""

    def __init__(self, spec: Mapping[str, Any] | None = None) -> None:
        spec = spec or {}
        self.spec = spec
        # id -> (title, [(parameter, required, max_length)])
        self.jobs: dict[str, tuple[str, list[tuple[str, bool, int]]]] = {
            ident: (title, params) for ident, title, params in _JOBS
        }
        for title in spec.get("jobs") or ():
            self.jobs[_extra_id(title)] = (title, [(_CODE, True, 4)])
        self.fields: dict[str, dict[str, FieldClass]] = dict(_FIELDS)
        for ident, (_, params) in self.jobs.items():
            self.fields.setdefault(
                ident,
                {
                    n: FieldClass(n, "required" if req else "sometimes", (), FieldLimits(longest))
                    for n, req, longest in params
                },
            )
        self.runs: list[dict[str, Any]] = [dict(one) for one in spec.get("runs") or ()]
        self.mail: list[dict[str, Any]] = [dict(one) for one in spec.get("mail") or ()]
        self.looked = False
        self.offers_taken: dict[str, str] = {}
        self.launches: list[Launch] = []
        self.undone: set[str] = set()
        self.works: list[str] = []

    def id_of(self, title: str) -> str:
        return next((i for i, (t, _) in self.jobs.items() if t == title), title)

    def title_of(self, job_id: str) -> str:
        # The undo job is always there to be started, listed or not.
        return (
            self.jobs[job_id][0]
            if job_id in self.jobs
            else DELETE
            if job_id == _extra_id(DELETE)
            else job_id
        )

    def run_rows(self) -> list[dict[str, object]]:
        return [
            {
                "id": one["id"],
                "job": self.id_of(str(one.get("job", ""))),
                "values": dict(one.get("values") or {}),
                "state": one.get("state", "running"),
                "stopped_because": _bounded(str(one.get("reason") or "")),
                "from_mail": bool(one.get("mail")),
                "question": str(one.get("question") or ""),
            }
            for one in self.runs
        ]

    def running(self, job_id: str, values: Mapping[str, str]) -> str:
        """The id of the run that already holds this job and these values, or ''."""
        want = _held(job_id, values)
        for one in self.runs:
            if (
                one.get("state") in _HOLDING
                and _held(self.id_of(str(one["job"])), one.get("values") or {}) == want
            ):
                return str(one["id"])
        return next((one.run_id for one in self.launches if one.key == want), "")


class FakeJobs(FindJobs):
    def __init__(self, world: World) -> None:
        self._world = world

    async def run(
        self, ctx: RequestContext, args: Mapping[str, object], turn: Turn = Turn()
    ) -> ToolResult:
        jobs = [_job((ident, title, params)) for ident, (title, params) in self._world.jobs.items()]
        return ToolResult(ok=True, data={"jobs": jobs})


class FakeRuns(RunStatus):
    def __init__(self, world: World) -> None:
        self._world = world

    async def run(
        self, ctx: RequestContext, args: Mapping[str, object], turn: Turn = Turn()
    ) -> ToolResult:
        wanted = str(args.get("run_id") or "")
        rows = [one for one in self._world.run_rows() if not wanted or one["id"] == wanted]
        return ToolResult(ok=True, data={"runs": rows})


class FakeMail(CheckMail):
    def __init__(self, world: World) -> None:
        self._world = world

    async def run(
        self, ctx: RequestContext, args: Mapping[str, object], turn: Turn = Turn()
    ) -> ToolResult:
        world = self._world
        if world.spec.get("mail_down"):
            return ToolResult(ok=False, error="the mailbox cannot be reached right now")
        mails, world.mail, world.looked = world.mail, [], True
        lines = []
        for one in mails:
            sender, subject = str(one.get("from") or ""), str(one.get("subject") or "")
            if is_automated(sender, one.get("headers") or {}):
                continue
            about = f"'{subject}'" if subject.strip() else "a mail with no subject"
            lines.append(f"- {about} from {sender}: {one.get('body') or ''}")
        if not mails:
            said = "Looked in the mail: no mail has arrived since the last look."
        elif not lines:
            said = "Looked in the mail: none of it asks for a job here."
        else:
            said = "Looked in the mail:\n" + "\n".join(lines)
        return ToolResult(ok=True, data={"said": _bounded(said), "read": len(mails)})


class FakeLookup(Lookup):
    def __init__(self, world: World) -> None:
        self._world = world

    async def run(
        self, ctx: RequestContext, args: Mapping[str, object], turn: Turn = Turn()
    ) -> ToolResult:
        found = self._world.spec.get("lookup")
        if not found:
            return ToolResult(ok=False, error="nothing found")
        return ToolResult(ok=True, data={"answer": _bounded(str(found)), "source": ["fake"]})


class FakeWork(WorkItOut):
    def __init__(self, world: World) -> None:
        self._world = world

    async def run(
        self, ctx: RequestContext, args: Mapping[str, object], turn: Turn = Turn()
    ) -> ToolResult:
        task = str(args.get("task") or "").strip()
        if not task:
            return ToolResult(ok=False, error="say what the task is")
        self._world.works.append(task)
        return ToolResult(
            ok=True,
            data={"plan": _bounded(f"plan for: {task}"), "changes_the_system": False, "say": ""},
        )


class FakeStart:
    """The start port: the real start's answers, a record instead of a launch."""

    def __init__(self, world: World) -> None:
        self._world = world

    async def execute(
        self,
        ctx: RequestContext,
        *,
        workflow_id: str,
        values: Mapping[str, str],
        offer: str = "",
        undoes_run: str = "",
        **_: object,
    ) -> Any:
        world = self._world
        if offer in world.offers_taken:
            raise OfferTaken(offer, world.offers_taken[offer])
        if (held := world.running(workflow_id, values)) and not undoes_run:
            raise OfferTaken(offer or workflow_id, held)
        run_id = f"run_fake{len(world.launches) + 1}"
        world.launches.append(
            Launch(
                world.title_of(workflow_id),
                workflow_id,
                dict(values),
                run_id,
                "undo" if undoes_run else "offer" if offer.startswith("offer:") else "start",
            )
        )
        if offer:
            world.offers_taken[offer] = run_id
        return SimpleNamespace(
            id=run_id,
            executor="steel",
            outcome="running",
            pinned=SimpleNamespace(title=world.title_of(workflow_id)),
        )

    async def start_on_steel(self, ctx: RequestContext, run: object) -> bool:
        return True

    async def perform(self, ctx: RequestContext, run: object) -> None:
        return None


class FakeStartJob(StartJob):
    """The real `run` and `_launch`; `check` is the real refusals over this world's jobs."""

    def __init__(self, world: World) -> None:
        self._world = world
        self._start = cast(StartWorkflowRun, FakeStart(world))
        self._spawn = lambda coro: coro.close()

    async def check(
        self, ctx: RequestContext, args: Mapping[str, object], turn: Turn = Turn()
    ) -> ToolResult | None:
        world, job_id = self._world, str(args.get("job_id") or "")
        values = values_of(args)
        if values is None:
            return ToolResult(ok=False, error="values is an object of parameter name to value")
        if job_id not in world.jobs:
            if built_in(job_id, ctx.tenant_id.value) is not None:
                return ToolResult(
                    ok=False,
                    error="that job sends mail, and mail goes out only when the operator presses "
                    "Send it; tell the operator you cannot send mail from chat",
                )
            return ToolResult(ok=False, error="that is not a job this team has; use find_jobs")
        wrong = what_is_wrong(values, world.fields[job_id], turn.said, Logins())
        return ToolResult(ok=False, error="; ".join(wrong)) if wrong else None


class _Runs:
    """The run port UndoRun reads: the operator's own runs, and what taking one back means."""

    def __init__(self, world: World) -> None:
        self._world = world

    async def execute(self, ctx: RequestContext, *, run_id: str) -> Any:
        for one in self._world.runs:
            if one["id"] == run_id:
                return SimpleNamespace(**one, started_by=ctx.principal_id.value)
        raise NotFound("no such run")

    async def undo_for(self, ctx: RequestContext, run: Any) -> tuple[str, str, str] | None:
        world = self._world
        made = str(run.job).startswith("Create ")
        if run.state != "done" or not made or run.id in world.undone:
            return None
        names = str((run.values or {}).get(_CODE) or "").strip()
        if not names:
            return None
        world.undone.add(run.id)
        return _extra_id(DELETE), _CODE, names


def fake_tools(world: World) -> list[Tool]:
    undo = UndoRun(
        cast(GetWorkflowRun, _Runs(world)),
        cast(StartWorkflowRun, FakeStart(world)),
        lambda c: c.close(),
    )
    return [
        FakeJobs(world),
        FakeStartJob(world),
        FakeRuns(world),
        FakeMail(world),
        undo,
        FakeLookup(world),
        AskOperator(),
        FakeWork(world),
    ]


# ---------------------------------------------------------------------------------------------
# The runner: one thread per scenario, its turns in order, through the real brain.
# ---------------------------------------------------------------------------------------------

K_TURN_S = 180.0

_BRAIN_LOG = "sro.application.chat.brain"


@dataclass
class Played:
    """Everything one turn did, as it happened."""

    said: str
    reply: str = ""
    # The operator's own words this turn: what a start's values must come from.
    heard: str = ""
    tools: list[dict[str, Any]] = field(default_factory=list)
    launches: list[dict[str, Any]] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    cost: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    latency: float = 0.0
    error: str | None = None
    timed_out: bool = False
    logs: list[str] = field(default_factory=list)


class _Meter:
    """The asker, with what the turn cost and why it failed."""

    def __init__(self, asker: Asker) -> None:
        self._asker = asker
        self.cost, self.tokens_in, self.tokens_out = 0.0, 0, 0
        self.error: str | None = None

    async def ask(self, **asking: Any) -> Answer:
        answer = await self._asker.ask(**asking)
        self.cost += answer.cost_usd
        self.tokens_in += answer.in_tokens
        self.tokens_out += answer.out_tokens
        if answer.data is None and self.error is None:
            self.error = answer.error or "the model did not answer"
        return answer


class _Logs(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


@contextmanager
def _brain_logs() -> Iterator[_Logs]:
    log, handler = logging.getLogger(_BRAIN_LOG), _Logs()
    was = log.level
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    try:
        yield handler
    finally:
        log.removeHandler(handler)
        log.setLevel(was)


def _offer_of(world: World) -> Pending | None:
    offers = world.spec.get("offers") or ()
    if not offers:
        return None
    one = offers[-1]
    return Pending(world.id_of(one["job"]), one["job"], dict(one.get("values") or {}), ())


async def _answer_offer(
    world: World, ctx: RequestContext, offer: Pending, said: str, key: str
) -> str:
    if let_go(said):
        return f"Left {offer.title}."
    try:
        await FakeStart(world).execute(
            ctx, workflow_id=offer.workflow_id, values=offer.values, offer=f"offer:{key}"
        )
    except OfferTaken:
        return "That one is already running."
    return f"Started {offer.title}."


async def play(scenario: Mapping[str, Any], asker: Asker, *, tenant: str = "eval") -> list[Played]:
    """One thread: the scenario's turns in order, history and the open question carried as
    `converse` carries them. A turn that broke says so in `error`."""
    spec = scenario.get("world") or {}
    world, meter = World(spec), _Meter(asker)
    tools = fake_tools(world)
    brain = Brain(cast(UnitOfWork, _Nowhere()), cast(Asker, meter), _Day(), tools, cap_usd=-1.0)
    ctx = RequestContext(tenant_id=TenantId(tenant), principal_id=PrincipalId("eval"))
    origin = (
        Origin("mail", str(spec.get("sender") or ""), str(spec.get("subject") or "a request"))
        if spec.get("origin") == "mail"
        else Origin("chat")
    )
    history: list[str] = list(spec.get("history") or [])
    asking = str(spec.get("asking") or "")
    if asking:
        history.append(f"assistant: {asking}")
    offer = _offer_of(world)
    if offer is not None:
        history.append(f"assistant: {of_the_offer(offer)}")
    played: list[Played] = []
    for n, turn in enumerate(scenario["turns"]):
        said, key = str(turn["said"]), f"{scenario['id']}-{n}"
        one = Played(said)
        ours = [
            h.removeprefix("operator: ") for h in history[-K_HISTORY:] if h.startswith("operator: ")
        ]
        one.heard = "\n".join([said, *ours, asking])
        before = len(world.launches)
        meter.cost, meter.tokens_in, meter.tokens_out, meter.error = 0.0, 0, 0, None
        began = time.monotonic()
        decisions: tuple[dict[str, object], ...] = ()
        cards: list[str] = []
        with _brain_logs() as logs:
            try:
                if offer is not None and (said_yes(said) or let_go(said)):
                    one.reply = await _answer_offer(world, ctx, offer, said, key)
                else:
                    reply = await asyncio.wait_for(
                        brain.turn(
                            ctx,
                            message=said,
                            history=history,
                            asking=asking,
                            origin=origin,
                            offer=f"chat:{key}",
                        ),
                        K_TURN_S,
                    )
                    one.reply, decisions = reply.said, reply.decisions
                    one.tools = [
                        {
                            "tool": c.tool,
                            "args": c.args,
                            "ok": r.ok,
                            "error": r.error,
                            "data": r.data,
                        }
                        for c, r in reply.steps
                    ]
                    one.questions = [
                        r.said for c, r in reply.steps if c.tool == "ask_operator" and r.ok
                    ]
                    # Every run the turn started keeps its card, as converse writes them.
                    cards = [r.said for _, r in reply.steps if r.decision][:-1]
            except TimeoutError:
                one.timed_out = True
        one.latency = time.monotonic() - began
        one.cost, one.tokens_in, one.tokens_out = meter.cost, meter.tokens_in, meter.tokens_out
        one.logs = logs.lines
        one.launches = [asdict(x) for x in world.launches[before:]]
        down = one.reply.startswith("I can't answer right now")
        one.error = meter.error or (one.reply if down else None)
        offer = None
        history += [f"operator: {said}", *(f"assistant: {x}" for x in (*cards, one.reply) if x)]
        asked = decisions[-1] if decisions else None
        asking = (
            str(asked.get("question") or "") if asked and asked.get("kind") == "brain_asks" else ""
        )
        played.append(one)
    return played
