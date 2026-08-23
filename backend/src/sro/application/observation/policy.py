"""Reading and changing what a tenant agreed to have observed.

Changing it is not an endpoint. There is no role model here -- every credential
for a tenant can do everything that tenant can do -- so an HTTP route to switch
observation on would let any operator consent on their colleagues' behalf. It is
a shell command for the same reason minting a credential is one.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.policy import ObservationPolicy


async def current_policy(uow: UnitOfWork, ctx: RequestContext) -> ObservationPolicy:
    """This tenant's policy, or the refusing default.

    Absence is not consent: a tenant nobody has configured captures nothing.
    """
    return await uow.observation_policies.get(ctx.tenant_id) or ObservationPolicy()


class ReadObservationPolicy:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> ObservationPolicy:
        async with self._uow as uow:
            return await current_policy(uow, ctx)


class SetObservationPolicy:
    """The shell's way in. Every change moves the version, so every extension
    picks it up on its next heartbeat."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, policy: ObservationPolicy) -> None:
        async with self._uow as uow:
            await uow.observation_policies.save(ctx.tenant_id, policy)
            await uow.commit()
