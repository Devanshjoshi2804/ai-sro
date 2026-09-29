from __future__ import annotations

from dataclasses import dataclass

from sro.application.chat.candidates import real_jobs
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.skill.job_facts import job_facts
from sro.domain.execution.belts import earned_from, proven_runs
from sro.domain.execution.compiled import Compiled
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Workflow, ordered_cites


@dataclass(frozen=True, slots=True)
class KnownWorkflow:
    workflow: Workflow
    total: int
    held: int
    stale: int
    earned: bool
    proven: int
    compiled: Compiled
    offered: bool


@dataclass(frozen=True, slots=True)
class CitedEvidence:
    gestures: tuple[Gesture, ...]
    recordings: tuple[str, ...]
    missing: tuple[str, ...]


class ReadWorkflows:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def one(self, ctx: RequestContext, *, workflow_id: str) -> Workflow:
        async with self._uow as uow:
            return await uow.workflows.get(ctx.tenant_id, workflow_id)

    async def execute(self, ctx: RequestContext) -> tuple[KnownWorkflow, ...]:
        async with self._uow as uow:
            tallied = await uow.workflow_runs.tallies(ctx.tenant_id)
            known = []
            every = await job_facts(
                uow, ctx.tenant_id, await uow.workflows.known(ctx.tenant_id), now=self._clock.now()
            )
            held_by = {job: held for job, (_, held) in tallied.items()}
            offered = real_jobs(((one.workflow, one.by_id) for one in every), held=held_by)
            for facts in every:
                workflow = facts.workflow
                total, held = tallied.get(workflow.id, (0, 0))
                proofs = await uow.workflows.proofs(ctx.tenant_id, workflow.id)
                known.append(
                    KnownWorkflow(
                        workflow=workflow,
                        total=total,
                        held=held,
                        stale=await uow.workflows.stale_count(workflow.id),
                        earned=earned_from(proofs),
                        proven=proven_runs(proofs),
                        compiled=facts.compiled,
                        offered=workflow.id in offered,
                    )
                )
            return tuple(known)


class ReadEvidence:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, workflow_id: str) -> CitedEvidence:
        async with self._uow as uow:
            workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)
            cited = tuple(dict.fromkeys(ordered_cites(workflow)))
            gestures = await uow.gestures.gestures_for(ctx.tenant_id, ids=cited) if cited else ()
            held = {gesture.id for gesture in gestures}
            return CitedEvidence(
                gestures=gestures,
                recordings=tuple(dict.fromkeys(gesture.stream_id for gesture in gestures)),
                missing=tuple(gid for gid in cited if gid not in held),
            )
