"""Every workflow a tenant has, and the evidence any one of them cites.

Ported from `new_agent_arch/src/rig/api.py:812` (the listing) and `:904` (the
evidence). Two reads in one module because they are the two halves of one
door -- a listing, and the evidence underneath a row of it -- and because
neither writes. `serve_shapes` keeps that same promise for the extension's
list; this is the console's, which is a different question about the same
rows: not "what can be matched against a live tail" but "what has become of
this job".

**The listing's history is narrowed from the rig, deliberately.** There,
`history` answered seven things per workflow and cost five queries to do it,
one of them per-workflow `counsel`. Three are ported -- the run tally, the
weak-locator count and whether the job's writes go unasked -- and each is here
because nothing else this backend serves can answer it:

- `total` and `held` come off `WorkflowRunRepository.tallies`, which is one
  grouped read for the whole tenant rather than one per row. The rig issued
  two index counts per workflow; `serve_shapes` learned that the per-workflow
  form degrades exactly as a customer succeeds, and this route is drawn on a
  console screen every few seconds.
- `stale` is the count of steps a run last matched through a weak locator,
  written by the runner's `mark_stale`. This is its only reader, as it was in
  the rig: without it a job's page can move under it for a week and the first
  anybody hears is the run that breaks.
- `earned` is whether this job may write without asking a person first. It is
  read from `proofs` and never from the tally beside it -- a job with a
  hundred held runs and nothing in its register has earned nothing.

`counsel`, the offer fates it is derived from, and the last run are not here.
The first two are `/v1/shapes`' answer already -- it serves the k a job is
offered at, and computing it a second time here is a second place the offer
policy lives -- and the runs, whole, with their steps and their approvals, are
`/v1/audit`'s. A field that already has a door is not worth two.

**The evidence is complete rather than trimmed**, as the rig's is, and for its
reason: `application.skill.from_rig` turns a mined step into something
replayable out of exactly this shape, and a route called `evidence` that
quietly ships part of the evidence is the defect this project keeps finding.
Cited gestures only, though -- not the stream and not the store. A workflow is
a claim about specific evidence, and the largest real one cites 35 of 387
gestures.

An unknown workflow is `NotFound` out of the repository, and never an empty
answer: `sro.interface.http.errors` maps it to a 404 once, for every route. A
listing that answered "this job cites nothing" to a job that does not exist
would tell a caller their bridge is fine and their workflow is empty.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.execution.effects import earned
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Workflow, ordered_cites


@dataclass(frozen=True, slots=True)
class KnownWorkflow:
    """One workflow with what has become of it.

    The workflow whole, rather than the handful of its fields a card draws:
    `parameters` and `unproven` are the pass's own model output and exist
    nowhere else a reader can reach, and `unproven` in particular is what the
    pass could not place -- the one thing a reader most needs and the field a
    route emitting its siblings is likeliest to drop.
    """

    workflow: Workflow
    total: int
    held: int
    stale: int
    earned: bool


@dataclass(frozen=True, slots=True)
class CitedEvidence:
    """What one workflow cites, in the shape a runner's bridge consumes.

    `recordings` is the distinct capture streams those gestures arrived on,
    which is the one input the caller would otherwise have to reach into a
    column for: the backend needs it for `Provenance`, and getting it wrong
    there mis-states whether a skill's values were ever diffed.
    """

    gestures: tuple[Gesture, ...]
    recordings: tuple[str, ...]


class ReadWorkflows:
    """The console's list of this tenant's jobs.

    A class taking a `RequestContext`, as `ReadAudit` beside it is, and not a
    container method like `read_spend`: that one is a method only so a clock
    can be handed to a bare function, and nothing here reads a clock. What
    both shapes keep is the property that matters -- handed a bare
    `tenant_id`, the route would unpack the caller itself, which puts the
    tenant boundary in the interface layer at the one seam where passing the
    wrong tenant is the failure.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> tuple[KnownWorkflow, ...]:
        async with self._uow as uow:
            # One grouped read for the tenant, before the loop, and never one
            # per row: see the module docstring.
            tallied = await uow.workflow_runs.tallies(ctx.tenant_id)
            known = []
            for workflow in await uow.workflows.known(ctx.tenant_id):
                # Absent means never run, which the store's GROUP BY gives no
                # row for at all.
                total, held = tallied.get(workflow.id, (0, 0))
                known.append(
                    KnownWorkflow(
                        workflow=workflow,
                        total=total,
                        held=held,
                        stale=await uow.workflows.stale_count(workflow.id),
                        earned=await earned(uow.workflows, ctx.tenant_id, workflow.id),
                    )
                )
            return tuple(known)


class ReadEvidence:
    """Everything one workflow cites, for the bridge that replays it."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, workflow_id: str) -> CitedEvidence:
        async with self._uow as uow:
            # Tenant-scoped, and this is the whole of the 404: a workflow of
            # somebody else's is not found rather than read.
            workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)
            # `ordered_cites` and not `cited_ids`, deduped rather than set:
            # one spelling of "in step order" in this codebase, and an answer
            # that does not reshuffle between two calls.
            cited = tuple(dict.fromkeys(ordered_cites(workflow)))
            # Not a null check. `gestures_for` with no ids is `IN ()` against
            # Postgres, and a workflow that cites nothing is a real row.
            gestures = await uow.gestures.gestures_for(ctx.tenant_id, ids=cited) if cited else ()
            return CitedEvidence(
                gestures=gestures,
                # In the order the gestures were read -- their own clock --
                # and not sorted: a `Provenance` reads these as the streams a
                # job's evidence arrived on, oldest first.
                recordings=tuple(dict.fromkeys(gesture.stream_id for gesture in gestures)),
            )
