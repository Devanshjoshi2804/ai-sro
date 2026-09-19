"""The press. A person opened a door and chose live or dry.

Ported from `start_run` in `new_agent_arch/src/rig/api.py:1021`. Nothing here
starts a run on its own: the rig has no scheduler for these and neither does
this, because a run drives an operator's own browser against their own
warehouse and there is nobody at the screen when nobody pressed anything.

**The order of the refusals is the rig's, and every position is an argument.**

* No model, first, and before a session is opened: a run plans every step on a
  model, so a deployment with none must not claim a row it can never drive.
* The cap, second and still before the browser is asked anything: a day that
  has spent its cap starts no run.
* The browser, third, and *before the workflow is looked up*. "your browser is
  not connected" is the answer a person can act on, and it holds whatever they
  asked for. A browser already driving a run is refused in the same place and
  for the same reason -- one browser, one hand: two runs driving the same
  window interleave their clicks into a form neither of them can then read
  back.
* Then the job, then the values, then which step to start on.

**The busy check is the answer, and it is not the guarantee.** Between reading
`in_flight` and the row existing there are two more awaits, and on one event
loop a second press can be scheduled in either of them: run against real
Postgres, two `asyncio.gather`ed presses produced two rows and zero refusals.
What makes "one browser, one hand" true is the UNIQUE partial index migration
0043 builds, which `SqlWorkflowRunRepository.save` turns into the same
`Conflict`, in the same words, out of `already_running`. The read stays because
it is the friendly answer and it names the run already driving; the index is
what holds when the read was right at the moment it was made and wrong by the
time the row was written.

**The row is claimed and committed here, not by the task.** Written inside
`run_workflow`, the `running` row appears only once the spawned task gets its
first slice, and a second press arriving in that window reads no busy run and
puts a second hand on the same browser. `run_workflow` says the same thing from
its own side and reads the row back as the authority for what was asked.

**`started_by` is the authenticated caller and never a name in a body.** A
request that says who authorised it is a signature nobody checked, and the
audit trail on a warehouse write is worth more than that.

Where the shape of the request is checked and where its meaning is:
`StartWorkflowRunRequest` refuses a body that is not an object of strings and a
`from_step` that is not honestly an integer, because both are facts about the
wire and pydantic already answers them -- the bool trap in particular can only
be caught before coercion, since `True` *is* an `int` by the time it reaches
here. What values a run may be performed *with*, and which steps a job has, are
this module's: trimming, dropping a value that is blank once trimmed, and the
range of `from_step` all need the workflow, and they live beside the refusal
that reads it.

**And the two reads of what the press left behind**, at the foot of the file:
`ListWorkflowRuns` (`api.py:1152`) and `GetWorkflowRun` (`api.py:1217`). They
are here rather than in a file of their own because the row they answer with
is the one `StartWorkflowRun` claims, and a reader asking what a run looks
like on the way out should not have to find a second module to learn what put
it there.

**And the stop button under them**, `AbortWorkflowRun` (`api.py:1237`), for the
same reason: the run it interrupts is the one claimed at the top of this file,
and the register it sets is the one `StartWorkflowRun` hands the task.

**And the Yes beside it**, `ApproveWorkflowStep` (`api.py:1270`), which is the
other half of the same seam: the stop button releases the approval wait to end
a run, and this one releases it to let the write out. Both reach the register
`StartWorkflowRun` handed the task, and neither of them is `/v1/confirmations`
-- that approves a *confirmation*, keyed on the confirmation and not the run.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import datetime

from sro.application.chat.announce import SayWhatHappened
from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.declared import declared_limits, names_of, screen_for
from sro.application.execution.gather import GatherContext
from sro.application.execution.read_runs import NOT_IN_A_BROWSER_HERE, CannotStop
from sro.application.execution.run_workflow import GatherValues, KnownFields, run_workflow
from sro.application.execution.stops import Stops
from sro.application.intent.spend import over_cap
from sro.application.knowledge.retrieve import Question, Retrieve
from sro.application.ports.channel import Channel
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.vault import CredentialVault, VaultUnavailable
from sro.application.shared.refusals import OverCap
from sro.domain.chat.asking import NEEDS, Pending, question
from sro.domain.chat.thread import Speaker
from sro.domain.execution.evidence import unperformable
from sro.domain.execution.gathering import Gathered
from sro.domain.execution.learned_step import limits_for
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.waiting import as_said, waiting_on
from sro.domain.execution.workflow_run import (
    RunStep,
    WorkflowRun,
    already_running,
    new_run_id,
)
from sro.domain.execution.write_plan import begins_again_at, seen_values
from sro.domain.knowledge.entry import EntryKind
from sro.domain.shared.errors import Conflict, DomainError, NotFound
from sro.domain.shared.identifiers import DeviceId, PrincipalId
from sro.domain.skill.reversals import addresses, identifies, undoes
from sro.domain.skill.shape import resumes_at
from sro.domain.skill.workflow import cited_ids

__all__ = [
    "AbortWorkflowRun",
    "ApproveWorkflowStep",
    "GetWorkflowRun",
    "ListWorkflowRuns",
    "NotDrivingThisRun",
    "RunRefused",
    "StartWorkflowRun",
]

logger = logging.getLogger(__name__)


DraftsForTheAsker = Callable[[RequestContext, str, Pending], Awaitable[bool]]
"""Write a mail to whoever asked, for a run that came up short.

A callable rather than the use case, for `GatherValues`' reason: this object
is built once per request and the drafter needs the request's own tenant and
operator. Optional throughout -- a deployment with no mailbox runs exactly as
it did, stopping with the question and asking nobody else.
"""


class RunRefused(Exception):
    """The press named something this job cannot be performed with.

    The rig's own 400, kept: the body parsed and its shape was right -- what it
    named was not a step of this job, or a value this job needs was not in it.
    Not a `DomainError`, for `OfferRefused`'s reason: a 422 is what a malformed
    body gets, and this body was not malformed.

    Never echoes a value out of the body. `str(exc)` becomes the `detail` of a
    problem document, and a refusal quoting the values writes a warehouse's own
    data into every access log between the browser and here.
    """

    code = "run_refused"


K_EVERY_FORM = 400
"""How many create forms one lookup asks for.

