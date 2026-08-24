"""An operator deleting their own evidence.

The button in the extension that says "purge the last hour" and means it. Scoped
to the principal on the credential, never to the tenant: one operator does not
get to erase another's day, and nothing here reaches across tenants at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.observation.artifacts import artifact_prefixes
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock


@dataclass(frozen=True, slots=True)
class Forgotten:
    batches: int
    events: int


class ForgetObservations:
    """Rows go, then blobs.

    That order on purpose: a row pointing at an object that is gone is a miner
    error somebody sees, and an object nobody points at is a lifecycle rule's
    problem. The reverse leaves evidence readable after it was said to be
    deleted, which is the one outcome that makes the promise a lie.
    """

    def __init__(self, uow: UnitOfWork, blobs: BlobStore, clock: Clock) -> None:
        self._uow = uow
        self._blobs = blobs
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, since: datetime) -> Forgotten:
        async with self._uow as uow:
            doomed = await uow.observations.between(
                ctx.tenant_id, since=since, principal_id=ctx.principal_id
            )
            if not doomed:
                return Forgotten(batches=0, events=0)
            await uow.observations.forget(ctx.tenant_id, tuple(batch.id for batch in doomed))
            await uow.commit()

        for batch in doomed:
            await self._blobs.forget(batch.uri)
            for prefix in artifact_prefixes(batch):
                await self._blobs.forget_prefix(prefix)
        return Forgotten(batches=len(doomed), events=sum(batch.event_count for batch in doomed))
