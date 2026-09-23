from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.observation.evidence import once_each
from sro.application.observation.shots import frame_of, frames_by_instant, stored_shots
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.recording.media import PLAYBACK_TTL
from sro.domain.observation.batch import ObservationBatch
from sro.domain.shared.identifiers import BatchId
from sro.domain.skill.workflow import ordered_cites


@dataclass(frozen=True, slots=True)
class PlayableShot:
    url: str
    content_type: str


class ReadShots:
    def __init__(self, uow: UnitOfWork, blobs: BlobStore) -> None:
        self._uow = uow
        self._blobs = blobs

    async def execute(self, ctx: RequestContext, *, workflow_id: str) -> Mapping[str, PlayableShot]:
        async with self._uow as uow:
            workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)
            cited = tuple(dict.fromkeys(ordered_cites(workflow)))
            gestures = await uow.gestures.gestures_for(ctx.tenant_id, ids=cited) if cited else ()
            batches: dict[str, ObservationBatch] = {}
            for batch_id in dict.fromkeys(gesture.batch_id for gesture in gestures):
                batch = await uow.observations.get(ctx.tenant_id, BatchId(batch_id))
                if batch is not None:
                    batches[batch_id] = batch

        shots: dict[str, PlayableShot] = {}
        for batch_id, batch in batches.items():
            found = await stored_shots(self._blobs, batch)
            if not found:
                continue
            try:
                frames = frames_by_instant(once_each(await self._blobs.read(batch.uri)))
            except (KeyError, OSError):
                continue
            for gesture in gestures:
                if gesture.batch_id != batch_id:
                    continue
                ordinal = frames.get(gesture.at)
                if ordinal is None:
                    continue
                shot = frame_of(found, ordinal)
                if shot is None:
                    continue
                url = await self._blobs.presigned_url_for_uri(shot.uri, expires_in=PLAYBACK_TTL)
                if url is not None:
                    shots[gesture.id] = PlayableShot(url=url, content_type=shot.content_type)
        return shots