Every one, rather than a search: `search` matches terms against a claim's title
and key, and a form's key is its route -- so a lookup for `customerType` finds
nothing at all, which is how this was first built and why it said nothing.
Measured on QA 2026-09-16: 88 forms, 756 fields, 0.09 seconds for the lot.
Four hundred is room for a base four times that size before a write stops
seeing the screen it is writing to.
"""


def _asking(needs: Sequence[str], title: str, limits: Mapping[str, int]) -> str:
    """The sentence that opens the question, in the words of what went wrong.

    Two different things bring a run here and they want two different
    questions. A value nobody could find is "I could not find X". A value that
    would not fit is "X holds 28 characters" -- and asking that one the first
    way gets the same value back, because nothing has told the person their
    description is twice the length the box takes. The browser did not say so:
    it truncated in silence, which is why the limit had to be discovered at
    all.
    """
    capped = [name for name in needs if name in limits]
    if not capped:
        return f"I could not find {', '.join(needs)} for {title}. "
    said = ", ".join(f"{name} holds {limits[name]} characters" for name in capped)
    rest = [name for name in needs if name not in limits]
    return f"For {title}, {said} — longer than what I was given. " + (
        f"I could not find {', '.join(rest)} either. " if rest else ""
    )


class StartWorkflowRun:
    """Claim the row for one press, then drive it.

    Two halves on purpose, and the seam between them is the answer to the
    caller: `execute` refuses or claims and returns, and `perform` is what the
    spawned task awaits. A run in somebody's own browser is the one a person
    sits and watches, and they could not if the id only arrived when the last
    step landed.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        *,
        channel: Channel,
        asker: Asker | None,
        plan_model: str,
        rescue_model: str,
        clock: Clock,
        cap_usd: float,
        stops: Stops,
        approvals: Approvals,
        verified_writes: tuple[VerifiedWrite, ...] = (),
        vault: CredentialVault | None = None,
        retrieve: Retrieve | None = None,
        gather: GatherContext | None = None,
        ids: IdFactory | None = None,
        asker_drafts: DraftsForTheAsker | None = None,
    ) -> None:
        self._uow = uow
        self._asker_drafts: DraftsForTheAsker | None = asker_drafts
        # Where a password comes from when a step types one. `None` is a
        # deployment with no vault configured: the run still happens, and a
        # step that needs a password refuses with the key it wanted rather
        # than typing a blank into a login form.
        self._vault = vault
        # What the knowledge base knows about a field. `None` is a deployment
        # with no retriever built, which is not a degraded mode: a run then
        # says nothing about its fields, exactly as every run did before the
        # claims were ingested.
        self._retrieve = retrieve
        # Where a value comes from when nobody typed one. `None` is a
        # deployment with no connector, and a run with missing values then
        # refuses exactly as it always did.
        self._gather = gather
        # What names a message when a run that came up short asks for what it
        # could not find. `None` is a deployment that has not wired it: the run
        # still stops with its sentence, and nobody is asked.
        self._ids = ids
        self._channel = channel
        # `Asker | None` rather than through `asker_or_refuse` in the container,
        # for `ReadChat`'s reason: a factory that raised would make the factory
        # itself unbuildable, and a deployment with no key would fail at
        # construction instead of at the one call that needs a model.
        self._asker = asker
        self._plan_model = plan_model
        self._rescue_model = rescue_model
        self._clock = clock
        self._cap_usd = cap_usd
        self._stops = stops
        self._approvals = approvals
        self._verified_writes = verified_writes

    async def execute(
        self,
        ctx: RequestContext,
        *,
        workflow_id: str,
        device_id: DeviceId,
        values: Mapping[str, str],
        live: bool,
        allow_focus: bool,
        watched: bool = False,
        from_step: int = 0,
        matched: int | None = None,
        items: Sequence[Mapping[str, str]] = (),
        run_id: str | None = None,
        conversation: tuple[str, str] = ("", ""),
        undoes_run: str = "",
    ) -> WorkflowRun:
        """The claimed row, or the refusal that stopped it being claimed.

        `undoes_run` is the run this one takes back, where a press on a result
        card started it. Refused where that run has already been taken back by
        a run that held: an undo pressed twice is a second delete addressed to
        a record the first one removed, and the warehouse's answer to that is
        nobody's idea of a good surprise.

        `conversation` is the outside thread this run answers to, where it came
        from one -- a request read out of somebody's mail. A run that comes up
        short can then be found again by a reply to that mail, which is the one
        address the panel does not have: the person who knows the missing value
        is usually whoever sent the request, and they are not sitting in front
        of this. See `domain/execution/waiting.py`.
        """
        # Before the session is opened: neither refusal needs a database, and a
        # 503 that first took a connection is a 503 that made the outage
        # slightly worse.
        asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap_usd)
            if why is not None:
                raise OverCap(why)
            if device_id not in self._channel.online(ctx.tenant_id):
                raise Conflict(f"{device_id.value} is not connected")
            busy = await uow.workflow_runs.in_flight(ctx.tenant_id, device_id)
            if busy is not None:
                raise Conflict(already_running(device_id.value, busy))
            # After both, so a workflow_id naming nothing does not answer a
            # person whose real problem is a browser that went away.
            workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)
            # Trimmed, and a value that is blank once trimmed is no value:
            # `required` on the page passes a space, and a job run with " " as
            # its client code is a job run with somebody else's. Dropped rather
            # than refused here so the check below sees it as the absent value
            # it is.
            given = {name: value.strip() for name, value in values.items() if value.strip()}
            # The things this job is to be done for, trimmed the same way and
            # with the run's own values under each. A job with no repeat is
            # handed none of them: performing its steps once per thing would do
            # the whole job three times over, which is not what "add these
            # three" means for a job that adds one thing per run.
            things = (
                [
                    {name: value.strip() for name, value in item.items() if value.strip()}
                    for item in items
                ]
                if workflow.repeat is not None
                else []
            )
            # Every parameter the workflow declares must arrive with one. The
            # planner falls back to the value the recording happened to contain
            # when a step has none -- right for a step nobody parameterised, and
            # for a declared parameter left blank it would quietly perform the
            # job with somebody else's client code. Named, never echoed.
            # Every declared parameter must arrive for every thing this run
            # will do. With no things that is the run's own values, as it
            # always was; with three, a parameter two of them named and the
            # third did not is a run that would perform the third with
            # somebody else's code.
            supplied = [{**given, **thing} for thing in things] or [given]
            absent = sorted(
                str(declared["name"])
                for declared in workflow.parameters
                if declared.get("name")
                and any(str(declared["name"]) not in one for one in supplied)
            )
            # Refused only where nothing could go and find them.
            #
            # A person pressing start with a field empty should be told, and
            # that is what this has always done. A deployment that can read the
            # operator's mailbox has a second answer: the run goes and looks,
            # and refuses at the step if the mailbox does not hold it either.
            # Held here rather than downstream so the refusal still arrives at
            # the press, in front of the person who can fix it, for every
            # deployment that cannot gather.
            #
            # A list is a different matter and keeps the old rule whatever is
            # configured: "add these three" where the third names no code is a
            # run that would perform it with somebody else's, and a gather
            # cannot tell which of three rows a mailbox meant.
            # A parameter somebody TYPED blank is refused whatever else is
            # configured. `given` strips an empty value out, so by here " " and
            # "never mentioned" look identical -- and they are not the same
            # fact. A person who typed a space has said something, and reading
            # their mailbox instead would overrule them; a person who said
            # nothing has left the question open for somebody to answer.
            blank = sorted(
                name
                for one in ([values, *items] if workflow.repeat is not None else [values])
                for name, value in one.items()
                if not value.strip() and any(d.get("name") == name for d in workflow.parameters)
            )
            if blank:
                raise RunRefused(f"this job needs a value for: {', '.join(blank)}")
            # Refused only where nothing could go and find them.
            #
            # A person pressing start with a field absent should be told, and
            # that is what this has always done. A deployment that can read the
            # operator's mailbox has a second answer: the run goes and looks,
            # and refuses at the step if the mailbox does not hold it either.
            # Held here rather than downstream so the refusal still arrives at
            # the press, in front of the person who can fix it, for every
            # deployment that cannot gather.
            #
            # A list keeps the old rule whatever is configured: "add these
            # three" where the third names no code is a run that would perform
            # it with somebody else's, and a gather cannot tell which of three
            # rows a mailbox meant.
            if absent and (self._gather is None or things):
                raise RunRefused(f"this job needs a value for: {', '.join(absent)}")
            if not workflow.steps:
                raise RunRefused("this job has no steps")
            # What a browser matched is GESTURES, and what this field means is
            # STEPS. A shape entry is one cited gesture, so a step of four
            # gestures is four entries, and `recognise.match` answers with how
            # many entries the tail matched -- 19 and 6 on this deployment's own
            # job. The extension sent that straight in as `from_step` and every
            # step under it was recorded done-by-the-operator and never
            # performed: at k=5 on a six-step job, the step that types the code
            # was skipped and the run went on to the description. Over the step
            # count it was refused outright, which is the same mistake wearing
            # the more obvious face.
            #
            # Converted here, where the evidence is, rather than asked of a
            # browser that has the shape but not the steps behind it.
            cited = await uow.gestures.gestures_for(
                ctx.tenant_id, ids=tuple(sorted(cited_ids(workflow)))
            )
            by_id = {gesture.id: gesture for gesture in cited}
            if matched is not None:
                from_step = resumes_at(workflow, by_id, matched)
            # A bool is not a step number, and `isinstance(True, int)` is why it
            # has to be said. `StartWorkflowRunRequest` refuses `true` at the
            # wire, where the coercion it would otherwise survive happens; this
            # is the same rule for a caller that is not a request body.
            #
            # The bound is the job's own highest order and not `len(steps) - 1`:
            # a model numbers its own steps and keeps that numbering, so a job
            # whose steps run 1..6 has a last step nothing could resume at while
            # this counted positions.
            last = max(step.order for step in workflow.steps)
            if isinstance(from_step, bool) or not 0 <= from_step <= last:
                raise RunRefused(f"from_step must be a step of this job (0..{last})")
            # After `from_step`, because which steps have to be performable is
            # what the press just decided. The runner asks this same question
            # of one step at a time, mid-run, once a browser is open and the
            # earlier steps are already sent -- so a job whose evidence has
            # gone is one an operator presses Yes on and watches stop half way.
            # It is a stored row going bad rather than a bad row being stored:
            # the workflow outlives the gestures it cites, and no check at mine
            # time can see that coming.
            # An undo already taken. Refused here rather than reported by the
            # card, because the card is one browser's copy and a second window
            # holds another -- and what two presses buy is a second delete
            # addressed to a record the first one removed.
            #
            # Only against a run that HELD. One that failed left the record
            # where it was, and refusing a second attempt because the first did
            # not work is refusing the one attempt that might.
            if undoes_run.strip():
                already = await uow.workflow_runs.taken_back_by(ctx.tenant_id, undoes_run.strip())
                if already is not None:
                    raise RunRefused(f"{undoes_run.strip()} was already taken back by {already}")
            undoable = unperformable(workflow, by_id, from_step=from_step)
            if undoable is not None:
                raise RunRefused(
                    f"step {undoable.order} has no evidence a browser can act on: {undoable.says}"
                )
            run = WorkflowRun(
                id=run_id or new_run_id(),
                tenant=ctx.tenant_id.value,
                workflow_id=workflow.id,
                device_id=device_id.value,
                values=given,
                started_by=ctx.principal_id.value,
                live=live,
                allow_focus=allow_focus,
                # Whether somebody is standing in front of it. A press in an open
                # panel means "show me"; a trigger at three in the morning means
                # "just do it". See `WorkflowRun.watched`.
                watched=watched,
                started_at=now.isoformat(),
                from_step=from_step,
                items=things,
                # Recorded at the start rather than at the stop, because the
                # stop is not the only thing that can want it and a run that
                # crashed still came from somewhere. Cleared below where the
                # run ends with nothing outstanding: a finished job is not
                # waiting to hear anything.
                awaiting=as_said(waiting_on(*conversation, now=now)),
                # The run this one takes back, where it is an undo of one. An
                # id and never a status: whether it worked is this run's own
                # outcome, read where every other outcome is read.
                undoes_run=undoes_run.strip() or None,
            )
            # Raises `Conflict` -- the same one the read above gives, in the
            # same words -- where the unique partial index refuses a second
            # running run for this browser. Nothing is caught here: it is
            # already the refusal this door means, and translating it twice is
            # how the two sentences would drift apart.
            await uow.workflow_runs.save(run)
            # Committed before the caller is answered and before anything is
            # spawned. A `running` row that only exists inside the task's first
            # slice is a row a second press cannot see.
            await uow.commit()
            return run

    async def _secret_for(self, key: str) -> str | None:
        """One password, at the moment a step types it.

        A method rather than the vault handed down, so `run_workflow` and
        `plan_step` never learn what a vault is: what they take is "given a
        key, give me a value or nothing".

        A vault that cannot be reached answers `None` and not an exception. The
        step then refuses with the key it wanted, which is the same sentence an
        operator gets when they never stored one -- and both are true from
        where they are standing. Raising here would fail the whole run on a
        step that could have said what was missing.
        """
        if self._vault is None:
            return None
        try:
            return await self._vault.get(key)
        except VaultUnavailable:
            return None

    async def perform(self, ctx: RequestContext, run: WorkflowRun) -> None:
        """Drive a run whose caller has already been answered.

        Nobody is awaiting this, so nobody would see it raise. A refusal or a
        broken session mid-run would leave the row saying `running` for as long
        as the process lived -- swept only by `fail_orphans` at the next start,
        which is a restart away and not a moment away -- and the console
        watching it would count the seconds forever.

        `run_workflow` closes its own row on the way out of its `finally`, and
        this is the backstop for the two cases that never reach it: what is
        raised before it starts, and a failure that took the session down with
        it so its own save could not land either.

        Everything the run is performed with comes off the claimed row rather
        than off this frame, so there is one answer to "what is this run doing"
        and not two that can drift -- `run_workflow` reads the same row back and
        refuses the pair if they disagree.

        **Four of these arguments are dead on this path, and they are passed
        anyway.** `run_workflow.py:343` does `values, live, allow_focus =
        run.values, run.live, run.allow_focus` off the row it read back, and
        `started_by` is read only on the branch where no row was found -- which
        `perform` can never take, because it always names one. So none of those
        four decides anything here, and a reader must not spend a minute
        believing otherwise: they are not controls, they are what the callee's
        signature requires, and the row is the authority downstream.

        They are the ROW's values rather than a repeat of the request's, and
        that is the part worth keeping. It costs nothing, it is what the one
        path that would read them should read, and if `run_workflow` ever
        stopped finding the row -- swept, deleted, a different tenant -- the
        arguments it fell back on would still describe this run instead of
        whatever a route happened to be holding.

        `plan_model` and `rescue_model` are not in that list. They are read on
        every step and nothing else supplies them, so swapping them plans every
        step on the rescue model forever -- which is why they are asserted at
        this call rather than only on the built object.
        """
        try:
            asker = asker_or_refuse(self._asker)
            async with self._uow as uow:
                workflow = await uow.workflows.get(ctx.tenant_id, run.workflow_id)
                title = workflow.title
                done = await run_workflow(
                    uow,
                    workflow,
                    # The same cap the press was judged against, so the run can
                    # keep asking. Read once and never again, one press on a
                    # long list could spend the rest of the tenant's day.
                    cap_usd=self._cap_usd,
                    tenant_id=ctx.tenant_id,
                    values=run.values,
                    channel=self._channel,
                    device_id=DeviceId(run.device_id),
                    asker=asker,
                    plan_model=self._plan_model,
                    rescue_model=self._rescue_model,
                    live=run.live,
                    allow_focus=run.allow_focus,
                    watched=run.watched,
                    started_by=run.started_by,
                    stops=self._stops,
                    approvals=self._approvals,
                    run_id=run.id,
                    from_step=run.from_step,
                    items=run.items,
                    verified_writes=self._verified_writes,
                    secret_for=self._secret_for,
                    known_fields=None if self._retrieve is None else self._known_fields(ctx),
                    gather_values=(
                        None
                        if self._gather is None
                        else self._gathering(ctx, workflow.title, seen_values(workflow))
                    ),
                )
        except Exception as error:
            logger.exception("a run in an operator's browser could not be finished")
            await self._close(ctx, run.id, f"{type(error).__name__}: {error}")
        else:
            # Outside the unit of work, because asking opens its own: the run
            # is over and its row is written, and a question that shared the
            # run's transaction would be a question that vanishes with it.
            await self._settle_the_wait(ctx, done)
            await self._ask_for_values(ctx, done, title)

    async def _settle_the_wait(self, ctx: RequestContext, run: WorkflowRun) -> None:
        """A run that came out whole is not waiting to hear anything.

        The address was written at the start, before anybody knew how the run
        would end, so the end is where it is either kept or let go. Kept is the
        interesting half and needs no writing: the row already says which
        conversation this run answers to, and a reply arriving there is the
        answer to a question that is still open.

        Let go is this. A job that found everything and wrote its record has
        nothing outstanding, and a mail arriving on that thread a week later --
        "thanks", or a fresh request -- must not be read as an answer to it.
        Cleared rather than left to expire, because seven days of a finished
        run claiming every reply to its own thread is seven days of the next
        request being swallowed by the last one.
        """
        if not run.awaiting:
            return
        async with self._uow as uow:
            # The committed row and not the copy in hand, which is what
            # `run_workflow` handed back and may be a step behind what it
            # saved. Whether anything is still outstanding is a question about
            # the row a reply would find, so it is asked of that row.
            saved = await uow.workflow_runs.get(ctx.tenant_id, run.id)
            if saved is None or saved.needs:
                return
            saved.awaiting = None
            await uow.workflow_runs.save(saved)
            # And committed. Without this the clear is rolled back when the
            # unit of work exits, and the row goes on naming a conversation it
            # is no longer waiting on -- for seven days, swallowing every reply
            # to that thread as an answer to a job that finished.
            #
            # The unit tests passed: `FakeUnitOfWork` does not require a commit
            # to have happened, so it agreed with the code rather than with the
            # store. Measured on the deployment 2026-09-18 -- a run held, needs
            # empty, `awaiting` still set.
            await uow.commit()

    async def _ask_for_values(self, ctx: RequestContext, run: WorkflowRun, title: str) -> None:
        """Turn a run that came up short into a question somebody can answer.

        The alternative, and what this replaces, is a row reading "nobody gave
        a value for Customer Type, and your mail does not say either" -- true,
        and the end of it. The operator had already said yes; what they get for
        it is a dead card and a job to start again from the beginning.

        One question, for one value, in their own conversation. What is
        established so far rides on the decision, so the answer is readable off
        the thread rather than out of a session nothing survives, and the last
        answer starts the job on the yes they already gave.

        `ids` is optional for the same reason the rest of this object's
        collaborators are: a deployment that has not wired it runs exactly as
        it did before, stopping with the sentence and asking nobody.
        """
        if not run.needs or self._ids is None:
            return
        # What the boxes behind these names will hold, where a run has found
        # out. A question that asks for a value again without saying why the
        # last one would not do gets the same value back -- the person has no
        # way to know the field stops at 28 characters, because the browser
        # never said so and neither did we.
        async with self._uow as uow:
            learnt = await uow.workflows.learned_for(run.workflow_id)
            workflow = await uow.workflows.get(ctx.tenant_id, run.workflow_id)
            # Which of this job's steps wrote, so the resumed one can be told
            # where it may safely start over. Read here rather than inferred
            # from the run's own record: what a STEP does is a fact about the
            # job and its evidence, and a run that stopped early performed too
            # few of them to say.
            cited = (
                await uow.gestures.gestures_for(
                    ctx.tenant_id,
                    ids=tuple(sorted({one for step in workflow.steps for one in step.cites})),
                )
                if workflow
                else ()
            )
        by_id = {gesture.id: gesture for gesture in cited}
        steps = workflow.steps if workflow else []
        limits = limits_for(
            steps,
            learnt,
            # And what the vendor's own dictionary says, for the fields no run
            # has hit yet. A job whose first request is too long would
            # otherwise learn that by sending it.
            await declared_limits(
                self._uow,
                ctx.tenant_id,
                names_of(workflow) if workflow else [],
                await screen_for(self._uow, ctx.tenant_id, workflow) if workflow else "",
            ),
        )
        pending = Pending(
            workflow_id=run.workflow_id,
            title=title,
            values=dict(run.values),
            missing=tuple(run.needs),
            items=tuple(dict(one) for one in run.items),
            watched=run.watched,
            limits=limits,
            # Where the run the answer starts has to begin.
            #
            # Not the step that stopped, which is where this started: that one
            # re-types a field into whatever is on the screen a minute later,
            # and the operator may well have navigated off the half-filled form
            # by then. So it goes back to the beginning of the block that BUILT
            # that screen -- pressing Add, opening the tab, the typing before
            # it -- and rebuilds the form the value is going into.
            #
            # `begins_again_at` partitions at the last write for the reason
            # everything here does: a write that may have landed is not a step
            # to try again, and nothing it returns is on the far side of one.
            from_step=(
                begins_again_at(workflow, by_id, stopped_at=run.steps[-1].order)
                if workflow and run.steps
                else 0
            ),
        )
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            # The person this run was for, not whoever is at the door: a
            # question in the wrong conversation is worse than none.
            for_operator=PrincipalId(run.started_by) if run.started_by else ctx.principal_id,
            text=_asking(run.needs, title, limits) + question(pending),
            # A question, not an announcement: `pending_job` reads back what the
            # ASSISTANT last decided, so this is what makes the answer findable.
            speaker=Speaker.ASSISTANT,
            decision={
                "kind": NEEDS,
                "workflow_id": pending.workflow_id,
                "title": pending.title,
                "values": dict(pending.values),
                "missing": list(pending.missing),
                "items": [dict(one) for one in pending.items],
                # Which way the job will be done when it runs. The person is
                # in the panel answering questions, so they are watching -- but
                # it is carried rather than assumed, because a run started by a
                # trigger that asked and was answered hours later is not.
                "watched": pending.watched,
                "limits": dict(limits),
                "from_step": pending.from_step,
                "from_run": run.id,
            },
        )
        # And whoever sent the request, where there is one and a way to reach
        # them.
        #
        # The question above goes to the operator, which is right and usually
        # enough. It is not enough for the case this whole path was built
        # around: a mail asking for a customer type by description, no code in
        # it, none in the thread, and an operator who did not write the request
        # and has no way of knowing. The person who does is whoever sent it.
        #
        # Drafted, never sent. What leaves here is words in the operator's own
        # conversation with a press under them, and the press is the only thing
        # that reaches a mailbox.
        #
        # Nothing here can stop the question that has already been asked: a
        # deployment with no connector, a thread that cannot be read, a run
        # nobody can trace to a request -- all of them mean no draft and none
        # of them means no question.
        if self._asker_drafts is not None:
            try:
                await self._asker_drafts(ctx, run.id, pending)
            except Exception:
                logger.exception("%s could not be drafted a mail about", run.id)

    def _gathering(
        self, ctx: RequestContext, job: str, seen: Mapping[str, frozenset[str]]
    ) -> GatherValues:
        """Bound to this request's own tenant and operator.

        A closure for `_known_fields`' reason -- `run_workflow` has no
        `RequestContext` -- and for one more that matters here: a mailbox is
        reached as ONE person, and the person is the one this run is for.
        """

        async def look(wanted: Sequence[str]) -> Gathered:
            return await self._gather.execute(  # type: ignore[union-attr]
                ctx,
                job=job,
                wanted=wanted,
                seen={name: tuple(sorted(values)) for name, values in seen.items()},
            )

        return look

    def _known_fields(self, ctx: RequestContext) -> KnownFields:
        """What the dictionary says about these body keys, by key.

        Bound to the request's own tenant, which is the whole of why this is a
        closure rather than the retriever handed down: `Retrieve` is
        tenant-scoped and `run_workflow` has no `RequestContext` to scope it
        with.

        `kinds=(FIELD,)` and the keys as terms, because `search` matches terms
        against a claim's title and key. The body key IS the claim's key --
        `customerType` is stored under `customerType` -- so this is a lookup
        rather than a search, and nothing here asks a vector store a question
        it cannot answer without embeddings. Measured on QA 2026-09-16: 404
        field claims, 0 embeddings, and the lookup answers.

        **And the FORM, which disagrees with the dictionary and is right.** The
        dictionary is what the vendor DOCUMENTS; a form model was captured from
        the real form an operator uses, which is why its claims are `OBSERVED`
        and the dictionary's are `ASSERTED`. Measured on QA 2026-09-16: the
        dictionary says `customerType` holds 60 characters, the Customer Types
        create form says 4, and the ledger's own gotcha -- somebody's
        measurement -- says `csttyp truncates at 4 chars`. Two of the three
        agree, and the card was reading the third: a request for `NEWSROTEST`
        would have been sent, truncated to `NEWS`, answered 201, and read back
        as the record the system actually made, with nothing to say so.

        So the form's numbers win where it has one, and what it says is
        REQUIRED comes back too -- a field the form marks required and the
        write does not carry is the other fact worth a line.
        """

        async def look(
            keys: tuple[str, ...], screen: str = ""
        ) -> Mapping[str, Mapping[str, object]]:
            if not keys:
                return {}
            found = await self._retrieve.execute(  # type: ignore[union-attr]
                ctx,
                Question(text=" ".join(keys), kinds=(EntryKind.FIELD,), limit=len(keys) * 4),
            )
            # Keyed by the claim's own key and only where it is one of the body
            # keys asked about. `search` is an OR over the terms, so a lookup
            # for two fields answers with claims for either -- and a claim for
            # a field this write does not fill must not be read as one it does.
            known: dict[str, dict[str, object]] = {
                entry.key: dict(entry.body)
                for entry in found
                if entry.key in keys and isinstance(entry.body, Mapping)
            }
            for slot, seen in (await self._forms(ctx, screen)).items():
                known.setdefault(slot, {}).update(seen)
            return known

        return look

    async def _forms(self, ctx: RequestContext, screen: str) -> Mapping[str, Mapping[str, object]]:
        """What the real create form for THIS screen says about its fields.

        By the screen and never by the body key. A key does not name a form:
        measured on QA 2026-09-16, `customerType` is posted by two of them --
        Customer Types and Existing Customers -- so a lookup by key would lend
        one screen's required fields to another screen's write and say that a
        customer number nobody asked for was missing.

        A form claim's key IS its route, `#wm.config/wm.config.partners.customers.types////`,
        and the step's own screen is the url the demonstrations agree on. One
        contains the other, which is the whole join.

        Every form, once, rather than a search: `search` matches terms against
        a claim's title and key, and neither carries the body keys -- a lookup
        for `customerType` finds nothing at all. Measured: 88 forms, 756
        fields, 0.09s for the lot, which is cheaper than being wrong.

        Silent where the screen matches no form. A write whose screen nothing
        documents is one the dictionary still describes field by field, and a
        guess between two forms is how this would start inventing missing
        fields.
        """
        if not screen.strip():
            return {}
        found = await self._retrieve.execute(  # type: ignore[union-attr]
            ctx, Question(text="", kinds=(EntryKind.FORM,), limit=K_EVERY_FORM)
        )
        seen: dict[str, dict[str, object]] = {}
        for entry in found:
            route = (entry.key or "").rstrip("/")
            if not route or route not in screen:
                continue
            fields = (entry.body or {}).get("fields")
            if not isinstance(fields, list):
                continue
            for one in fields:
                if not isinstance(one, Mapping):
                    continue
                slot = one.get("field")
                if not isinstance(slot, str):
                    continue
                said: dict[str, object] = {"observed": True}
                if isinstance(one.get("label"), str):
                    said["labels"] = [one["label"]]
                if isinstance(one.get("maxLength"), int) and not isinstance(
                    one.get("maxLength"), bool
                ):
                    said["max_length"] = one["maxLength"]
                if one.get("required") is True:
                    said["required"] = True
                seen.setdefault(slot, {}).update(said)
        return seen

    async def _close(self, ctx: RequestContext, run_id: str, reason: str) -> None:
        """Mark a row nobody is driving any more, on a session of its own.

        The same shape as the orphan sweep -- the reason lands on the last step,
        or on a new one where the run never reached one -- because a reader has
        one place to look for why a run stopped. Left alone where the row is
        already finished: `run_workflow` may well have closed it on its way out,
        and a second close would overwrite the verdict it wrote with this one.
        """
        try:
            async with self._uow as uow:
                saved = await uow.workflow_runs.get(ctx.tenant_id, run_id)
                if saved is None or saved.outcome != "running":
                    return
                if saved.steps:
                    last = saved.steps[-1]
                    last.verdict, last.verdict_by, last.reason = "failed", "none", reason
                else:
                    saved.steps.append(
                        RunStep(
                            order=0,
                            says="",
                            verdict="failed",
                            verdict_by="none",
                            reason=reason,
                        )
                    )
                saved.outcome = "failed"
                saved.finished_at = self._clock.now().isoformat()
                await uow.workflow_runs.save(saved)
                await uow.commit()
        except Exception:
            logger.exception("and its row could not be closed either")


