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
    batch_id: BatchId
    ordinal: int


@dataclass(frozen=True, slots=True)
class Shot:
    uri: str
    content_type: str
    size_bytes: int


def numbered(payload: bytes) -> Iterator[tuple[int | None, Mapping[str, object]]]:
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
    if batch.rejected:
        return {}
    found: dict[str, int] = {}
    for prefix in artifact_prefixes(batch):
        found.update(await blobs.list_prefix(f"{prefix}{ArtifactKind.SCREENSHOT.value}/"))
    return found


def frame_of(found: Mapping[str, int], ordinal: int) -> Shot | None:
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
