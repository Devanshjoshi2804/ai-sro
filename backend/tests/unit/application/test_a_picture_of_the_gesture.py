"""A learned recording carries the pictures of the gestures it describes.

A screenshot taken during passive capture has no row. It is keyed by the
gesture's position within its batch, as the recorder counted it, and nothing
writes that join down -- so every test here is about the counting. A picture on
the wrong frame is worse evidence than no picture at all: nothing about it
looks wrong.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.observation.teach import TeachCandidate
from sro.domain.observation.batch import CaptureMode, ObservationBatch, RejectedEvent
from sro.domain.observation.candidate import Episode, TaskCandidate
from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.identifiers import BatchId, CandidateId, DeviceId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS = "https://wms.acme.test"
START = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
KEY = f"{f.TENANT}/{f.OPERATOR}/2026-03-01/bat-1.ndjson"
URI = f"s3://sro-artifacts/{KEY}"
SHOTS = f"{f.TENANT}/{f.OPERATOR}/2026-03-01/bat-1/screenshot"


class _NoUnderstanding:
    async def execute(
        self, ctx: RequestContext, *, recording_id: object, name: str | None = None
    ) -> object:
        raise InductionFailed("the evidence is too thin")


def _gesture(seconds: float, *, kind: str = "click", name: str = "Save") -> dict[str, object]:
    return {
        "kind": "gesture",
        "gesture": {
            "kind": kind,
            "at": (START + timedelta(seconds=seconds)).timestamp(),
            "url": f"{WMS}/suppliers",
            "target": {"tag": "button", "name": name, "cssPath": f"div > button.{name}"},
        },
    }


def _call(seconds: float) -> dict[str, object]:
    return {
        "kind": "request",
        "request": {
            "request_id": f"r{seconds}",
            "method": "POST",
            "url": f"{WMS}/api/suppliers",
            "resource_type": "xhr",
            "started_at": (START + timedelta(seconds=seconds)).isoformat(),
            "status": 200,
            "request_headers": {"content-type": "application/json"},
        },
    }


async def _taught(
    events: Sequence[dict[str, object]],
    *,
    photographed: Sequence[int] = (),
    rejected: Sequence[RejectedEvent] = (),
    window: float = 60,
) -> tuple[FakeUnitOfWork, object]:
    """One episode of one batch, taught, with pictures for the named gestures.

    ``photographed`` names ordinals the way the recorder numbers them -- its
    own count over every gesture line in the batch -- which is exactly the
    thing under test.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    payload = b"".join(json.dumps(event).encode() + b"\n" for event in events)
    blobs.objects[KEY] = payload
    for ordinal in photographed:
        blobs.objects[f"{SHOTS}/{ordinal:05d}.png"] = b"PNG" * ordinal + b"PNG"

    await uow.observations.add(
        ObservationBatch(
            id=BatchId("bat-1"),
            tenant_id=f.TENANT,
            device_id=DeviceId("dev-1"),
            principal_id=f.OPERATOR,
            mode=CaptureMode.PASSIVE,
            started_at=START,
            ended_at=START + timedelta(minutes=1),
            received_at=START,
            uri=URI,
            event_count=len(events),
            byte_count=len(payload),
            rejected=tuple(rejected),
        )
    )
    candidate = TaskCandidate(
        id=CandidateId("cnd-1"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        signature="POST api/suppliers",
        host="wms.acme.test",
        title="Create suppliers on wms.acme.test",
        episodes=(
            Episode(
                started_at=START,
                ended_at=START + timedelta(seconds=window),
                host="wms.acme.test",
                batch_ids=(BatchId("bat-1"),),
                gestures=1,
                calls=1,
            ),
        ),
    )
    await uow.candidates.add(candidate)

    teach = TeachCandidate(
        uow,
        blobs,
        FakeClock(START),
        FakeIdFactory(),
        _NoUnderstanding(),  # type: ignore[arg-type]
        None,
    )
    taught = await teach.execute(CTX, candidate_id=candidate.id)
    assert taught.recording_id is not None
    return uow, taught.recording_id


def _shots(recording: object) -> dict[int, str]:
    return {
        artifact.frame_index: artifact.uri
        for artifact in recording.artifacts  # type: ignore[attr-defined]
        if artifact.kind is ArtifactKind.SCREENSHOT
    }


async def test_a_learned_recording_carries_the_picture_of_each_gesture() -> None:
    uow, recording_id = await _taught(
        [_gesture(1, name="Open"), _call(2), _gesture(3, name="Save"), _call(4)],
        photographed=(0, 1),
    )
    recording = await uow.recordings.get(f.TENANT, recording_id)

    assert len(recording.frames) == 2
    assert _shots(recording) == {
        0: f"s3://sro-artifacts/{SHOTS}/00000.png",
        1: f"s3://sro-artifacts/{SHOTS}/00001.png",
    }
    # The size is the store's, not a guess: it is what the Artifacts tab shows.
    picture = next(a for a in recording.artifacts if a.frame_index == 1)
    assert picture.size_bytes == len(b"PNG" * 1 + b"PNG")
    assert picture.content_type == "image/png"


async def test_a_gesture_nobody_photographed_leaves_its_frame_without_one() -> None:
    # The per-minute cap, a background tab, a trim for the byte budget: the
    # recorder still counts the gesture, so the picture after it must not
    # slide back onto the frame that went unillustrated.
    uow, recording_id = await _taught(
        [_gesture(1, name="Open"), _call(2), _gesture(3, name="Save"), _call(4)],
        photographed=(1,),
    )
    recording = await uow.recordings.get(f.TENANT, recording_id)

    assert _shots(recording) == {1: f"s3://sro-artifacts/{SHOTS}/00001.png"}


async def test_a_gesture_outside_the_episode_still_counts_for_the_numbering() -> None:
    # The recorder numbers pictures over the whole batch; an episode is a slice
    # of it. Counting only the gestures this episode kept would hand this
    # frame 00000 -- a picture of a screen from before the task began.
    uow, recording_id = await _taught(
        [_gesture(-30, name="Elsewhere"), _gesture(1, name="Save"), _call(2)],
        photographed=(0, 1),
    )
    recording = await uow.recordings.get(f.TENANT, recording_id)
    assert len(recording.frames) == 1

    assert _shots(recording) == {0: f"s3://sro-artifacts/{SHOTS}/00001.png"}


async def test_a_scrolled_past_gesture_does_not_shift_the_pictures() -> None:
    # A scroll is a gesture to the recorder and not a step to assembly. The
    # picture numbered against it must not land on the click that follows.
    uow, recording_id = await _taught(
        [_gesture(1, kind="scroll", name="Down"), _gesture(2, name="Save"), _call(3)],
        photographed=(0, 1),
    )
    recording = await uow.recordings.get(f.TENANT, recording_id)

    assert len(recording.frames) == 1
    assert _shots(recording) == {0: f"s3://sro-artifacts/{SHOTS}/00001.png"}


async def test_a_batch_the_server_filtered_gets_no_pictures_rather_than_wrong_ones() -> None:
    # `admit` dropped something the recorder had already counted, so the
    # gestures stored here are not the gestures the pictures were numbered
    # against, and which ones went is not recoverable from a RejectedEvent.
    uow, recording_id = await _taught(
        [_gesture(1, name="Open"), _call(2), _gesture(3, name="Save"), _call(4)],
        photographed=(0, 1),
        rejected=(RejectedEvent(index=0, reason="an excluded host"),),
    )
    recording = await uow.recordings.get(f.TENANT, recording_id)

    assert _shots(recording) == {}