class ListWorkflowRuns:
    """The most recent runs, newest first, as the rig listed them.

    Ported from `runs` in `new_agent_arch/src/rig/api.py:1152`.

    **Newest first, and that is deliberately not `for_workflow`'s order.**
    `for_workflow` is oldest first because `proofs` reads a job's writes
    forward through time. This is the list a person opens, and what they are
    looking for is what happened last -- which is also the shape the extension
    and the console will be written against. The port used to justify its
    ascending order by citing the rig, whose list says the opposite; the
    citation is corrected and the rig's order lives here, under `recent`.

    **`awaiting=true` is the supervisor's queue**, narrowed to the runs parked
    on a write nobody has let out yet -- from any browser, not the one the run
    is in. Narrowed by the ids `awaiting` gives and then capped, in that order:
    a cap applied first would answer "nothing is waiting" out of the busiest
    tenant, which is the one that needs the queue.

    **`limit` caps the rows and not that set, and this is the one unbounded
    thing on this read.** Every parked run id of the tenant is interpolated
    into the `IN (...)`. What bounds it is migration 0043 rather than a number
    here: one running run per browser, and only a running run can be parked, so
    the set is at most one id per browser the tenant has. A bound in code would
    have to be a cap on `awaiting` itself, which would drop parked runs out of
    the queue silently -- the thing the ruling below exists to refuse.

    The whole row comes back rather than the rig's one line each, so every
    parked step is already on the wire. The rig reported the deepest parked
    step of each run and this reports all of them, `ord` ascending -- plan 4b's
    ruling, recorded here and on `WorkflowRunRepository.awaiting`: anyone may
    answer a parked run, and a queue that hides all but the deepest step hides
    work from the person who could clear it.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        workflow_id: str | None,
        limit: int,
        awaiting: bool,
    ) -> tuple[WorkflowRun, ...]:
        # No defaults. The route passes all three, so a default here is
        # unreachable -- and a `limit` default would be a second copy of the
        # page size, in the one of the two places that never reaches
        # `openapi.json`.

        async with self._uow as uow:
            parked: frozenset[str] | None = None
            if awaiting:
                # No early return on an empty queue, which is what the rig
                # did. Its `id IN ()` would have been a syntax error with no
                # ids to interpolate; here an empty set is a filter that
                # matches nothing, said once in `recent` and kept by the
                # contract suite. A branch here would be a second statement of
                # the same rule that no test can tell from its absence -- it
                # was written, and the mutation that deleted it passed 59
                # tests.
                parked = frozenset(
                    run_id for run_id, _, _ in await uow.workflow_runs.awaiting(ctx.tenant_id)
                )
            return await uow.workflow_runs.recent(
                ctx.tenant_id, limit=limit, workflow_id=workflow_id, ids=parked
            )


class GetWorkflowRun:
    """One run, whole, or the 404 that will not say which kind of missing.

    Ported from `read_run` in `new_agent_arch/src/rig/api.py:1217`.

    The repository answers `None` rather than raising -- "every caller answers
    404 itself" -- and this is that caller. A run of another tenant takes the
    same path as one that never existed, because a 403 confirms the id exists:
    run ids are unguessable and the answer to "is this yours" must not differ
    from the answer to "does this exist".

    The rig also hung `approved_at` and `approved_by` off each step out of the
    approvals table. Not here: `/v1/audit` already serves the approvals of
    every run of the tenant, and a second place that says when a write was let
    out is a second place for the two to disagree.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, run_id: str) -> WorkflowRun:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
            if run is None:
                raise NotFound("no such run")
            return run

    async def undo_for(self, ctx: RequestContext, run: WorkflowRun) -> tuple[str, str, str] | None:
        """Which of this tenant's jobs takes back what this run made, if any.

        Asked only of a run that is over and made something: a run still going
        may make more, and a run that made nothing has nothing to take back --
        and this is a read of every job's evidence, on a door the panel polls.

        Answers WHAT and never starts anything: the job that takes it back, and
        the one record it would address. The second half is what this said it
        lacked -- *a mapping this has no evidence for, and a wrong mapping
        deletes the wrong record* -- and the evidence arrived with `made_by`: a
        step that created something records what the warehouse called it.

        `addresses` refuses anything but one record named one way, for the
        reason that sentence gives. A run that made two would need two deletes,
        and an undo that takes back half of what a run did is worse than none.
        """
        if run.outcome == "running" or not any(step.made for step in run.steps):
            return None
        async with self._uow as uow:
            known = list(await uow.workflows.known(ctx.tenant_id))
            made = next((one for one in known if one.id == run.workflow_id), None)
            if made is None:
                return None
            gestures = {
                gesture.id: gesture for gesture in await uow.gestures.gestures_for(ctx.tenant_id)
            }
            takes_back = undoes(made, gestures, known)
            if takes_back is None:
                return None
            # And which record. Without it the panel can name a job and not
            # press it, which is where this has stood since it was written.
            #
            # `identifies` reads the undo's own delete for the field it
            # addresses a record by -- the key in its body whose value is the
            # segment in its path. Measured on the deployment 2026-09-19: the
            # pair was found and not one of ninety-two runs could offer the
            # button, because each run's `made` carries the two slots the
            # read-back confirmed and a record named two ways is a record this
            # cannot name. `None` where the delete does not say, which is the
            # old rule exactly.
            takes_it_by = identifies(next(one for one in known if one.id == takes_back), gestures)
            which = addresses([step.made for step in run.steps if step.made], takes_it_by)
            if which is None:
                return None
            field, names = which
            return takes_back, field, names


