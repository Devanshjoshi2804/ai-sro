"""Take an upload from a browser and put it in the evidence plane.

Verbatim, in one object per batch. Whatever normalisation a miner wants can be
re-run over what arrived; what was never stored cannot be recovered, and an
operator's day is not repeatable the way a demonstration is.
"""

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
from sro.domain.shared.identifiers import BatchId, DeviceId, RecordingId

CONTENT_TYPE = "application/x-ndjson"


def _as_wire_batch(batch: ObservationBatch, events: Sequence[Event]) -> tuple[WireBatch, int]:
    """The stored batch in the shape `correlate` reads, and how many events it
    could not.

    Parsed one at a time and never as a whole envelope, which is the rig's rule
    at `new_agent_arch/src/rig/api.py:482-487` and it holds harder here: these
    events have already been admitted, stored and answered for. An event kind
    the extension shipped last week must not take the batch beside it down --
    by the time this runs the upload is a fact, and raising would roll back a
    claim for events that are already in the blob store.

    The count comes back so the tally says a batch had events nothing could
    read, rather than a batch that quietly had fewer.
    """
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
    snapshots_ignored: int = 0
    """Accessibility-tree snapshots admitted, stored, and read by nothing.

    There is nowhere in the schema to put one, and `correlate`'s docstring says
    why the count exists anyway: silently dropping them is not the same as
    never having received them. On the response for the same reason the
    rejections are -- a browser shipping snapshots nothing reads should be able
    to see that from the answer, not from a mining run three weeks later. The
    rig returns it in the same 202 body (`new_agent_arch/src/rig/api.py:534`).

    0 on a batch we already had: nothing re-read it, and no column records what
    the first pass ignored.
    """


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
            # Before the object is written, not after. `ObservationBatch`
            # asks the same two questions and it is built below, once the blob
            # has an address -- so an envelope carrying an offset-less time
            # answered 422 with the NDJSON already in the store, the
            # transaction rolled back, and no row left pointing at it. Neither
            # a purge nor the retention sweep can reach an object nothing
            # names.
            check_times(started_at, ended_at, now)
            redacted = redact_events(admission.accepted)
            payload = _ndjson(redacted)
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
            # The same upload again, as the miner reads it. Two tables, neither
            # derived from the other: `observations` keeps the events verbatim
            # in the blob store, and this keeps what was read out of them.
            #
            # In this block on purpose, so the batch claim and its gestures
            # commit together. A claim written without them is an id that can
            # never be retried -- the events it named are gone, and the row says
            # they were handled. The rig makes the same argument for the same
            # reason at `new_agent_arch/src/rig/api.py:63-72`.
            #
            # Correlated from the REDACTED events, not the accepted ones: the
            # redacted payload is what was stored, and a gesture carrying a
            # value the blob store does not have is a citation pointing at
            # nothing.
            #
            # Measured, because the argument is right and the margin is not:
            # `rig_wire`'s validators redact on their own, so a url, a typed
            # value, a prose label, a header and a body TEXT come out the same
            # either way. The one field that does not is `redacted_fields` --
            # the wire's `redact_body` reports shapes and this one reports
            # names -- so `admission.accepted` here would store bodies that no
            # longer say a password was ever in them. Pinned by
            # `test_the_gesture_stored_says_which_field_the_blob_store_lost`.
            # Defence in depth, then, rather than the only belt; keep it that
            # way, and do not let the wire's copy become the argument for
            # deleting this one.
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
                    recording_id=recording_id.value if recording_id else None,
                    accepted=len(gestures),
                    # Two kinds of loss, deliberately one number. An event
                    # `admit()` turned away never reached the blob store; one
                    # `_as_wire_batch` could not parse did, was paid for, and
                    # is read by nobody. Neither became a gesture, and this
                    # column's question is "what did this batch not yield" --
                    # so `accepted + rejected` is not the event count and was
                    # never meant to be. Split them the day something acts on
                    # the difference rather than reports it.
                    rejected=len(admission.rejected) + unreadable,
                )
            )
            if gestures:
                await uow.gestures.add_gestures(tuple(gestures))
            # A call or a page event no gesture in THIS batch claimed. In the
            # same block for the same reason the gestures are: an orphan
            # written outside the batch claim is a row nothing can retry.
            #
            # The whole point is the batch boundary. The extension uploads on
            # a timer, so a click at the end of batch N routinely has its XHR
            # arrive in batch N+1, and `correlate` -- which only ever sees one
            # batch -- cannot own it. Dropped here, that call is gone for good
            # and the gesture reads as a click that asked the server nothing.
            # Kept, it is a row a later pass can join on. The rig stores both
            # (`new_agent_arch/src/rig/api.py:118-136`); this discarded both as
            # `_calls` and `_marks` until now, which made cross-batch
            # correlation dead on this side and alive on that one.
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
                    # The column is a string and the domain keeps epoch
                    # seconds, so it is spelled here the way the rig spells it
                    # and the way the contract test writes it: ISO, UTC.
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
