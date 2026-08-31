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


def test_working_through_a_pile_without_stopping_is_still_several_pieces() -> None:
    """The blind spot a pause-based boundary has.

    Somebody clearing a queue takes the next job off it without stopping, so
    three doings arrive as one run with no gap in it -- counted once, under a
    signature that is the task three times over. The most repetitive work in the
    warehouse was the work this was least able to see, and a fourth doing that
    afternoon would have made a different candidate again.
    """
    events = [
        *_doing(START, "S1"),
        *_doing(START + timedelta(seconds=90), "S2"),
        *_doing(START + timedelta(seconds=180), "S3"),
    ]

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert len(found) == 3
    assert len({piece.signature for piece in found}) == 1
    # Each keeps its own evidence, which is what teaching one of them reads.
    assert [piece.episode.started_at for piece in found] == [
        START,
        START + timedelta(seconds=90),
        START + timedelta(seconds=180),
    ]


def test_a_task_that_visits_a_screen_twice_is_not_cut_in_half() -> None:
    """Cutting on "it came back to where it started" would do this wrongly: a
    task that lists, writes and lists again returns to its first call in the
    middle of itself. Only a whole repetition is a repetition."""
    events = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "GET", "/api/suppliers"),
        _gesture(START + timedelta(seconds=20)),
        _call(START + timedelta(seconds=41), "POST", "/api/suppliers"),
        _call(START + timedelta(seconds=42), "GET", "/api/suppliers"),
    ]

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert len(found) == 1


def test_a_detour_between_two_doings_belongs_to_one_of_them_not_to_both() -> None:
    """Two doings with a wander in the middle do not repeat exactly, so the
    period rule leaves them whole -- and the change rule cuts them anyway.

    The cut is at the second save, which is never an invented boundary: it is
    the moment the second task committed. The detour lands in the piece it
    happened in and colours neither signature, because a signature starts at
    the change.
    """
    events = [
        *_doing(START, "S1"),
        _gesture(START + timedelta(seconds=80)),
        _call(START + timedelta(seconds=81), "GET", "/api/labels"),
        *_doing(START + timedelta(seconds=90), "S2"),
    ]

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert len(found) == 2
    assert found[0].signature == found[1].signature, (
        "a detour between two doings made them two different tasks"
    )


def test_a_pile_the_operator_was_interrupted_in_the_middle_of_loses_nothing() -> None:
    """Two doings and the start of a third, cut at the changes.

    The unfinished third never got as far as saving, so it is what it looks
    like: somebody reading a list. It becomes its own piece rather than being
    swallowed by the doing before it or dropped -- evidence that belongs to
    nothing is evidence that quietly disappears.
    """
    events = [
        *_doing(START, "S1"),
        *_doing(START + timedelta(seconds=90), "S2"),
        _gesture(START + timedelta(seconds=180)),
        _call(START + timedelta(seconds=181), "GET", "/api/suppliers"),
    ]

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert [piece.signature for piece in found] == [
        "POST api/suppliers",
        "POST api/suppliers",
        "GET api/suppliers",
    ]
    assert found[-1].episode.ended_at == START + timedelta(seconds=181), "the tail was dropped"


def test_a_request_timestamp_missing_its_offset_is_skipped_not_crashed() -> None:
    # The protocol requires an offset; datetime.fromisoformat parses one
    # without it anyway, silently naive -- sorted() against a gesture's
    # always-aware, epoch-derived timestamp used to raise straight through it.
    events = [
        _gesture(START),
        {
            "kind": "request",
            "request": {
                "request_id": "r1",
                "method": "GET",
                "url": f"{WMS}/api/suppliers",
                "resource_type": "xhr",
                "started_at": "2026-03-01T09:00:01",
                "status": 200,
            },
        },
    ]

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert found == ()


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
    """A grid that pages twice is the same step done twice.

    On a task that only reads, because that is the one whose signature is made
    of reads. A task that changes something is known by the change, and the
    grid refreshing behind it is not part of what it is.
    """
    events = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "GET", "/api/suppliers"),
        _call(START + timedelta(seconds=2), "GET", "/api/suppliers"),
        _call(START + timedelta(seconds=3), "GET", "/api/suppliers"),
    ]

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert found[0].signature == "GET api/suppliers"


