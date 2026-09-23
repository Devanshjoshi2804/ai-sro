from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sro.application.context import RequestContext
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.identifiers import RecordingId

PLAYBACK_TTL = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class PlayableMedia:
    kind: ArtifactKind
    url: str
    content_type: str
    size_bytes: int
    duration_ms: int | None
    frame_index: int | None


class GetRecordingMedia:
    def __init__(self, uow: UnitOfWork, blobs: BlobStore) -> None:
        self._uow = uow
        self._blobs = blobs

    async def execute(
        self, ctx: RequestContext, *, recording_id: RecordingId
    ) -> tuple[PlayableMedia, ...]:
        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)

        playable = []
        for artifact in recording.artifacts:
            url = await self._blobs.presigned_url_for_uri(artifact.uri, expires_in=PLAYBACK_TTL)
            if url is None:
                continue
            playable.append(
                PlayableMedia(
                    kind=artifact.kind,
                    url=url,
                    content_type=artifact.content_type,
                    size_bytes=artifact.size_bytes,
                    duration_ms=artifact.duration_ms,
                    frame_index=artifact.frame_index,
                )
            )
        return tuple(playable)
