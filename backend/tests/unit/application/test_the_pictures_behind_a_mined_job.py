"""A mined job hands back the pictures of the gestures it cites.

991 screenshots were in the object store and nothing read one of them back.
The join has no row: a picture is numbered by its gesture's position in the
batch as the recorder counted it, and the `Gesture` rows a workflow cites
carry ids the stored batch never saw. So the numbering is redone over the
stored payload and the two sides are matched on the browser's clock.

Every test here is about that count, or about who is allowed to hold the link
it produces. A presigned URL is a capability -- whoever has it reads the
object without proving anything again -- so a picture handed to the wrong
tenant is not a display bug.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.observation.read_shots import ReadShots
from sro.application.recording.media import PLAYBACK_TTL
from sro.domain.observation.batch import CaptureMode, ObservationBatch, RejectedEvent
from sro.domain.observation.gesture import Action, Gesture
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import BatchId, DeviceId, PrincipalId, TenantId
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
RIVAL = RequestContext(tenant_id=TenantId("rival"), principal_id=PrincipalId("clerk@rival.test"))
WMS = "https://wms.acme.test"
START = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
BATCH = "bat-1"


def _where(tenant: TenantId) -> tuple[str, str, str]:
    """The three addresses one batch has: its events, its URI, its pictures.

    Built from the tenant on purpose. `artifact_prefixes` puts the batch's own
    tenant at the head of every key, so a read that took the tenant from
    anywhere but the batch it just proved would look for pictures that are not
    there -- and a read that took it from the path would find somebody else's.
    """
    stem = f"{tenant}/{f.OPERATOR}/2026-03-01/{BATCH}"
    return f"{stem}.ndjson", f"s3://sro-artifacts/{stem}.ndjson", f"{stem}/screenshot"


KEY, URI, SHOTS = _where(f.TENANT)
JOB = "wfl_zebra"

WHEN = [(START + timedelta(seconds=n)).timestamp() for n in (1, 2, 3)]
"""Three gestures in one batch, one second apart. The middle one is the one
nobody photographed, so a count that skipped it would hand the third gesture
the second picture -- and nothing about that answer looks wrong."""


def _line(at: float, *, name: str) -> bytes:
    return (
        json.dumps(
            {
                "kind": "gesture",
                "gesture": {
                    "kind": "click",
                    "at": at,
                    "url": f"{WMS}/suppliers",
                    "target": {"tag": "button", "name": name},
                },
            }
        ).encode()
        + b"\n"
    )


def _call_line(at: float) -> bytes:
    """A request line, which the recorder does not count. Present in every
    plant: a counter that numbered every line rather than every gesture line
    passes a payload of gestures alone."""
    return (
        json.dumps(
            {
                "kind": "request",
                "request": {
                    "request_id": f"req-{at}",
                    "method": "POST",
                    "url": f"{WMS}/api/suppliers",
                    "started_at": at,
                    "status": 200,
                },
            }
        ).encode()
        + b"\n"
    )


def _gesture(gesture_id: str, at: float, *, tenant: TenantId = f.TENANT) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=tenant.value,
        stream_id="str-1",
        batch_id=BATCH,
        at=at,
        url=f"{WMS}/suppliers",
        system="wms.acme.test",
        tab_id=7,
        frame_url=None,
        action=Action(kind="click", at=at, url=f"{WMS}/suppliers"),
    )


async def _planted(
    *,
    photographed: Sequence[int] = (0, 2),
    cites: Sequence[str] = ("ges-0", "ges-1", "ges-2"),
    rejected: Sequence[RejectedEvent] = (),
    tenant: TenantId = f.TENANT,
) -> tuple[ReadShots, FakeUnitOfWork, FakeBlobStore]:
    """One batch of three gestures, two of them photographed, cited by one job.

    ``photographed`` names ordinals the way the recorder numbers them -- its
    own count over every gesture line in the batch -- which is the thing under
    test.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    key, uri, shots = _where(tenant)
    blobs.objects[key] = b"".join(
        (
            _line(WHEN[0], name="Open"),
            _call_line(WHEN[0]),
            _line(WHEN[1], name="Code"),
            _line(WHEN[2], name="Save"),
        )
    )
    for ordinal in photographed:
        blobs.objects[f"{shots}/{ordinal:05d}.png"] = b"PNG" * (ordinal + 1)

    await uow.observations.add(
        ObservationBatch(
            id=BatchId(BATCH),
            tenant_id=tenant,
            device_id=DeviceId("dev-1"),
            principal_id=f.OPERATOR,
            mode=CaptureMode.PASSIVE,
            started_at=START,
            ended_at=START + timedelta(minutes=1),
            received_at=START,
            uri=uri,
            event_count=4,
            byte_count=len(blobs.objects[key]),
            rejected=tuple(rejected),
        )
    )
    await uow.gestures.add_gestures(
        tuple(_gesture(f"ges-{n}", WHEN[n], tenant=tenant) for n in range(3))
    )
    await uow.workflows.save(
        Workflow(
            id=JOB,
            tenant=tenant.value,
            title="create a supplier",
            narrative="open the screen, type the code, save",
            steps=[Step(order=0, says="do it", system="wms.acme.test", cites=list(cites))],
        )
    )
    return ReadShots(uow, blobs), uow, blobs


