from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sro.application.context import RequestContext
from sro.application.observation.artifacts import artifact_prefixes
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock


@dataclass(frozen=True, slots=True)
class Forgotten:
    batches: int
    events: int
    artifacts: int = 0


class ForgetObservations:
    def __init__(self, uow: UnitOfWork, blobs: BlobStore, clock: Clock) -> None:
        self._uow = uow
        self._blobs = blobs
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, since: datetime) -> Forgotten:
        bound = since if since.tzinfo else since.replace(tzinfo=UTC)
        async with self._uow as uow:
            doomed = await uow.observations.between(
                ctx.tenant_id, since=bound, principal_id=ctx.principal_id
            )
            if not doomed:
                return Forgotten(batches=0, events=0, artifacts=0)
            await uow.observations.forget(ctx.tenant_id, tuple(batch.id for batch in doomed))
            await uow.commit()

        artifacts = 0
        for batch in doomed:
            await self._blobs.forget(batch.uri)
            for prefix in artifact_prefixes(batch):
                artifacts += await self._blobs.forget_prefix(prefix)
        return Forgotten(
            batches=len(doomed),
            events=sum(batch.event_count for batch in doomed),
            artifacts=artifacts,
        )
