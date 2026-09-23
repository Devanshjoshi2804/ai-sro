"""Teaching-mode evidence: observation batches that name a demonstration.

What has to hold is that the evidence is attributable — that a batch says which
demonstration it belongs to, and that the browser it came from is the one that
was asked. Evidence nobody can attribute is indistinguishable from an ordinary
morning's browsing.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.application.context import RequestContext
from sro.application.observation.ingest import IngestObservation, ObservationRefused
from sro.application.observation.policy import SetObservationPolicy
from sro.domain.observation.batch import CaptureMode
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import BatchId, DeviceId, RecordingId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SECRET = "what-this-browser-proves-itself-with"  # noqa: S105 -- not a credential
LAPTOP = DeviceId("dev-1")
OTHER = DeviceId("dev-2")


def _gesture(at: float = 1_787_654_321.5) -> dict[str, object]:
    return {
        "kind": "gesture",
        "gesture": {
            "kind": "click",
            "target": {"tag": "button", "name": "Save", "secret": False},
            "value": None,
            "secret": False,
            "modifiers": [],
            "at": at,
            "url": "https://wms.example/orders",
        },
        "tab_id": 8,
        "frame_url": "https://wms.example/orders",
    }


async def _device(uow: FakeUnitOfWork, device_id: DeviceId = LAPTOP) -> None:
    await uow.devices.add(
        AgentDevice(
            id=device_id,
            tenant_id=f.TENANT,
            principal_id=f.OPERATOR,
            label="laptop",
            extension_version="0.1.0",
            registered_at=datetime(2020, 1, 1, tzinfo=UTC),
            last_seen_at=datetime(2020, 1, 1, tzinfo=UTC),
            secret=SECRET,
        )
    )
    await SetObservationPolicy(uow).execute(CTX, policy=ObservationPolicy().enabled())


async def _recording(uow: FakeUnitOfWork, *, device_id: DeviceId | None = LAPTOP) -> Recording:
    recording = Recording(
        id=RecordingId("rec-1"),
        tenant_id=f.TENANT,
        demonstrator=f.OPERATOR,
        started_at=datetime(2026, 8, 25, 9, 0, tzinfo=UTC),
        device_id=device_id,
    )
    await uow.recordings.add(recording)
    return recording


def _ingest(uow: FakeUnitOfWork, blobs: FakeBlobStore) -> IngestObservation:
    return IngestObservation(uow, blobs, FakeClock())


async def test_a_teaching_batch_is_filed_against_the_demonstration_it_shows() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _device(uow)
    await _recording(uow)

    await _ingest(uow, blobs).execute(
        CTX,
        device_id=LAPTOP,
        secret=SECRET,
        batch_id=BatchId("bat-1"),
        started_at=datetime(2026, 8, 25, 9, 1, tzinfo=UTC),
        ended_at=datetime(2026, 8, 25, 9, 2, tzinfo=UTC),
        mode=CaptureMode.TEACHING,
        events=[_gesture()],
        recording_id=RecordingId("rec-1"),
    )

    stored = await uow.observations.for_recording(f.TENANT, RecordingId("rec-1"))
    assert [batch.id.value for batch in stored] == ["bat-1"]


async def test_teaching_evidence_that_names_no_demonstration_is_refused() -> None:
    """It would be indistinguishable from an ordinary morning's browsing, and
    the operator was asked to show the system something specific."""
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _device(uow)

    with pytest.raises(ObservationRefused, match="names its demonstration"):
        await _ingest(uow, blobs).execute(
            CTX,
            device_id=LAPTOP,
            secret=SECRET,
            batch_id=BatchId("bat-1"),
            started_at=datetime(2026, 8, 25, 9, 1, tzinfo=UTC),
            ended_at=datetime(2026, 8, 25, 9, 2, tzinfo=UTC),
            mode=CaptureMode.TEACHING,
            events=[_gesture()],
        )


async def test_ordinary_browsing_cannot_be_filed_as_a_demonstration() -> None:
    """The opposite mistake, and the worse one: a passive batch named against a
    recording would teach a skill from work nobody meant to show."""
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _device(uow)
    await _recording(uow)

    with pytest.raises(ObservationRefused, match="a passive one does not"):
        await _ingest(uow, blobs).execute(
            CTX,
            device_id=LAPTOP,
            secret=SECRET,
            batch_id=BatchId("bat-1"),
            started_at=datetime(2026, 8, 25, 9, 1, tzinfo=UTC),
            ended_at=datetime(2026, 8, 25, 9, 2, tzinfo=UTC),
            mode=CaptureMode.PASSIVE,
            events=[_gesture()],
            recording_id=RecordingId("rec-1"),
        )


async def test_another_browser_cannot_upload_into_your_demonstration() -> None:
    """A credential is not ownership of somebody else's demonstration, and two
    devices filling one recording is a task nobody actually performed."""
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _device(uow, OTHER)
    await _recording(uow, device_id=LAPTOP)

    with pytest.raises(ObservationRefused, match="different browser"):
        await _ingest(uow, blobs).execute(
            CTX,
            device_id=OTHER,
            # Its own secret: this browser is who it says it is, and is still
            # refused. Proving you are yourself is not ownership of somebody
            # else's demonstration.
            secret=SECRET,
            batch_id=BatchId("bat-1"),
            started_at=datetime(2026, 8, 25, 9, 1, tzinfo=UTC),
            ended_at=datetime(2026, 8, 25, 9, 2, tzinfo=UTC),
            mode=CaptureMode.TEACHING,
            events=[_gesture()],
            recording_id=RecordingId("rec-1"),
        )


async def test_a_sealed_demonstration_takes_nothing_more() -> None:
    """Skill provenance cites recordings. One that could still grow after it
    was reviewed is a review of something else."""
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _device(uow)
    recording = await _recording(uow)
    recording.append_frame(f.frame())
    recording.name_objective(f.objective())
    recording.seal(datetime(2026, 8, 25, 9, 30, tzinfo=UTC))
    await uow.recordings.save(recording)

    with pytest.raises(ObservationRefused, match="already been sealed"):
        await _ingest(uow, blobs).execute(
            CTX,
            device_id=LAPTOP,
            secret=SECRET,
            batch_id=BatchId("bat-2"),
            started_at=datetime(2026, 8, 25, 9, 31, tzinfo=UTC),
            ended_at=datetime(2026, 8, 25, 9, 32, tzinfo=UTC),
            mode=CaptureMode.TEACHING,
            events=[_gesture()],
            recording_id=RecordingId("rec-1"),
        )