async def test_a_cited_gesture_gets_a_link_to_the_picture_of_it() -> None:
    read, _, _ = await _planted()

    shots = await read.execute(CTX, workflow_id=JOB)

    assert shots["ges-0"].url == (
        f"https://blobs.test/{SHOTS}/00000.png?expires={int(PLAYBACK_TTL.total_seconds())}"
    )
    assert shots["ges-0"].content_type == "image/png"


async def test_the_link_expires_as_soon_as_a_recordings_does() -> None:
    """A link to a picture of somebody's screen that outlives the page it was
    drawn on is a copy of the evidence nobody is tracking. Playback already
    decided how long that is; a second number here would be a second policy."""
    read, _, _ = await _planted()

    shots = await read.execute(CTX, workflow_id=JOB)

    assert f"expires={int(PLAYBACK_TTL.total_seconds())}" in shots["ges-0"].url
    assert timedelta(hours=1) >= PLAYBACK_TTL


async def test_a_gesture_nobody_photographed_is_absent_rather_than_empty() -> None:
    """The per-minute cap, a background tab, a trim for the byte budget. The
    console draws what it is given, and a key carrying nothing would have it
    draw a broken picture where there was never one to draw."""
    read, _, _ = await _planted()

    shots = await read.execute(CTX, workflow_id=JOB)

    assert "ges-1" not in shots
    assert sorted(shots) == ["ges-0", "ges-2"]


async def test_the_gesture_nobody_photographed_still_counts_for_the_numbering() -> None:
    """The recorder counts every gesture it sends, photographed or not. Count
    only the photographed ones and the third gesture is handed the second
    picture -- a real screenshot, of the wrong moment, with nothing about it to
    say so."""
    read, _, _ = await _planted()

    shots = await read.execute(CTX, workflow_id=JOB)

    assert shots["ges-2"].url.endswith(f"{SHOTS}/00002.png?expires=1800")


async def test_a_picture_of_a_gesture_this_job_does_not_cite_is_not_served() -> None:
    """The batch holds pictures of the whole afternoon. What the route answers
    is what this job's steps cite, which is how the evidence route already
    behaves for the gestures themselves."""
    read, _, _ = await _planted(cites=("ges-0",))

    shots = await read.execute(CTX, workflow_id=JOB)

    assert sorted(shots) == ["ges-0"]


async def test_a_batch_the_server_filtered_gets_no_pictures_rather_than_wrong_ones() -> None:
    """`admit` dropped an event the recorder had already counted, so the
    payload stored here is not what the pictures were numbered against, and
    which line went is not recoverable from a `RejectedEvent`."""
    read, _, _ = await _planted(rejected=(RejectedEvent(index=0, reason="an excluded host"),))

    assert await read.execute(CTX, workflow_id=JOB) == {}


async def test_another_tenants_job_is_not_found_rather_than_photographed() -> None:
    """404 and never a 403, which is what the evidence route beside this
    already answers: the caller holds a credential that was accepted, and
    telling them the job exists but is not theirs is the enumeration channel
    that route's docstring refuses to open.

    A URL is not withheld here so much as never minted: nothing this tenant
    does not own is read, so there is no key to sign.
    """
    read, _, _ = await _planted()

    with pytest.raises(NotFound):
        await read.execute(RIVAL, workflow_id=JOB)


async def test_the_pictures_of_another_tenants_batch_are_never_reached() -> None:
    """The job, its gestures and its batch all belong to `rival`, and `rival`
    is who asks -- so the answer is real. `acme` naming the same job id gets
    nothing: a presigned URL is a capability, and the batch read that mints
    one is scoped by the credential rather than by the id in the path.
    """
    read, _, _ = await _planted(tenant=TenantId("rival"))

    assert sorted(await read.execute(RIVAL, workflow_id=JOB)) == ["ges-0", "ges-2"]
    with pytest.raises(NotFound):
        await read.execute(CTX, workflow_id=JOB)


async def test_a_job_that_cites_nothing_is_an_answer_and_not_a_failure() -> None:
    read, _, _ = await _planted(cites=())

    assert await read.execute(CTX, workflow_id=JOB) == {}


async def test_evidence_that_aged_out_of_the_store_costs_nothing_but_its_pictures() -> None:
    """The batch row outlived the object it points at. A job whose evidence a
    retention rule has swept still answers -- without pictures -- rather than
    failing the whole read."""
    read, _, blobs = await _planted()
    del blobs.objects[KEY]

    assert await read.execute(CTX, workflow_id=JOB) == {}
