"""Cutting a day of watching into pieces of work, and clustering the repeats.

No model decides any of this. The same evidence produces the same candidates
every time, which is what lets an operator argue with one by reading it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sro.application.context import RequestContext
from sro.application.observation.ingest import IngestObservation
from sro.application.observation.mine import MineObservations, title_for
from sro.application.observation.policy import SetObservationPolicy
from sro.application.observation.segment import read, segment
from sro.domain.observation.batch import CaptureMode
from sro.domain.observation.candidate import WORTH_OFFERING
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.identifiers import BatchId, DeviceId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS = "https://wms.acme.test"
START = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)


def _gesture(at: datetime, url: str = f"{WMS}/suppliers") -> dict[str, object]:
    return {
        "kind": "gesture",
        "gesture": {
            "kind": "click",
            "at": at.timestamp(),
            "url": url,
            "target": {"tag": "button", "cssPath": "div > button"},
        },
    }


def _call(at: datetime, method: str, path: str) -> dict[str, object]:
    return {
        "kind": "request",
        "request": {
            "request_id": f"r{at.timestamp()}",
            "method": method,
            "url": f"{WMS}{path}",
            "resource_type": "xhr",
            "started_at": at.isoformat(),
            "status": 200,
        },
    }


def _doing(at: datetime, supplier: str) -> list[dict[str, object]]:
    """One doing of "create a supplier": look at the list, fill it in, save."""
    return [
        _gesture(at),
        _call(at + timedelta(seconds=1), "GET", "/api/suppliers"),
        _gesture(at + timedelta(seconds=20)),
        _call(at + timedelta(seconds=41), "POST", "/api/suppliers"),
        _call(at + timedelta(seconds=42), "GET", f"/api/suppliers/{supplier}"),
    ]


def _payload(events: list[dict[str, object]]) -> bytes:
    return b"".join(json.dumps(event).encode() + b"\n" for event in events)


def test_a_pause_ends_a_piece_of_work_because_the_person_went_elsewhere() -> None:
    events = _doing(START, "S1") + _doing(START + timedelta(minutes=40), "S2")

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert len(found) == 2
    assert found[0].signature == found[1].signature


def test_two_doings_of_one_task_have_the_same_signature_despite_different_records() -> None:
    # /api/suppliers/S1 and /api/suppliers/S2 are the same step. Which record it
    # was is what induction exists to find; here it would only stop the two
    # being recognised as each other.
    first = segment(read(_payload(_doing(START, "S00099")), BatchId("bat-1")))
    second = segment(read(_payload(_doing(START, "S00412")), BatchId("bat-2")))

    assert first[0].signature == second[0].signature
    assert "POST api/suppliers" in first[0].signature


def test_reading_a_screen_is_not_a_piece_of_work() -> None:
    # Traffic with nobody touching anything is a page keeping itself alive.
    only_calls = [_call(START, "GET", "/api/suppliers"), _call(START, "GET", "/api/heartbeat")]

    assert segment(read(_payload(only_calls), BatchId("bat-1"))) == ()


def test_a_repeat_of_the_same_step_is_one_step_not_two() -> None:
    # A grid that pages twice is the same step done twice.
    events = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "GET", "/api/suppliers"),
        _call(START + timedelta(seconds=2), "GET", "/api/suppliers"),
        _call(START + timedelta(seconds=3), "POST", "/api/suppliers"),
    ]

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert found[0].signature == "GET api/suppliers → POST api/suppliers"


def test_a_title_says_what_changed_and_where() -> None:
    assert (
        title_for("GET api/suppliers → POST api/suppliers", "wms.acme.test")
        == "Create suppliers on wms.acme.test"
    )
    assert title_for("GET api/waves/*", "wms.acme.test") == "Read waves on wms.acme.test"


async def _stored(uow: FakeUnitOfWork, blobs: FakeBlobStore, doings: list[datetime]) -> None:
    await SetObservationPolicy(uow).execute(CTX, policy=ObservationPolicy().enabled())
    device = AgentDevice(
        id=DeviceId("dev-1"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        label="laptop",
        extension_version="0.1.0",
        registered_at=START,
        last_seen_at=START,
    )
    await uow.devices.add(device)

    ingest = IngestObservation(uow, blobs, FakeClock())
    for index, at in enumerate(doings):
        await ingest.execute(
            CTX,
            device_id=device.id,
            batch_id=BatchId(f"bat_{index}"),
            started_at=at,
            ended_at=at + timedelta(minutes=1),
            mode=CaptureMode.PASSIVE,
            events=_doing(at, f"S{index}"),
        )


async def test_the_same_task_three_times_becomes_one_candidate_worth_offering() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    doings = [START + timedelta(hours=hour) for hour in range(WORTH_OFFERING)]
    await _stored(uow, blobs, doings)

    mined = await MineObservations(uow, blobs, FakeIdFactory()).execute(CTX, since=START)

    assert mined.candidates_new == 1
    candidate = next(iter(uow.candidates.rows.values()))
    assert candidate.times_seen == WORTH_OFFERING
    assert candidate.worth_offering is True
    assert candidate.median_duration_ms == 42_000


async def test_mining_the_same_window_again_does_not_count_anything_twice() -> None:
    # A count of how often something happened is the whole reason a candidate
    # exists, and the miner reads windows it has already read.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _stored(uow, blobs, [START, START + timedelta(hours=1)])
    miner = MineObservations(uow, blobs, FakeIdFactory())

    await miner.execute(CTX, since=START)
    again = await miner.execute(CTX, since=START)

    assert again.candidates_new == 0
    assert again.occurrences_new == 0
    assert next(iter(uow.candidates.rows.values())).times_seen == 2


async def test_something_done_once_is_not_offered() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _stored(uow, blobs, [START])

    await MineObservations(uow, blobs, FakeIdFactory()).execute(CTX, since=START)

    assert next(iter(uow.candidates.rows.values())).worth_offering is False


async def test_evidence_that_has_aged_out_does_not_fail_the_sweep() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _stored(uow, blobs, [START, START + timedelta(hours=1)])
    blobs.objects.clear()

    mined = await MineObservations(uow, blobs, FakeIdFactory()).execute(CTX, since=START)

    assert mined.episodes == 0
