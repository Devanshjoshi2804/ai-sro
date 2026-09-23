from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.policy import ObservationPolicy


async def current_policy(uow: UnitOfWork, ctx: RequestContext) -> ObservationPolicy:
    return await uow.observation_policies.get(ctx.tenant_id) or ObservationPolicy()


class ReadObservationPolicy:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> ObservationPolicy:
        async with self._uow as uow:
            return await current_policy(uow, ctx)


class SetObservationPolicy:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, policy: ObservationPolicy) -> None:
        async with self._uow as uow:
            await uow.observation_policies.save(ctx.tenant_id, policy)
            await uow.commit()
