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
from collections.abc import Mapping, Sequence
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.read_runs import NOT_IN_A_BROWSER_HERE, CannotStop
from sro.application.execution.run_workflow import run_workflow
from sro.application.execution.stops import Stops
from sro.application.intent.spend import over_cap
from sro.application.ports.channel import Channel
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.ports.vault import CredentialVault, VaultUnavailable
from sro.application.shared.refusals import OverCap
from sro.domain.execution.evidence import unperformable
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.workflow_run import (
    RunStep,
    WorkflowRun,
    already_running,
    new_run_id,
)
from sro.domain.shared.errors import Conflict, DomainError, NotFound
from sro.domain.shared.identifiers import DeviceId
from sro.domain.skill.reversals import undoes
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
    ) -> None:
        self._uow = uow
        # Where a password comes from when a step types one. `None` is a
        # deployment with no vault configured: the run still happens, and a
        # step that needs a password refuses with the key it wanted rather
        # than typing a blank into a login form.
        self._vault = vault
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
        from_step: int = 0,
        items: Sequence[Mapping[str, str]] = (),
        run_id: str | None = None,
    ) -> WorkflowRun:
        """The claimed row, or the refusal that stopped it being claimed."""
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
            if absent:
                raise RunRefused(f"this job needs a value for: {', '.join(absent)}")
            if not workflow.steps:
                raise RunRefused("this job has no steps")
            # A bool is not a step number, and `isinstance(True, int)` is why it
            # has to be said. `StartWorkflowRunRequest` refuses `true` at the
            # wire, where the coercion it would otherwise survive happens; this
            # is the same rule for a caller that is not a request body.
            if isinstance(from_step, bool) or not 0 <= from_step < len(workflow.steps):
                raise RunRefused(
                    f"from_step must be a step of this job (0..{len(workflow.steps) - 1})"
                )
            # After `from_step`, because which steps have to be performable is
            # what the press just decided. The runner asks this same question
            # of one step at a time, mid-run, once a browser is open and the
            # earlier steps are already sent -- so a job whose evidence has
            # gone is one an operator presses Yes on and watches stop half way.
            # It is a stored row going bad rather than a bad row being stored:
            # the workflow outlives the gestures it cites, and no check at mine
            # time can see that coming.
            cited = await uow.gestures.gestures_for(
                ctx.tenant_id, ids=tuple(sorted(cited_ids(workflow)))
            )
            undoable = unperformable(
                workflow, {gesture.id: gesture for gesture in cited}, from_step=from_step
            )
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
                started_at=now.isoformat(),
                from_step=from_step,
                items=things,
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
                await run_workflow(
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
                    started_by=run.started_by,
                    stops=self._stops,
                    approvals=self._approvals,
                    run_id=run.id,
                    from_step=run.from_step,
                    items=run.items,
                    verified_writes=self._verified_writes,
                    secret_for=self._secret_for,
                )
        except Exception as error:
            logger.exception("a run in an operator's browser could not be finished")
            await self._close(ctx, run.id, f"{type(error).__name__}: {error}")

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

    async def undo_for(self, ctx: RequestContext, run: WorkflowRun) -> str | None:
        """Which of this tenant's jobs takes back what this run made, if any.

        Asked only of a run that is over and made something: a run still going
        may make more, and a run that made nothing has nothing to take back --
        and this is a read of every job's evidence, on a door the panel polls.

        Answers an id and never starts anything. What a press would have to do
        -- address each created record by whatever the warehouse called it --
        is a mapping this has no evidence for, and a wrong mapping deletes the
        wrong record.
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
            return undoes(made, gestures, known)


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
