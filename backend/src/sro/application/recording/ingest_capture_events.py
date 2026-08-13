"""Fold a batch of capture events into a live recording."""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.capture.assemble import assemble_frames
from sro.application.capture.events import CaptureEvent
from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import RecordingId


@dataclass(frozen=True, slots=True)
class IngestResult:
    frames_added: int
    total_frames: int
    absorbed_requests: int
    """Calls attached to the previous action because they finished after a drain."""

    orphaned_requests: int
    """Calls with no action to attach to at all: page-load noise."""


class IngestCaptureEvents:
    """Append-only, so a retried batch duplicates rather than corrupts.

    Duplication is visible in the review UI; a rewritten frame would not be.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        events: list[CaptureEvent],
    ) -> IngestResult:
        assembled = assemble_frames(events)

        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)
            # Absorb before appending: unattached traffic precedes this batch's
            # actions, so it belongs to the frame that was already the last one.
            absorbed = recording.absorb_late_evidence(requests=assembled.unattached_requests)
            for frame in assembled.frames:
                recording.append_frame(frame)
            await uow.recordings.save(recording)
            await uow.commit()

        return IngestResult(
            frames_added=len(assembled.frames),
            total_frames=len(recording.frames),
            absorbed_requests=assembled.unattached_count if absorbed else 0,
            orphaned_requests=0 if absorbed else assembled.unattached_count,
        )
