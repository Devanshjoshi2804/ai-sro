from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from sro.application.capture.rig_wire import Batch as WireBatch
from sro.application.context import RequestContext
from sro.application.observation.admit import Event, admit
from sro.application.observation.correlate import correlate
from sro.application.observation.policy import current_policy
from sro.application.observation.redact import redact_events
from sro.application.observation.register import refuse_unless_itself
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.config import get_settings
from sro.domain.observation.batch import (
    CaptureMode,
    ObservationBatch,
    RejectedEvent,
    check_times,
)
from sro.domain.observation.gesture import GestureBatch
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import BatchId, DeviceId

CONTENT_TYPE = "application/x-ndjson"


def _as_wire_batch(batch: ObservationBatch, events: Sequence[Event]) -> tuple[WireBatch, int]:
    readable = []
    unreadable = 0
    for event in events:
        try:
            readable.append(
                WireBatch.model_validate(
                    {
                        "batch_id": batch.id.value,
                        "device_id": batch.device_id.value,
                        "started_at": batch.started_at.isoformat(),
                        "ended_at": batch.ended_at.isoformat(),
                        "mode": batch.mode.value,
                        "recording_id": batch.recording_id.value if batch.recording_id else None,
                        "events": [event],
                    }
                ).events[0]
            )
        except ValueError:
            unreadable += 1
    return (
        WireBatch(
            batch_id=batch.id.value,
            device_id=batch.device_id.value,
            started_at=batch.started_at.isoformat(),
            ended_at=batch.ended_at.isoformat(),
            mode=batch.mode.value,
            recording_id=batch.recording_id.value if batch.recording_id else None,
            events=readable,
        ),
        unreadable,
    )


class ObservationRefused(DomainError):
    code = "observation_refused"


@dataclass(frozen=True, slots=True)
class Ingested:
    batch_id: BatchId
    accepted: int
    rejected: tuple[RejectedEvent, ...]
    stored_at: str | None

    already_had_it: bool = False
    snapshots_ignored: int = 0


class IngestObservation:
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
        started_at: datetime,
        ended_at: datetime,
        mode: CaptureMode,
        events: Sequence[Event],
    ) -> Ingested:
        now = self._clock.now()

        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
            refuse_unless_itself(device, secret, device_id)
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

            admission = admit(
                events, policy, device.granted_hosts(now), get_settings().our_own_origins()
            )
            if not admission.accepted:
                return Ingested(
                    batch_id=batch_id,
                    accepted=0,
                    rejected=admission.rejected,
                    stored_at=None,
                )

            check_times(started_at, ended_at, now)
            redacted = redact_events(admission.accepted)
            payload = _ndjson(redacted)
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
            wire, unreadable = _as_wire_batch(batch, redacted)
            gestures, orphans, marks, snapshots = correlate(wire, ctx.tenant_id.value)
            await uow.gestures.add_batch(
                GestureBatch(
                    batch_id=batch.id.value,
                    device_id=device_id.value,
                    tenant=ctx.tenant_id.value,
                    mode=mode.value,
                    received_at=now.isoformat(),
                    started_at=started_at.isoformat(),
                    ended_at=ended_at.isoformat(),
                    accepted=len(gestures),
                    rejected=len(admission.rejected) + unreadable,
                )
            )
            if gestures:
                await uow.gestures.add_gestures(tuple(gestures))
            for orphan in orphans:
                await uow.gestures.add_orphan_request(
                    ctx.tenant_id,
                    batch_id=batch.id.value,
                    request_id=orphan.request_id,
                    payload=asdict(orphan),
                )
            for mark in marks:
                await uow.gestures.add_orphan_page(
                    ctx.tenant_id,
                    batch_id=batch.id.value,
                    at=datetime.fromtimestamp(mark.at, UTC).isoformat(),
                    payload=asdict(mark),
                )
            device.uploaded(now)
            await uow.devices.save(device)
            await uow.commit()

        return Ingested(
            batch_id=batch_id,
            accepted=batch.event_count,
            rejected=batch.rejected,
            stored_at=batch.uri,
            snapshots_ignored=snapshots,
        )


def _key(ctx: RequestContext, batch_id: BatchId, *, at: datetime) -> str:
    return f"{ctx.tenant_id}/{ctx.principal_id}/{at.date().isoformat()}/{batch_id}.ndjson"


def _ndjson(events: Sequence[Event]) -> bytes:
    return b"".join(
        json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
        for event in events
    )
