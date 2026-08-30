"""A browser proves it is itself before anything is filed under its name.

The tenant credential says who is asking and can never say which browser. Until
now the evidence paths took a device id from a request body and checked only
the tenant, so a colleague holding a valid token could file their own browsing
against somebody else's device -- and every candidate mined from it, every
skill induced from those, and every screenshot stored beside them would name
the wrong operator.

The attacker here is not a stranger. It is somebody who already has a
credential for this tenant, which is exactly why the tenant is not the check.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.observation.artifacts import StoreObservationArtifact
from sro.application.observation.ingest import IngestObservation
from sro.application.observation.policy import SetObservationPolicy
from sro.application.recording.start_recording import StartRecording
from sro.domain.observation.batch import CaptureMode
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.artifact import ArtifactKind
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import BatchId, DeviceId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
COLLEAGUE = RequestContext(tenant_id=f.TENANT, principal_id="other@acme.test")
MINE = DeviceId("dev-mine")
SECRET = "what-my-browser-proves-itself-with"  # noqa: S105 -- not a credential
A_GUESS = "a-guess"  # what a stranger presents
AT = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)

GESTURE: dict[str, object] = {
    "kind": "gesture",
    "gesture": {
        "kind": "click",
        "at": AT.timestamp(),
        "url": "https://wms.acme.test/waves",
        "target": {"tag": "button", "name": "Release", "cssPath": "div > button"},
    },
}


async def _ready(uow: FakeUnitOfWork) -> None:
    await uow.devices.add(
        AgentDevice(
            id=MINE,
            tenant_id=f.TENANT,
            principal_id=f.OPERATOR,
            label="laptop",
            extension_version="0.1.0",
            registered_at=AT,
            last_seen_at=AT,
            secret=SECRET,
        )
    )
    await SetObservationPolicy(uow).execute(CTX, policy=ObservationPolicy().enabled())


async def _ingest(uow: FakeUnitOfWork, blobs: FakeBlobStore, secret: str) -> object:
    return await IngestObservation(uow, blobs, FakeClock()).execute(
        CTX,
        device_id=MINE,
        secret=secret,
        batch_id=BatchId("bat-1"),
        started_at=AT,
        ended_at=AT + timedelta(minutes=1),
        mode=CaptureMode.PASSIVE,
        events=[GESTURE],
    )


async def test_a_batch_filed_against_a_browser_that_cannot_prove_itself_is_refused() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _ready(uow)

    with pytest.raises(NotFound):
        await _ingest(uow, blobs, A_GUESS)

    assert await uow.observations.get(f.TENANT, BatchId("bat-1")) is None
    assert blobs.objects == {}


async def test_the_browser_it_says_it_is_files_its_own_evidence() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _ready(uow)

    ingested = await _ingest(uow, blobs, SECRET)

    assert ingested.accepted == 1  # type: ignore[attr-defined]


async def test_a_colleagues_valid_credential_is_not_enough_to_file_under_your_device() -> None:
    # The whole point. Same tenant, real credential, somebody else's device id
    # -- and without that browser's secret it is a stranger.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _ready(uow)

    with pytest.raises(NotFound):
        await IngestObservation(uow, blobs, FakeClock()).execute(
            COLLEAGUE,
            device_id=MINE,
            secret="",
            batch_id=BatchId("bat-1"),
            started_at=AT,
            ended_at=AT + timedelta(minutes=1),
            mode=CaptureMode.PASSIVE,
            events=[GESTURE],
        )


async def test_a_refused_browser_is_told_the_same_thing_as_one_that_never_existed() -> None:
    # Absent, wrong, and belonging to somebody else are one answer, so a caller
    # holding an id it should not have learns nothing from the difference.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _ready(uow)

    with pytest.raises(NotFound) as wrong:
        await _ingest(uow, blobs, A_GUESS)
    with pytest.raises(NotFound) as absent:
        await IngestObservation(uow, blobs, FakeClock()).execute(
            CTX,
            device_id=DeviceId("dev-never-registered"),
            secret=A_GUESS,
            batch_id=BatchId("bat-2"),
            started_at=AT,
            ended_at=AT + timedelta(minutes=1),
            mode=CaptureMode.PASSIVE,
            events=[GESTURE],
        )

    assert str(wrong.value).replace(str(MINE), "X") == str(absent.value).replace(
        "dev-never-registered", "X"
    )


async def test_a_screenshot_cannot_be_stored_against_a_browser_you_cannot_prove() -> None:
    # A picture of somebody's screen, filed under their name.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _ready(uow)
    store = StoreObservationArtifact(uow, blobs, FakeClock())

    with pytest.raises(NotFound):
        await store.execute(
            CTX,
            device_id=MINE,
            secret=A_GUESS,
            batch_id=BatchId("bat-1"),
            kind=ArtifactKind.SCREENSHOT,
            data=b"PNG",
            content_type="image/png",
            frame_index=0,
        )

    assert blobs.objects == {}


async def test_a_demonstration_cannot_be_started_in_a_browser_you_cannot_prove() -> None:
    # A demonstration is the strongest evidence here -- it is what a skill is
    # induced from -- so naming somebody else's browser to perform it is
    # refused before the recording exists.
    uow = FakeUnitOfWork()
    await _ready(uow)
    start = StartRecording(uow, None, FakeClock(), FakeIdFactory(), None)  # type: ignore[arg-type]

    with pytest.raises(NotFound):
        await start.execute(CTX, device_id=MINE, device_secret=A_GUESS, label="teaching")

    assert uow.recordings.rows == {}
