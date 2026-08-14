"""Store a capture artifact and attach it to the recording."""

from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from datetime import datetime, timedelta

from sro.application.context import RequestContext
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.ports.transcription import TranscribedSegment, Transcriber
from sro.domain.recording.artifact import ArtifactKind, MediaArtifact
from sro.domain.recording.narration import NarrationSegment
from sro.domain.shared.identifiers import RecordingId, TenantId


def _place(
    segments: tuple[TranscribedSegment, ...], recorded_from: datetime
) -> tuple[NarrationSegment, ...]:
    """Offsets into the audio become points on the recording's clock."""
    return tuple(
        NarrationSegment(
            starts_at=recorded_from + timedelta(milliseconds=segment.start_ms),
            ends_at=recorded_from + timedelta(milliseconds=segment.end_ms),
            text=segment.text,
        )
        for segment in segments
    )


def artifact_key(
    tenant_id: TenantId, recording_id: RecordingId, kind: ArtifactKind, content_type: str
) -> str:
    """Object-store key. Tenant-first so bucket policies can scope per tenant."""
    extension = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".bin"
    return f"{tenant_id}/{recording_id}/{kind.value}{extension}"


@dataclass(frozen=True, slots=True)
class AttachResult:
    uri: str
    transcript_uri: str | None


class AttachArtifact:
    def __init__(
        self,
        uow: UnitOfWork,
        blobs: BlobStore,
        clock: Clock,
        transcriber: Transcriber,
    ) -> None:
        self._uow = uow
        self._blobs = blobs
        self._clock = clock
        self._transcriber = transcriber

    async def execute(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        kind: ArtifactKind,
        data: bytes,
        content_type: str,
        duration_ms: int | None = None,
        recorded_from: datetime | None = None,
    ) -> AttachResult:
        """``recorded_from`` is when the microphone started, which is the only
        thing that turns a transcript's offsets into times a frame can be
        matched against."""
        now = self._clock.now()

        key = artifact_key(ctx.tenant_id, recording_id, kind, content_type)
        uri = await self._blobs.put(key, data, content_type=content_type)

        artifacts = [
            MediaArtifact(
                kind=kind,
                uri=uri,
                content_type=content_type,
                size_bytes=len(data),
                created_at=now,
                duration_ms=duration_ms,
            )
        ]

        transcript_uri: str | None = None
        segments: tuple[NarrationSegment, ...] = ()
        if kind is ArtifactKind.AUDIO and self._transcriber.available:
            transcribed = await self._transcriber.transcribe(data, content_type=content_type)
            segments = _place(transcribed, recorded_from or now)
            transcript_key = artifact_key(
                ctx.tenant_id, recording_id, ArtifactKind.TRANSCRIPT, "application/json"
            )
            payload = json.dumps(
                [
                    {
                        "starts_at": segment.starts_at.isoformat(),
                        "ends_at": segment.ends_at.isoformat(),
                        "text": segment.text,
                    }
                    for segment in segments
                ]
            ).encode("utf-8")
            transcript_uri = await self._blobs.put(
                transcript_key, payload, content_type="application/json"
            )
            artifacts.append(
                MediaArtifact(
                    kind=ArtifactKind.TRANSCRIPT,
                    uri=transcript_uri,
                    content_type="application/json",
                    size_bytes=len(payload),
                    created_at=now,
                )
            )

        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)
            for artifact in artifacts:
                recording.attach_artifact(artifact)
            if segments:
                recording.attach_narration(segments)
            await uow.recordings.save(recording)
            await uow.commit()

        return AttachResult(uri=uri, transcript_uri=transcript_uri)

    async def record_stored_blob(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        kind: ArtifactKind,
        uri: str,
        content_type: str,
        size_bytes: int,
        duration_ms: int | None = None,
        frame_index: int | None = None,
        label: str | None = None,
    ) -> None:
        """Attach a blob the capture adapter already wrote.

        Screenshots and oversized payloads are stored as they are captured --
        holding them in memory until the recording ends would defeat the point.
        This records their existence without moving the bytes again.
        """
        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)
            recording.attach_artifact(
                MediaArtifact(
                    kind=kind,
                    uri=uri,
                    content_type=content_type,
                    size_bytes=size_bytes,
                    created_at=self._clock.now(),
                    duration_ms=duration_ms,
                    frame_index=frame_index,
                    label=label,
                )
            )
            await uow.recordings.save(recording)
            await uow.commit()
