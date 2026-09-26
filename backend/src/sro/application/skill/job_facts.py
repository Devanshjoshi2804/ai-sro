from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.execution.declared import kb_rows, limits_from_rows, names_of, screen_of_loaded
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.compiled import Compiled, compile_job
from sro.domain.execution.lanes import Broken, cites_key
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.aliases import JobAlias
from sro.domain.skill.workflow import Workflow

logger = logging.getLogger(__name__)

_SAID: dict[tuple[str, str], tuple[str, ...]] = {}


@dataclass(frozen=True, slots=True)
class JobFacts:
    workflow: Workflow
    by_id: Mapping[str, Gesture]
    learned: Mapping[int, LearnedStep]
    broken: tuple[Broken, ...]
    aliases: tuple[JobAlias, ...]
    compiled: Compiled


def _say_once(tenant_id: TenantId, workflow_id: str, compiled: Compiled) -> None:
    codes = tuple(one.code for one in compiled.reasons)
    if _SAID.get((tenant_id.value, workflow_id), ()) == codes:
        return
    _SAID[(tenant_id.value, workflow_id)] = codes
    if codes:
        logger.info("%s: %s cannot run: %s", tenant_id.value, workflow_id, ", ".join(codes))


async def job_facts(
    uow: UnitOfWork,
    tenant_id: TenantId,
    workflows: Sequence[Workflow],
    *,
    now: datetime,
    values: Mapping[str, str] | None = None,
    from_step: int = 0,
) -> tuple[JobFacts, ...]:
    ledger = await uow.workflows.learned_writes(tenant_id)
    ids = tuple(sorted({one for w in workflows for step in w.steps for one in step.cites}))
    gestures = {g.id: g for g in await uow.gestures.gestures_for(tenant_id, ids=ids)} if ids else {}
    names_by_workflow = {workflow.id: names_of(workflow) for workflow in workflows}
    fields, forms = await kb_rows(uow, tenant_id) if any(names_by_workflow.values()) else ((), ())
    found = []
    for workflow in workflows:
        by_id = {
            one: gestures[one] for step in workflow.steps for one in step.cites if one in gestures
        }
        learned = {one.ord: one for one in await uow.workflows.learned_for(workflow.id)}
        broken = await uow.workflows.broken_for(
            tenant_id,
            workflow.id,
            {step.order: cites_key(step) for step in workflow.steps},
            now=now,
        )
        aliases: tuple[JobAlias, ...] = ()
        names = names_by_workflow[workflow.id]
        declared = (
            limits_from_rows(names, fields, forms, screen_of_loaded(by_id, workflow))
            if names
            else {}
        )
        compiled = compile_job(
            workflow,
            by_id,
            learned=learned,
            ledger=ledger,
            broken=broken,
            aliases=aliases,
            values=values,
            from_step=from_step,
            declared=declared,
        )
        if values is None and not from_step:
            _say_once(tenant_id, workflow.id, compiled)
        found.append(JobFacts(workflow, by_id, learned, tuple(broken), aliases, compiled))
    return tuple(found)
