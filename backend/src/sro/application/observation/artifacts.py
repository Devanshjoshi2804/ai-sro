"""Screenshots and oversized bodies, stored beside the batch they belong to."""

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
"""A recording's other kinds -- raw events, audio, transcript -- belong to a
demonstration somebody started. An observation stream has no narration."""


@dataclass(frozen=True, slots=True)
class Stored:
    uri: str
    size_bytes: int


def artifact_prefixes(batch: ObservationBatch) -> tuple[str, ...]:
    """Every key prefix a purge of this batch's artifacts has to sweep.

    Usually one: an artifact is filed under the day of the batch it
    illustrates, which `execute()` below reads off the batch for exactly this
    reason. A batch spanning midnight gets both days rather than risk leaving
    one behind -- the same key shape `execute()` writes, read back rather than
    re-derived a second way.

    `received_at` is in the set as well, and it is the belt. An artifact whose
    batch row had not landed yet is filed under the day this server was having
    when it arrived, and that is the closest day to it anything here knows.
    Without it, a screenshot filed on one day and a batch stamped on another
    -- the browser's clock runs up to 23 hours from this one on the real store
    -- leaves a prefix nobody ever sweeps: `forget_prefix` returns 0, the
    operator is told "0 artifacts", and the pictures stay.
    """
    days = {batch.started_at.date(), batch.ended_at.date(), batch.received_at.date()}
    return tuple(
        f"{batch.tenant_id}/{batch.principal_id}/{day.isoformat()}/{batch.id}/" for day in days
    )


class StoreObservationArtifact:
    """No row. The key says which batch and which frame it belongs to, so a
    miner reading a batch finds its screenshots by prefix, and a retention rule
    expires them with the evidence they illustrate.
    """

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
            # The same two questions ingest asks, for the same reason: the
            # credential says which tenant, the secret says which browser, and
            # a screenshot is a picture of somebody's screen filed under their
            # name.
            device = await uow.devices.get(ctx.tenant_id, device_id)
            refuse_unless_itself(device, secret, device_id)
            batch = await uow.observations.get(ctx.tenant_id, batch_id)

        # The batch's own day, because the purge reads the batch and this
        # writes the key: two clocks here means a prefix nobody sweeps. This
        # server's day only when there is no batch to ask -- a picture that
        # arrived before the evidence it illustrates -- and
        # `artifact_prefixes` carries `received_at` to cover that case.
        day = (at or (batch.started_at if batch else self._clock.now())).date().isoformat()
        name = f"{frame_index:05d}" if frame_index is not None else (label or "artifact")
        key = (
            f"{ctx.tenant_id}/{ctx.principal_id}/{day}/{batch_id}/"
            f"{kind.value}/{name}{_EXTENSIONS.get(content_type, '')}"
        )
        uri = await self._blobs.put(key, data, content_type=content_type)
        return Stored(uri=uri, size_bytes=len(data))
