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
from sro.application.observation.redact import redact_events
from sro.application.observation.register import refuse_unless_itself
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.config import get_settings
from sro.domain.observation.batch import CaptureMode, ObservationBatch, RejectedEvent
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import BatchId, DeviceId, RecordingId

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
        secret: str,
        batch_id: BatchId,
        started_at: datetime,
        ended_at: datetime,
        mode: CaptureMode,
        events: Sequence[Event],
        recording_id: RecordingId | None = None,
    ) -> Ingested:
        now = self._clock.now()

        if (mode is CaptureMode.TEACHING) != (recording_id is not None):
            # Both directions are refusals. Teaching evidence with no
            # demonstration named cannot be told from an ordinary morning, and
            # ordinary browsing filed against a demonstration would be taught
            # as though somebody had meant to show it.
            raise ObservationRefused(
                "a teaching batch names its demonstration and a passive one does not"
            )

        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
            # The tenant credential says who is asking and can never say which
            # browser. Without this, a colleague holding a valid token could
            # file a day of their own browsing against somebody else's device,
            # and every candidate mined from it would name the wrong operator.
            refuse_unless_itself(device, secret, device_id)
            if device.paused:
                raise ObservationRefused(
                    "this device is paused; nothing it captures will be stored"
                )

            policy = await current_policy(uow, ctx)
            if not policy.capture_enabled:
                raise ObservationRefused("observation is not switched on for this tenant")

            if recording_id is not None:
                # Read, not trusted: the demonstration has to exist, be this
                # tenant's, be the one this browser was asked to perform, and
                # still be open. A sealed recording that could still be added
                # to is a skill whose provenance changes after it was reviewed.
                recording = await uow.recordings.get(ctx.tenant_id, recording_id)
                if recording.device_id != device_id:
                    raise ObservationRefused(
                        "this demonstration is being performed in a different browser"
                    )
                if not recording.is_open:
                    raise ObservationRefused("this demonstration has already been sealed")

            seen = await uow.observations.get(ctx.tenant_id, batch_id)
            if seen is not None:
                return Ingested(
                    batch_id=batch_id,
                    accepted=seen.event_count,
                    rejected=seen.rejected,
                    stored_at=seen.uri,
                    already_had_it=True,
                )

            # What this operator said may be watched after all, on top of
            # what the tenant agreed to by default. Read from the device
            # already loaded above, and expired grants simply are not in it.
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

            # Between screening and serialisation, on the whole batch, and
            # nowhere else. `admit()` filters by host policy and says nothing
            # about values; without this the browser's own redaction was the
            # only one there was, and a browser can be made not to run it --
            # measured, on this tenant's real traffic: a live JWT and the
            # `&code=` carrying it reached the blob store with no marker on
            # them at all.
            payload = _ndjson(redact_events(admission.accepted))
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
                recording_id=recording_id,
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
    """One event per line, as the extension streamed it.

    ``ensure_ascii=False`` because the default escapes the redaction marker to
    ``\\u00abredacted\\u00bb``: every batch already in the store carries the
    markers the extension wrote, and grepping those objects for the «redacted»
    that every redaction path in this codebase writes finds not one of them.
    The same round-trip argument as `_redact_query` -- a marker a reviewer
    cannot grep for is a hole nobody can count.
    """
    return b"".join(
        json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
        for event in events
    )
