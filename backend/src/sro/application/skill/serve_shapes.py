"""Every proven workflow of a tenant, as the extension needs it.

Ported from `shapes_for` in `new_agent_arch/src/rig/shapes.py`. The arithmetic
-- given a workflow's cited pairs, its held tally and its counsel, what shape
comes out -- is `sro.domain.skill.shape.shape_of`, which plan 1 took whole.
What is here is the half that needed a store: the loop over a tenant's
workflows, the gate each one has to pass, and the three reads behind every
shape that is served.

`rekey_workflows` was landed here by Task 7 and has since moved to
`sro.application.observation.mining_pass`, where the plan's file map and the
rig both put it. It walks the same evidence, but it WRITES, and this module's
promise is that nothing in it does -- two session contracts in one file is a
docstring that is false twelve lines below where it is made.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.ports.repositories import UnitOfWork
from sro.application.skill.counsel import counsel
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.shape import Shape, cited_pairs, shape_of
from sro.domain.skill.workflow import ordered_cites


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
        wanted = ordered_cites(workflow)
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
