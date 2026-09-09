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
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.run_workflow import run_workflow
from sro.application.execution.stops import Stops
from sro.application.intent.spend import over_cap
from sro.application.ports.channel import Channel
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap
from sro.domain.execution.workflow_run import (
    RunStep,
    WorkflowRun,
    already_running,
    new_run_id,
)
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import DeviceId

__all__ = ["RunRefused", "StartWorkflowRun"]

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
    ) -> None:
        self._uow = uow
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
            # Every parameter the workflow declares must arrive with one. The
            # planner falls back to the value the recording happened to contain
            # when a step has none -- right for a step nobody parameterised, and
            # for a declared parameter left blank it would quietly perform the
            # job with somebody else's client code. Named, never echoed.
            absent = sorted(
                str(declared["name"])
                for declared in workflow.parameters
                if declared.get("name") and str(declared["name"]) not in given
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
