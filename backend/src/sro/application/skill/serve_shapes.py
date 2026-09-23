from __future__ import annotations

from datetime import datetime

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
    served: list[Shape] = []
    for workflow in await uow.workflows.known(tenant_id):
        _, held = tallied.get(workflow.id, (0, 0))
        if broke.get(workflow.id, 0) >= K_ONLY_EVER_FAILED and not held:
            continue
        wanted = ordered_cites(workflow)
        if not wanted:
            continue
        by_id = {
            gesture.id: gesture
            for gesture in await uow.gestures.gestures_for(tenant_id, ids=tuple(wanted))
        }
        advice = await counsel(
            uow, tenant_id=tenant_id, workflow_id=workflow.id, device_id=device_id, now=now
        )
        shape = shape_of(workflow, cited_pairs(workflow, by_id), held=held, advice=advice)
        if shape is not None:
            served.append(shape)
    return served
