"""The screenshots behind the gestures one workflow cites.

The recorder photographed an operator's screen as it watched, and every one of
those pictures is in the object store keyed by
``tenant/principal/day/batch/screenshot/NNNNN.png`` -- and until this, nothing
read a single one of them back. A mined job's evidence was prose about clicks
nobody could see.

The join is `shots`': the number on a picture is the gesture's position in its
batch as the recorder counted it. What is different here is the side we start
from. `teach` walks a batch's stored lines and is holding the very events the
numbers were assigned to; this is holding `Gesture` rows, which carry ids
`correlate` minted and the payload never saw. So the batch is read back and
its gestures numbered again, and the two sides are matched on the browser's
clock -- the one value both carry. `frames_by_instant` drops an instant two
gestures share rather than guessing between them.

Tenant scoping is the whole of the security here, because a presigned URL is a
capability: whoever holds it reads that object without proving anything again.
Both reads are by `ctx.tenant_id` -- the workflow, then the batch -- and the
key a URL is minted for is built from the *batch's* tenant and principal by
`artifact_prefixes`. A batch belonging to somebody else is `None` and its
pictures are never reached.
"""

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
    """A picture of one gesture, addressed for a browser to fetch once."""

    url: str
    content_type: str


class ReadShots:
    """What a workflow's cited gestures looked like on the screen.

    Keyed by gesture id, and a gesture nobody photographed simply has no
    entry: the per-minute cap, a background tab, a batch the server filtered.
    An entry carrying nothing would make the console draw a broken picture
    where there was never one to draw.
    """

    def __init__(self, uow: UnitOfWork, blobs: BlobStore) -> None:
        self._uow = uow
        self._blobs = blobs

    async def execute(self, ctx: RequestContext, *, workflow_id: str) -> Mapping[str, PlayableShot]:
        async with self._uow as uow:
            # Tenant-scoped, and this is the whole of the 404: a workflow of
            # somebody else's is not found rather than read. `ReadEvidence`
            # beside it answers the same way, so the route this rides on says
            # one thing about an unknown job rather than two.
            workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)
            cited = tuple(dict.fromkeys(ordered_cites(workflow)))
            # Not a null check: `gestures_for` with no ids is `IN ()` against
            # Postgres, and a workflow that cites nothing is a real row.
            gestures = await uow.gestures.gestures_for(ctx.tenant_id, ids=cited) if cited else ()
            batches: dict[str, ObservationBatch] = {}
            for batch_id in dict.fromkeys(gesture.batch_id for gesture in gestures):
                batch = await uow.observations.get(ctx.tenant_id, BatchId(batch_id))
                if batch is not None:
                    batches[batch_id] = batch

        # Outside the transaction, as `GetRecordingMedia` mints its links
        # outside one: what is left is object storage, and a database
        # connection held open across it is held for nothing.
        shots: dict[str, PlayableShot] = {}
        for batch_id, batch in batches.items():
            found = await stored_shots(self._blobs, batch)
            if not found:
                continue
            try:
                frames = frames_by_instant(once_each(await self._blobs.read(batch.uri)))
            except (KeyError, OSError):
                # The evidence aged out from under the job that cites it. The
                # other gestures still have their pictures.
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
                # Short-lived, and the same window playback uses: a link that
                # outlives the page it was drawn on is a copy of somebody's
                # screen that nobody is tracking.
                url = await self._blobs.presigned_url_for_uri(shot.uri, expires_in=PLAYBACK_TTL)
                if url is not None:
                    shots[gesture.id] = PlayableShot(url=url, content_type=shot.content_type)
        return shots
