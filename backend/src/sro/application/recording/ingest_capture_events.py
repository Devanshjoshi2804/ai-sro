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
    orphaned_requests: int


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
            for frame in assembled.frames:
                recording.append_frame(frame)
            await uow.recordings.save(recording)
            await uow.commit()

        return IngestResult(
            frames_added=len(assembled.frames),
            total_frames=len(recording.frames),
            orphaned_requests=assembled.orphaned_requests,
        )
