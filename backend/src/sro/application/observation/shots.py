"""The pictures an observed episode left behind, joined back to its gestures.

A screenshot taken during passive capture has no row of its own.
`StoreObservationArtifact` keys one by
``tenant/principal/day/batch/screenshot/NNNNN.png``, where ``NNNNN`` is the
gesture's position within its batch as the recorder counted it
(`new-chrome-extension/src/background/upload.js`, ``framesOf``). Nothing writes
that join down anywhere, so this reads it back: count a batch's gestures the
same way the recorder did, then ask the store which of them were photographed.

Without this, a skill learned from watching has an empty Artifacts tab and a
timeline of prose, while the pictures of the very gestures it describes sit in
the object store unreferenced.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.capture.events import InputEvent
from sro.application.observation.artifacts import artifact_prefixes
from sro.application.ports.blob import BlobStore
from sro.domain.observation.batch import ObservationBatch
from sro.domain.recording.artifact import ArtifactKind, MediaArtifact
from sro.domain.shared.identifiers import BatchId

_CONTENT_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@dataclass(frozen=True, slots=True)
class ShotRef:
    """Where a gesture's picture would be, if one was taken."""

    batch_id: BatchId
    ordinal: int
    """The gesture's position among its batch's gestures, counting from zero.

    Every gesture, not only the photographed ones -- that is the recorder's
    rule, and counting any other way slides every later picture onto the wrong
    gesture.
    """


async def pictures(
    blobs: BlobStore,
    *,
    batches: Sequence[ObservationBatch],
    sources: Sequence[InputEvent],
    refs: Mapping[int, ShotRef],
    now: datetime,
) -> tuple[MediaArtifact, ...]:
    """The screenshots for an assembled recording, in frame order.

    ``sources`` is `AssemblyResult.sources` -- the gesture each frame was
    opened by -- and ``refs`` is keyed by ``id()`` of those same objects.
    Identity rather than timestamp: two gestures can share an instant, and a
    picture attached to the wrong one is worse evidence than no picture, since
    nothing about it looks wrong.
    """
    listings: dict[BatchId, Mapping[str, int]] = {}
    for batch in batches:
        if batch.rejected:
            # The recorder counted the gestures it sent; `admit` then dropped
            # some of them, so the gestures stored here are not the gestures
            # the pictures were numbered against. Which ones went is not
            # recoverable from a `RejectedEvent`, so this batch's pictures are
            # left behind rather than hung on whichever gesture the shifted
            # count lands on.
            continue
        found: dict[str, int] = {}
        for prefix in artifact_prefixes(batch):
            found.update(await blobs.list_prefix(f"{prefix}{ArtifactKind.SCREENSHOT.value}/"))
        listings[batch.id] = found

    artifacts: list[MediaArtifact] = []
    for index, source in enumerate(sources):
        ref = refs.get(id(source))
        if ref is None:
            continue
        found = dict(listings.get(ref.batch_id, {}))
        for uri, size in found.items():
            name, _, suffix = uri.rpartition("/")[2].partition(".")
            if name != f"{ref.ordinal:05d}":
                continue
            artifacts.append(
                MediaArtifact(
                    kind=ArtifactKind.SCREENSHOT,
                    uri=uri,
                    content_type=_CONTENT_TYPES.get(f".{suffix}", "image/png"),
                    size_bytes=size,
                    created_at=now,
                    frame_index=index,
                )
            )
            break
    return tuple(artifacts)
