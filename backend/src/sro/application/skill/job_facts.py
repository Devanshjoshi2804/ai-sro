from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.compiled import Compiled, compile_job
from sro.domain.execution.lanes import Broken, cites_key
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.aliases import JobAlias
from sro.domain.skill.workflow import Workflow

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class JobFacts:
    workflow: Workflow
    by_id: Mapping[str, Gesture]
    learned: Mapping[int, LearnedStep]
    broken: tuple[Broken, ...]
    aliases: tuple[JobAlias, ...]
    compiled: Compiled


async def job_facts(
    uow: UnitOfWork, tenant_id: TenantId, workflows: Sequence[Workflow]
) -> tuple[JobFacts, ...]:
    ledger = await uow.workflows.learned_writes(tenant_id)
    ids = tuple(sorted({one for w in workflows for step in w.steps for one in step.cites}))
    gestures = {g.id: g for g in await uow.gestures.gestures_for(tenant_id, ids=ids)} if ids else {}
    found = []
    for workflow in workflows:
        by_id = {
            one: gestures[one] for step in workflow.steps for one in step.cites if one in gestures
        }
        learned = {one.ord: one for one in await uow.workflows.learned_for(workflow.id)}
        broken = await uow.workflows.broken_for(
            tenant_id, workflow.id, {step.order: cites_key(step) for step in workflow.steps}
        )
        aliases: tuple[JobAlias, ...] = ()
        compiled = compile_job(
            workflow, by_id, learned=learned, ledger=ledger, broken=broken, aliases=aliases
        )
        found.append(JobFacts(workflow, by_id, learned, tuple(broken), aliases, compiled))
    return tuple(found)


async def runnable_jobs(
    uow: UnitOfWork, tenant_id: TenantId, workflows: Sequence[Workflow]
) -> tuple[JobFacts, ...]:
    facts = await job_facts(uow, tenant_id, workflows)
    for one in facts:
        if not one.compiled.runnable:
            logger.info(
                "%s: %s cannot run and is not offered: %s",
                tenant_id.value,
                one.workflow.id,
                ", ".join(reason.code for reason in one.compiled.reasons),
            )
    return tuple(one for one in facts if one.compiled.runnable)