class AbortWorkflowRun:
    """Ask a run of a mined job, in somebody's own browser, to stop.

    Ported from `abort_run` in `new_agent_arch/src/rig/api.py:1237`, and it
    closes phase 4a's carried item 1: `run_workflow` has asked `Stops` between
    every step since it was written, and nothing outside this process could set
    it.

    **A sibling of `StopRun`, not a branch on it.** That one is the SKILL run's
    half and resolves through `uow.runs` on a `RunId`; this resolves through
    `uow.workflow_runs` on a plain `str`. `new_run_id` says why the two id
    spaces stay apart: "a string that round-trips through the wrong repository
    will be looked up, found missing, and read as a run that does not exist
    rather than as a type error". Its two refusals are copied because they are
    right for both, and both the `CannotStop` class and the sentence of the
    second one are imported rather than redeclared, so neither the `code` nor
    the words a console renders can drift into two.

    **The flag first, then the release**, which is the rig's order. A run parked
    on a person is not between steps and would sit out `K_APPROVAL_WAIT_S`
    before it noticed the flag; releasing the wait lets the loop see it now. The
    release is not a yes -- `run_workflow` asks `Stops` on the way out of
    `wait_for` and aborts rather than writing.

    Written in that order and not testable in it: nothing is awaited between the
    two lines, so on one event loop the woken task cannot be scheduled between
    them and the reverse order would behave identically today. It is written the
    safe way round because the day something is awaited in between is the day it
    stops being identical, and that day will not come with a test attached.

    **Nothing here writes the row.** The task driving the browser is the only
    thing that knows whether the gesture it was mid-way through landed, and it
    closes the run on its way out. A route that marked the row `aborted` would
    race the task it just interrupted.

    Nothing here talks to the browser either. The loop sends `kind="abort"` the
    moment it reads the flag, and it now does so on BOTH of its readings -- the
    one between steps and the one on the way out of the approval wait, which
    had none until this route made that path reachable. So the rig's own
    best-effort send is made unnecessary rather than dropped, and it stays in
    the loop rather than moving here because the loop is what holds the socket
    and knows the run is really over.
    """

    def __init__(self, uow: UnitOfWork, stops: Stops, approvals: Approvals) -> None:
        self._uow = uow
        self._stops = stops
        self._approvals = approvals

    async def execute(self, ctx: RequestContext, *, run_id: str) -> WorkflowRun:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
        # A run of another tenant takes the same path as one that never
        # existed, for `GetWorkflowRun`'s reason: a 403 confirms the id exists.
        if run is None:
            raise NotFound("no such run")
        if run.outcome != "running":
            raise CannotStop(f"that run already {run.outcome}")
        # `WorkflowRun.device_id` is a non-null `str` where the skill run's is
        # `DeviceId | None`, so the empty string is what "no browser" looks like
        # here. Kept for `StopRun`'s reason rather than because this system
        # writes such a row: what a stop control must never do is answer
        # "stopping" for a run nothing in this process is driving.
        if not run.device_id:
            raise CannotStop(NOT_IN_A_BROWSER_HERE)
        self._stops.ask(run.id)
        self._approvals.approve(run.id)
        # ponytail: in-process only. A run and the socket it drives live in one
        # worker, so stopping must land there too -- sticky-route by device_id
        # if this is ever run with more than one.
        return run