def test_how_somebody_got_there_is_not_what_the_task_is() -> None:
    """The rule passive observation lives or dies by.

    The same creation reached two different ways is one task done twice. Before
    this it was two tasks done once each -- and once each is a number that
    never earns anything, so a system nobody demonstrates to could never learn
    a thing.
    """
    from_the_menu = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "GET", "/api/menu"),
        _call(START + timedelta(seconds=2), "GET", "/api/suppliers"),
        _call(START + timedelta(seconds=3), "POST", "/api/suppliers"),
        _call(START + timedelta(seconds=4), "GET", "/api/suppliers"),
    ]
    from_a_search = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "GET", "/api/search"),
        _call(START + timedelta(seconds=2), "GET", "/api/search/results"),
        _call(START + timedelta(seconds=3), "POST", "/api/suppliers"),
        _call(START + timedelta(seconds=4), "GET", "/api/suppliers"),
    ]

    menu = segment(read(_payload(from_the_menu), BatchId("bat-1")))
    search = segment(read(_payload(from_a_search), BatchId("bat-2")))

    assert menu[0].signature == search[0].signature == "POST api/suppliers"
    # The route is still evidence of the same piece of work; it is just not
    # what the piece of work *is*.
    assert menu[0].episode.calls == 4


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
        secret="what-this-browser-proves-itself-with",  # noqa: S106 -- not a credential
    )
    await uow.devices.add(device)

    ingest = IngestObservation(uow, blobs, FakeClock())
    for index, at in enumerate(doings):
        await ingest.execute(
            CTX,
            device_id=device.id,
            secret=device.secret,
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


def test_a_beacon_landing_mid_form_does_not_cut_the_task_in_half() -> None:
    """A keep-alive is a POST on a timer, not a thing somebody did.

    The first real pair this produced was one whole creation and a second
    "doing" that began at the third field of the same form -- because a
    performance beacon landed while the operator was still typing, and the
    piece of work was cut there. Two doings that do not start in the same place
    are not two doings of one task, and induction says so and refuses.
    """
    events = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "GET", "/api/suppliers"),
        _gesture(START + timedelta(seconds=2)),
        _call(START + timedelta(seconds=3), "POST", "/api/webPerformanceEntries/batch"),
        _gesture(START + timedelta(seconds=4)),
        _call(START + timedelta(seconds=5), "POST", "/api/suppliers"),
    ]

    found = segment(read(_payload(events), BatchId("bat-1")))

    assert len(found) == 1, "a beacon on a timer ended the task the operator was in"
    assert found[0].signature == "POST api/suppliers"


def test_how_fast_somebody_clicked_next_is_not_what_the_task_is() -> None:
    """Two doings of one task, one paused after saving and one carried straight
    on. Before this they were two tasks done once each.

    The signature used to run from the change to the end of the piece, so it
    swept up whatever the application did after the save. But the piece is cut
    at the first thing the operator touches after something changed -- so an
    operator who sat still kept the grid refresh and the re-reads inside their
    piece, and one who clicked the next row did not. The identical task in the
    identical screen produced `POST workOperations → GET workOperations → GET
    deviceClassFunctions` one time and `POST workOperations` the next, and the
    two never met.

    Found on a real WMS, twice, by an operator doing the same job twice and
    getting two candidates at one occurrence each -- which is the number that
    never earns anything, and exactly what `_signature` was written to prevent.

    The reads after a change are what the reads before it always were: evidence
    of the same piece of work, and not what the piece of work is.
    """
    unhurried = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "POST", "/api/workOperations"),
        _call(START + timedelta(seconds=2), "GET", "/api/workOperations"),
        _call(START + timedelta(seconds=3), "GET", "/api/deviceClassFunctions"),
    ]
    straight_on = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "POST", "/api/workOperations"),
    ]

    paused = segment(read(_payload(unhurried), BatchId("bat-1")))
    carried_on = segment(read(_payload(straight_on), BatchId("bat-2")))

    assert paused[0].signature == carried_on[0].signature == "POST api/workOperations"
    # The reads are still in the episode. They are the evidence teaching reads;
    # they are just not what makes two doings the same task.
    assert paused[0].episode.calls == 3


def test_a_task_that_only_reads_is_still_known_by_what_it_read() -> None:
    """It has nothing else to be known by, and reading a screen is a task.

    The rule above removes the reads from a signature that has a change in it.
    A run with no change at all is the one place they are still the whole of it,
    and losing that would make every read-only task the same task.
    """
    looking = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "GET", "/api/suppliers"),
        _call(START + timedelta(seconds=2), "GET", "/api/suppliers/S1"),
    ]
    looking_elsewhere = [
        _gesture(START),
        _call(START + timedelta(seconds=1), "GET", "/api/labels"),
    ]

    one = segment(read(_payload(looking), BatchId("bat-1")))
    other = segment(read(_payload(looking_elsewhere), BatchId("bat-2")))

    assert one[0].signature == "GET api/suppliers → GET api/suppliers/*"
    assert one[0].signature != other[0].signature
