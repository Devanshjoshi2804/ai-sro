from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sro.application.capture.assemble import assemble_frames
from sro.application.capture.decode import to_ax_graph, to_captured_request, to_input_action
from sro.application.capture.events import CaptureEvent, InputEvent, RequestEvent, SnapshotEvent
from sro.application.context import RequestContext
from sro.application.observation.evidence import once_each
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import RecordingId


class NothingDemonstrated(DomainError):
    code = "nothing_demonstrated"


@dataclass(frozen=True, slots=True)
class Assembled:
    recording_id: RecordingId
    frames: int
    batches: int


class AssembleDemonstration:
    def __init__(self, uow: UnitOfWork, blobs: BlobStore) -> None:
        self._uow = uow
        self._blobs = blobs

    async def execute(self, ctx: RequestContext, *, recording_id: RecordingId) -> Assembled:
        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)
            if recording.frames:
                return Assembled(recording_id=recording_id, frames=len(recording.frames), batches=0)
            batches = await uow.observations.for_recording(ctx.tenant_id, recording_id)

        events: list[CaptureEvent] = []
        for batch in batches:
            try:
                payload = once_each(await self._blobs.read(batch.uri))
            except (KeyError, OSError):
                continue
            events.extend(_events_in(payload))

        assembled = assemble_frames(events)
        if not assembled.frames:
            raise NothingDemonstrated(
                "nothing in this demonstration looks like a step; "
                "the browser may not have been capturing"
            )

        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)
            for frame in assembled.frames:
                recording.append_frame(frame)
            await uow.recordings.save(recording)
            await uow.commit()

        return Assembled(
            recording_id=recording_id, frames=len(assembled.frames), batches=len(batches)
        )


def _events_in(payload: bytes) -> Sequence[CaptureEvent]:
    kept: list[CaptureEvent] = []
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, Mapping):
            continue
        decoded = _one(event)
        if decoded is not None:
            kept.append(decoded)
    return kept


def _one(event: Mapping[str, object]) -> CaptureEvent | None:
    kind = event.get("kind")
    try:
        if kind == "gesture":
            gesture = event.get("gesture")
            if not isinstance(gesture, Mapping):
                return None
            at = _at(gesture.get("at"))
            return None if at is None else InputEvent(at=at, action=to_input_action(dict(gesture)))

        if kind == "request":
            request = event.get("request")
            if not isinstance(request, Mapping):
                return None
            return RequestEvent(request=to_captured_request(dict(request)))

        if kind == "snapshot":
            snapshot = event.get("snapshot")
            taken_at = event.get("taken_at")
            url = event.get("url")
            if not isinstance(snapshot, Mapping) or not isinstance(taken_at, str):
                return None
            graph = to_ax_graph(
                dict(snapshot),
                url=str(url or ""),
                taken_at=datetime.fromisoformat(taken_at).astimezone(UTC),
            )
            return None if graph is None else SnapshotEvent(snapshot=graph)
    except (KeyError, TypeError, ValueError):
        return None
    return None


def _at(value: object) -> datetime | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(float(value), tz=UTC)
