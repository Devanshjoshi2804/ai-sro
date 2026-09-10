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

Two callers, one counter. `teach` numbers the events it is assembling into a
recording; `read_shots` numbers a batch to answer which stored gesture each
picture belongs to. Both go through `numbered` below, because the recorder's
rule is one rule and a second spelling of it is a second answer to which
gesture a picture is of.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
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


@dataclass(frozen=True, slots=True)
class Shot:
    """One picture the store actually holds."""

    uri: str
    content_type: str
    size_bytes: int


def numbered(payload: bytes) -> Iterator[tuple[int | None, Mapping[str, object]]]:
    """Every readable line of a stored batch, each gesture carrying its frame
    number and everything else carrying ``None``.

    The counter walks every gesture line, including the ones the caller then
    drops -- out of the episode, unreadable, a scroll -- because that is what
    the recorder counted when it numbered the pictures (`upload.js`,
    ``framesOf``). Counting only the surviving gestures slides every later
    picture onto the wrong one.
    """
    ordinal = -1
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, Mapping):
            continue
        if event.get("kind") == "gesture":
            ordinal += 1
            yield ordinal, event
        else:
            yield None, event


def frames_by_instant(payload: bytes) -> Mapping[float, int]:
    """Each gesture's frame number in this batch, keyed by the instant it
    happened.

    For the reader that has `Gesture` rows rather than the payload's own
    lines. The two share no id -- `correlate` mints a gesture id this payload
    never saw -- so the browser's clock is the only thing both sides carry.

    An instant two gestures share is dropped rather than guessed at, which is
    this module's rule everywhere: a picture hung on the wrong gesture is
    worse evidence than no picture, because nothing about it looks wrong.
    """
    seen: dict[float, int] = {}
    twice: set[float] = set()
    for ordinal, event in numbered(payload):
        if ordinal is None:
            continue
        gesture = event.get("gesture")
        if not isinstance(gesture, Mapping):
            continue
        at = gesture.get("at")
        if not isinstance(at, int | float):
            continue
        if float(at) in seen:
            twice.add(float(at))
        seen[float(at)] = ordinal
    for at in twice:
        del seen[at]
    return seen


async def stored_shots(blobs: BlobStore, batch: ObservationBatch) -> Mapping[str, int]:
    """Every screenshot the store holds for one batch, by URI, with its size.

    Nothing at all for a batch the server filtered: the recorder counted the
    gestures it sent, `admit` then dropped some of them, so the gestures
    stored here are not the gestures the pictures were numbered against. Which
    ones went is not recoverable from a `RejectedEvent`, so this batch's
    pictures are left behind rather than hung on whichever gesture the shifted
    count lands on.
    """
    if batch.rejected:
        return {}
    found: dict[str, int] = {}
    for prefix in artifact_prefixes(batch):
        found.update(await blobs.list_prefix(f"{prefix}{ArtifactKind.SCREENSHOT.value}/"))
    return found


def frame_of(found: Mapping[str, int], ordinal: int) -> Shot | None:
    """The picture numbered for this gesture, or ``None`` when none was taken.

    Absent is the ordinary answer: the per-minute cap, a background tab, a
    trim for the byte budget.
    """
    for uri, size in found.items():
        name, _, suffix = uri.rpartition("/")[2].partition(".")
        if name == f"{ordinal:05d}":
            return Shot(
                uri=uri,
                content_type=_CONTENT_TYPES.get(f".{suffix}", "image/png"),
                size_bytes=size,
            )
    return None


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
        listings[batch.id] = await stored_shots(blobs, batch)

    artifacts: list[MediaArtifact] = []
    for index, source in enumerate(sources):
        ref = refs.get(id(source))
        if ref is None:
            continue
        shot = frame_of(listings.get(ref.batch_id, {}), ref.ordinal)
        if shot is None:
            continue
        artifacts.append(
            MediaArtifact(
                kind=ArtifactKind.SCREENSHOT,
                uri=shot.uri,
                content_type=shot.content_type,
                size_bytes=shot.size_bytes,
                created_at=now,
                frame_index=index,
            )
        )
    return tuple(artifacts)
