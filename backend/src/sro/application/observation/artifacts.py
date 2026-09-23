from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.observation.register import refuse_unless_itself
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.observation.batch import ObservationBatch
from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, DeviceId

_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "video/mp4": ".mp4"}

_ALLOWED = (ArtifactKind.SCREENSHOT, ArtifactKind.PAYLOAD, ArtifactKind.VIDEO)


@dataclass(frozen=True, slots=True)
class Stored:
    uri: str
    size_bytes: int


def artifact_prefixes(batch: ObservationBatch) -> tuple[str, ...]:
    days = {batch.started_at.date(), batch.ended_at.date(), batch.received_at.date()}
    return tuple(
        f"{batch.tenant_id}/{batch.principal_id}/{day.isoformat()}/{batch.id}/" for day in days
    )


class StoreObservationArtifact:
    def __init__(self, uow: UnitOfWork, blobs: BlobStore, clock: Clock) -> None:
        self._uow = uow
        self._blobs = blobs
        self._clock = clock

    async def execute(
        self,
        ctx: RequestContext,
        *,
        device_id: DeviceId,
        secret: str,
        batch_id: BatchId,
        kind: ArtifactKind,
        data: bytes,
        content_type: str,
        frame_index: int | None = None,
        label: str | None = None,
        at: datetime | None = None,
    ) -> Stored:
        if kind not in _ALLOWED:
            raise InvariantViolation(f"an observation carries no {kind.value}")
        if not data:
            raise InvariantViolation("an artifact with no bytes in it")

        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
            refuse_unless_itself(device, secret, device_id)
            batch = await uow.observations.get(ctx.tenant_id, batch_id)

        day = (at or (batch.started_at if batch else self._clock.now())).date().isoformat()
        name = f"{frame_index:05d}" if frame_index is not None else (label or "artifact")
        key = (
            f"{ctx.tenant_id}/{ctx.principal_id}/{day}/{batch_id}/"
            f"{kind.value}/{name}{_EXTENSIONS.get(content_type, '')}"
        )
        uri = await self._blobs.put(key, data, content_type=content_type)
        return Stored(uri=uri, size_bytes=len(data))
