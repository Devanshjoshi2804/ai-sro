"""Every proven workflow of a tenant, as the extension needs it.

Ported from `shapes_for` in `new_agent_arch/src/rig/shapes.py`. The arithmetic
-- given a workflow's cited pairs, its held tally and its counsel, what shape
comes out -- is `sro.domain.skill.shape.shape_of`, which plan 1 took whole.
What is here is the half that needed a store: the loop over a tenant's
workflows, the gate each one has to pass, and the three reads behind every
shape that is served.

`rekey_workflows` sits beside it because it is the same walk over the same
evidence, asking the other question about a shape key. Plan 3a's file map
lists it under the mining pass; its three tests were deferred to this task by
name, and one implementation under two names is worse than one in the file
its tests are in. The miner should import it from here.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.ports.repositories import UnitOfWork
from sro.application.skill.counsel import counsel
from sro.domain.observation.identity import shape_key
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.shape import Shape, cited_pairs, shape_of
from sro.domain.skill.workflow import Workflow


def _ordered_cites(workflow: Workflow) -> list[str]:
    """Every gesture the workflow cites, in step order. `cited_ids` is a set,
    and a shape key made in set order is not this job's shape."""
    return [cited for step in sorted(workflow.steps, key=lambda s: s.order) for cited in step.cites]


async def shapes_for(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    device_id: DeviceId | None = None,
    now: datetime,
) -> list[Shape]:
    """Every proven workflow, as the extension needs it. `device_id` is the
    asking browser, for the rest its own refusals earned it.

    A workflow that has been run is asked a harder question -- has it ever
    held -- because an offer to do a job the runner has only ever failed is an
    offer to fail in front of somebody. The gate is per workflow and not per
    tenant: one workflow's first failure must not silence every sibling that
    has simply never been run. And a job that has never run at all is served,
    because it has not failed anything -- it has sat no test.

    Nothing after that gate is fatal either. A workflow that cites evidence
    the store no longer holds, or that starts on an origin its own evidence
    never names, is skipped where it stands. This is asked by every browser on
    every gesture cache miss, and one bad row emptying the panel is the whole
    tenant losing its jobs over one of them.

    `now` is the caller's clock, passed on to `counsel` and never read in
    here, so a test can move it. Nothing writes, so nothing commits: the
    caller owns the session.

    A stated divergence from the rig: the rig counted a workflow's runs off
    the runs index rather than loading them, and this port has no count on
    `WorkflowRunRepository` to do that with. `for_workflow` loads each run
    with its steps, one read per proven workflow.
    """
    served: list[Shape] = []
    for workflow in await uow.workflows.known(tenant_id):
        if workflow.unproven:
            continue
        runs = await uow.workflow_runs.for_workflow(tenant_id, workflow.id)
        held = sum(1 for run in runs if run.outcome == "held")
        if runs and not held:
            continue
        wanted = _ordered_cites(workflow)
        if not wanted:
            continue
        by_id = {
            gesture.id: gesture
            for gesture in await uow.gestures.gestures_for(tenant_id, ids=tuple(wanted))
        }
        cited = cited_pairs(workflow, by_id)
        if not cited:
            continue
        advice = await counsel(
            uow, tenant_id=tenant_id, workflow_id=workflow.id, device_id=device_id, now=now
        )
        shape = shape_of(workflow, cited, held=held, advice=advice)
        if shape is not None:
            served.append(shape)
    return served


async def rekey_workflows(uow: UnitOfWork, *, tenant_id: TenantId) -> int:
    """Every stored workflow's shape key recomputed from its cited gestures,
    and how many changed.

    The key is what `identity.resolve` compares a new proposal against. When
    the rule that makes it changes -- the text rung stopped taking page copy
    -- keys mined before the change no longer match keys mined after, and a
    job the rig already holds could be proposed again as a new one. Run once
    at startup; a key that already agrees is left alone, and a pass that
    changes nothing writes nothing.
    """
    changed = 0
    for workflow in await uow.workflows.known(tenant_id):
        wanted = _ordered_cites(workflow)
        if not wanted:
            continue
        by_id = {
            gesture.id: gesture
            for gesture in await uow.gestures.gestures_for(tenant_id, ids=tuple(wanted))
        }
        # Only over the whole evidence. A key recomputed over the survivors of
        # a pruned batch would be shorter than the job -- and an empty one
        # matches nothing, which is the duplicate this exists to prevent.
        if any(cited not in by_id for cited in wanted):
            continue
        fresh = shape_key([by_id[cited] for cited in wanted])
        if [list(triple) for triple in fresh] == workflow.shape_key:
            continue
        await uow.workflows.rekey(tenant_id, workflow.id, fresh)
        changed += 1
    if changed:
        await uow.commit()
    return changed