class NotDrivingThisRun(DomainError):
    """This browser is not the one driving the run it is trying to release.

    403 and not 404: the caller holds a tenant credential that was accepted and
    a browser secret that checked out, so this is not an enumeration channel --
    they have already been told the run exists by every read on this router.
    `tenant_only` refuses in the same words for the same reason.

    A `DomainError` with its own entry in `errors._STATUS_BY_ERROR`, rather
    than a subclass of `call_run_wrong.NotYours` -- which is the nearest thing
    to it and refuses the same shape of caller. That one is about a PERSON and
    this is about a BROWSER: "that is another browser's run" and "that is
    another person's run" are two different sentences to whoever is holding the
    screen, and its own `code` is what keeps them two on the wire.

    Not a subclass for a second reason, now historical: when this was written
    neither `NotYours` had a handler registered, so both reached a caller as a
    500 and inheriting would have inherited it. `0302584` fixed that door.
    """

    code = "not_driving_this_run"


class ApproveWorkflowStep:
    """A person saw the write the panel showed and said go.

    Ported from `approve_run` in `new_agent_arch/src/rig/api.py:1270`, and it
    is the precondition on anything ever being pressed live: without it a run
    that parks on a person sits out `K_APPROVAL_WAIT_S` and fails for want of
    an answer, however hard anybody taps.

    **Two halves, and the durable one goes first.** The row says who let the
    write out; the event is what the parked `run_workflow` task is waiting on.
    The rig fires the event and writes the row after (`api.py:1284` then
    `:1305`) and this is deliberately the other way round. The asymmetry is not
    symmetric: event first and a failed write is a live warehouse write with no
    record of who authorised it, which `routers/runs.py` has already ruled
    against -- "the audit trail on a warehouse write is worth more than that";
    row first and a failed release is a run that stays parked, times out and
    aborts, and an operator who taps again. A lost tap is recoverable.

    **The rig's own order was safe where the rig ran, and that is exactly why
    it must not be copied here.** An earlier revision of this docstring claimed
    it raced the task it woke; it does not, and the claim was checked and
    withdrawn. `Approvals.approve` there is a sync `event.set()`
    (`rig/runner.py:90-94`), `store.query` and `store.execute` are sync sqlite
    (`rig/store.py:447-453`), and there is no `await` anywhere between the two
    -- so the woken task cannot be scheduled in between, and the rig's read of
    which step to record always ran before the task could touch it.

    What the rig had, then, was an insert that could not be preceded by a
    yield and a store with no commit to fail. This has both: `uow.commit()` is
    an awaited round trip to Postgres that can raise, and the release is a
    separate act after it. The asymmetry therefore bites HARDER here than it
    ever did there -- the failure the rig's shape merely permitted in theory is
    one this shape can actually produce -- which is the whole reason the order
    is inverted rather than ported.

    **The order is what the 409 costs.** The rig got "nothing is awaiting" from
    `Approvals.approve` returning False, which is not available before the
    event is fired. This asks the run's own steps instead, with the predicate
    `WorkflowRunRepository.awaiting` already carries -- a `running` run with a
    step whose verdict is `awaiting` -- so the queue and the tap agree about
    what "parked" means. The two are not identical and the difference falls the
    safe way: `run_workflow` registers on `Approvals` BEFORE it saves the
    parked step, so in the window between them the event exists and the row
    does not. The rig would have released the wait there and written no
    authorisation; this answers 409 and the operator taps again a moment later.

    **The deepest parked step is the one a tap authorises**, `ORDER BY ord DESC
    LIMIT 1`, and that is deliberately NOT `awaiting`'s rule. That one returns
    every parked step of every run, `ord` ascending, because anyone may answer
    a parked run and a queue hiding all but the deepest hides work from the
    person who could clear it. It answers "what is waiting"; this answers
    "which step does THIS tap let out", and a run is parked at its deepest.

    **`WorkflowRunRepository.approve` is tenant-blind on purpose** -- the run
    id is the only thing the panel has -- and the lookup at the top of this
    method is the whole of what stands between that and a cross-tenant write.
    A run of another tenant takes the same path as one that never existed, for
    `GetWorkflowRun`'s reason: a 403 confirms the id exists.

    **A caller that NAMES a browser answers for the run that browser is
    driving and no other**, checked before anything is written and before the
    event is set. `asking` is the browser that proved itself with
    `X-Device-Secret` beside `?device_id=`, so it can never be a claim -- the
    rig had to rank a token's own device above a `device_id` in the body, and
    here there is no body to rank it against.

    **Say what that is, because the rig's sentence for it promises more.** The
    rig wrote "one compromised browser must not be able to satisfy every other
    browser's human-in-the-loop gate", and neither the rig nor this delivers
    it: a caller who names no browser at all skips the check, and here the
    extension holds the tenant's bearer, so a compromised one can simply omit
    the pair. What this check IS: a browser that identifies itself is bound to
    its own run, so a panel cannot answer for a window it is not driving, and
    an id lifted from one browser's screen buys nothing against another's. What
    it is NOT: a barrier against a caller holding the tenant's credential --
    which already starts, stops and reads every run of the tenant.

    Refusing `asking is None` would close that, and it is deliberately not
    done: `awaiting` and `GET /v1/workflow-runs?awaiting=true` exist so that
    ANYBODY may answer a parked run, across browsers, and the reader they were
    built for is a supervisor's console holding the tenant's credential and no
    extension of its own. A device-only tap would delete the supervisor's
    queue. The row then names no browser rather than one nobody proved, which
    is the honest record of a console tap.

    The return says which step was authorised and whether THIS tap was the one
    that authorised it. The first tap wins: a write rescued to the second rung
    parks at the same step and takes a second tap, and the first authorisation
    is the one in the audit. A second tap is not refused, though -- the run
    really is parked again, and a 409 would leave it sitting out five minutes.
    """

    def __init__(self, uow: UnitOfWork, approvals: Approvals, clock: Clock) -> None:
        self._uow = uow
        self._approvals = approvals
        self._clock = clock

    async def execute(
        self, ctx: RequestContext, *, run_id: str, asking: DeviceId | None
    ) -> tuple[int, bool, bool]:
        """(the step authorised, whether this tap was the one, whether anything woke)."""
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
            if run is None:
                raise NotFound("no such run")
            if asking is not None and run.device_id != asking.value:
                raise NotDrivingThisRun("that run is not the one this browser is driving")
            parked = [step.order for step in run.steps if step.verdict == "awaiting"]
            # `running` beside the verdict, which is `awaiting`'s own second
            # predicate: a step left `awaiting` on a run that was aborted or
            # failed is not waiting on anybody, and a tap on it would record a
            # person letting out a write nothing is holding open.
            if run.outcome != "running" or not parked:
                raise Conflict("nothing is awaiting approval on this run")
            ord_ = max(parked)
            first = await uow.workflow_runs.approve(
                run.id,
                ord_,
                at=self._clock.now().isoformat(),
                device_id=asking.value if asking else None,
            )
            # Committed inside the block and the release outside it, so the row
            # is durable before anything can act on the event. The other order
            # would let a write out on a transaction that then rolled back.
            await uow.commit()
        # Whether anything was waiting is REPORTED and never refused, and the
        # distinction is the whole of this line. Refusing would answer "nothing
        # was awaiting" about a row that exists: the authorisation is committed
        # above, and the person really did say go.
        #
        # But silence is worse. An operator tapped Approve on a real login
        # step, got a 200, and watched the browser sit on the same screen until
        # they gave up -- the process holding that run had restarted, so there
        # was no event to set and nothing to resume. The 200 was true about the
        # authorisation and silent about the only thing they cared about.
        #
        # Two ways it comes back false. The wait timed out: `wait_for` pops its
        # event after `K_APPROVAL_WAIT_S`, so a run can stop waiting between
        # the 409 check above and this line. Or the process that was waiting is
        # gone, which `fail_orphans` cleans up at the next start and cannot
        # reach while this one is live.
        resumed = self._approvals.approve(run.id)
        return ord_, first, resumed
