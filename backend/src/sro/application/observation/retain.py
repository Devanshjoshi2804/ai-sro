from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.application.observation.artifacts import artifact_prefixes
from sro.application.observation.forget import Forgotten
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.identifiers import TenantId

_BEFORE_THIS_SYSTEM_EXISTED = datetime(2000, 1, 1, tzinfo=UTC)


class SweepRetention:
    def __init__(self, uow: UnitOfWork, blobs: BlobStore, clock: Clock) -> None:
        self._uow = uow
        self._blobs = blobs
        self._clock = clock

    async def execute(self) -> dict[str, Forgotten]:
        now = self._clock.now()
        async with self._uow as uow:
            tenants = await uow.observations.tenants_since(_BEFORE_THIS_SYSTEM_EXISTED)

        forgotten: dict[str, Forgotten] = {}
        for tenant_id in tenants:
            forgotten[tenant_id.value] = await self._sweep_one(tenant_id, now)
        return forgotten

    async def _sweep_one(self, tenant_id: TenantId, now: datetime) -> Forgotten:
        async with self._uow as uow:
            policy = await uow.observation_policies.get(tenant_id) or ObservationPolicy()
            cutoff = now - timedelta(days=policy.retention_days)
            doomed = await uow.observations.received_before(tenant_id, cutoff)
            if not doomed:
                return Forgotten(batches=0, events=0)
            await uow.observations.forget(tenant_id, tuple(batch.id for batch in doomed))
            await uow.commit()

        for batch in doomed:
            await self._blobs.forget(batch.uri)
            for prefix in artifact_prefixes(batch):
                await self._blobs.forget_prefix(prefix)
        return Forgotten(batches=len(doomed), events=sum(batch.event_count for batch in doomed))
