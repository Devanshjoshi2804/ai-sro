"""Take an upload from a browser and put it in the evidence plane.

Verbatim, in one object per batch. Whatever normalisation a miner wants can be
re-run over what arrived; what was never stored cannot be recovered, and an
operator's day is not repeatable the way a demonstration is.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.observation.admit import Event, admit
from sro.application.observation.policy import current_policy
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.observation.batch import CaptureMode, ObservationBatch, RejectedEvent
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import BatchId, DeviceId

CONTENT_TYPE = "application/x-ndjson"


class ObservationRefused(DomainError):
    """This upload will not be stored, and the reason is not transient.

    A tenant who has not switched observation on, or a device an administrator
    has paused. The extension stops rather than retries -- a queue draining into
    a refusal is how a browser spends a day trying to send work nobody wants.
    """

    code = "observation_refused"


@dataclass(frozen=True, slots=True)
class Ingested:
    batch_id: BatchId
    accepted: int
    rejected: tuple[RejectedEvent, ...]
    stored_at: str | None
    """Where the evidence went. ``None`` when nothing in the batch survived
    screening, in which case no object was written and no row was made."""

    already_had_it: bool = False


class IngestObservation:
    """Idempotent on the batch id the extension minted.

    An upload that reached us and whose response was lost is retried by every
    correct client. Storing it twice would double every count a miner reads, and
    the miner's whole job is counting how often something happened.
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
        batch_id: BatchId,
        started_at: datetime,
        ended_at: datetime,
        mode: CaptureMode,
        events: Sequence[Event],
    ) -> Ingested:
        now = self._clock.now()

        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
            if device.paused:
                raise ObservationRefused(
                    "this device is paused; nothing it captures will be stored"
                )

            policy = await current_policy(uow, ctx)
            if not policy.capture_enabled:
                raise ObservationRefused("observation is not switched on for this tenant")

            seen = await uow.observations.get(ctx.tenant_id, batch_id)
            if seen is not None:
                return Ingested(
                    batch_id=batch_id,
                    accepted=seen.event_count,
                    rejected=seen.rejected,
                    stored_at=seen.uri,
                    already_had_it=True,
                )

            admission = admit(events, policy)
            if not admission.accepted:
                return Ingested(
                    batch_id=batch_id,
                    accepted=0,
                    rejected=admission.rejected,
                    stored_at=None,
                )

            payload = _ndjson(admission.accepted)
            # ponytail: the daily byte budget is enforced in the extension only.
            # Server-side would mean summing today's batches on every upload;
            # add it here when a device is seen to ignore the policy.
            uri = await self._blobs.put(
                _key(ctx, batch_id, at=started_at), payload, content_type=CONTENT_TYPE
            )

            batch = ObservationBatch(
                id=batch_id,
                tenant_id=ctx.tenant_id,
                device_id=device_id,
                principal_id=ctx.principal_id,
                mode=mode,
                started_at=started_at,
                ended_at=ended_at,
                received_at=now,
                uri=uri,
                event_count=admission.accepted_count,
                byte_count=len(payload),
                rejected=admission.rejected,
            )
            await uow.observations.add(batch)
            device.uploaded(now)
            await uow.devices.save(device)
            await uow.commit()

        return Ingested(
            batch_id=batch_id,
            accepted=batch.event_count,
            rejected=batch.rejected,
            stored_at=batch.uri,
        )


def _key(ctx: RequestContext, batch_id: BatchId, *, at: datetime) -> str:
    """Tenant first, then who, then the day. A lifecycle rule for a retention
    window is a prefix match, and a purge for one operator is another."""
    return f"{ctx.tenant_id}/{ctx.principal_id}/{at.date().isoformat()}/{batch_id}.ndjson"


def _ndjson(events: Sequence[Event]) -> bytes:
    return b"".join(json.dumps(event, separators=(",", ":")).encode() + b"\n" for event in events)
