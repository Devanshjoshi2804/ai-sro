from __future__ import annotations

from datetime import datetime

from sro.application.chat.candidates import real_jobs
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.skill.counsel import counsel
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.shape import Shape, cited_pairs, shape_of
from sro.domain.skill.workflow import ordered_cites


class ServeShapes:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, device_id: DeviceId | None) -> list[Shape]:
        async with self._uow as uow:
            return await shapes_for(
                uow,
                tenant_id=ctx.tenant_id,
                device_id=device_id,
                now=self._clock.now(),
            )


K_ONLY_EVER_FAILED = 3


async def shapes_for(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    device_id: DeviceId | None = None,
    now: datetime,
) -> list[Shape]:
    tallied = await uow.workflow_runs.tallies(tenant_id)
    broke = await uow.workflow_runs.failures(tenant_id)
    known = await uow.workflows.known(tenant_id)
    ids = tuple(sorted({one for workflow in known for one in ordered_cites(workflow)}))
    stored = {g.id: g for g in await uow.gestures.gestures_for(tenant_id, ids=ids)} if ids else {}
    cited = {
        workflow.id: {one: stored[one] for one in ordered_cites(workflow) if one in stored}
        for workflow in known
    }
    real = real_jobs(
        ((workflow, cited[workflow.id]) for workflow in known),
        held={job: held for job, (_, held) in tallied.items()},
    )
    served: list[Shape] = []
    for workflow in known:
        _, held = tallied.get(workflow.id, (0, 0))
        if workflow.id not in real:
            continue
        if broke.get(workflow.id, 0) >= K_ONLY_EVER_FAILED and not held:
            continue
        by_id = cited[workflow.id]
        advice = await counsel(
            uow, tenant_id=tenant_id, workflow_id=workflow.id, device_id=device_id, now=now
        )
        shape = shape_of(workflow, cited_pairs(workflow, by_id), held=held, advice=advice)
        if shape is not None:
            served.append(shape)
    return served
