import json
from datetime import UTC, datetime, timedelta

from sro.application.capture.events import RequestEvent, SnapshotEvent
from sro.application.observation.propose import _plainly, _workflows, occurrences
from sro.application.observation.segment import Observed, segment
from sro.application.observation.teach import _within
from sro.domain.observation.candidate import Episode, JoinKind, TaskCandidate
from sro.domain.shared.identifiers import BatchId, CandidateId
from tests import factories as f

AT = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
BATCH = BatchId("bat_one")


def _gesture(seconds: int, host: str) -> Observed:
    return Observed(
        at=AT + timedelta(seconds=seconds),
        kind="gesture",
        host=host,
        batch_id=BATCH,
        url=f"https://{host}/screen",
    )


def _call(seconds: int, host: str, method: str = "POST") -> Observed:
    return Observed(
        at=AT + timedelta(seconds=seconds),
        kind="request",
        host=host,
        batch_id=BATCH,
        method=method,
        url=f"https://{host}/api/suppliers",
        mutating=method != "GET",
    )


def test_another_tab_talking_does_not_cut_the_work_in_half() -> None:
    """A mail client polls while somebody works in the warehouse system. The
    poll is not a boundary in their work -- it is not even their work."""
    work = [
        _gesture(0, "wms.example"),
        _call(1, "wms.example", "GET"),  # looking the supplier up, not yet a change
        _call(2, "mail.example", "GET"),  # another tab, mid-task
        _gesture(3, "wms.example"),
        _call(4, "wms.example"),
    ]

    pieces = segment(work)

    wms = [piece for piece in pieces if piece.episode.host == "wms.example"]
    assert len(wms) == 1, f"the warehouse work was cut into {len(wms)} pieces"
    assert wms[0].episode.gestures == 2


def test_a_real_pause_still_ends_the_work() -> None:
    """Partitioning by host must not swallow the bound that says a person went
    away and came back to do it again."""
    work = [
        _gesture(0, "wms.example"),
        _call(1, "wms.example"),
        _gesture(60 * 20, "wms.example"),  # twenty minutes later, past IDLE
        _call(60 * 20 + 1, "wms.example"),
    ]

    assert len(segment(work)) == 2


def test_an_episode_says_when_somebody_had_their_hands_on_it() -> None:
    """When the page was still talking is not when a person was working. Only
    the second can say two tabs were one job."""
    work = [
        _call(0, "wms.example", "GET"),  # the screen loading
        _gesture(5, "wms.example"),
        _gesture(9, "wms.example"),
        _call(10, "wms.example"),
        _call(30, "wms.example", "GET"),  # the grid refreshing afterwards
    ]

    (piece,) = segment(work)

    assert piece.episode.touched_from == AT + timedelta(seconds=5)
    assert piece.episode.touched_until == AT + timedelta(seconds=9)
    assert piece.episode.started_at == AT, "the episode still covers the whole piece"


def _request_line(host: str, request_id: str) -> bytes:
    return json.dumps(
        {
            "kind": "request",
            "request": {
                "request_id": request_id,
                "method": "POST",
                "resource_type": "xhr",
                "started_at": AT.isoformat(),
                "url": f"https://{host}/api/suppliers",
            },
        }
    ).encode()


def _gesture_line(url: str | None = None) -> bytes:
    gesture: dict[str, object] = {
        "kind": "click",
        "at": AT.isoformat(),
        "target": {"cssPath": "button"},
    }
    if url is not None:
        gesture["url"] = url
    return json.dumps({"kind": "gesture", "gesture": gesture}).encode()


_TREE = {
    "nodes": [
        {
            "nodeId": "1",
            "role": {"value": "button"},
            "name": {"value": "Add"},
            "ignored": False,
            "childIds": [],
        }
    ]
}


def _snapshot_line(url: str) -> bytes:
    return json.dumps(
        {"kind": "snapshot", "snapshot": _TREE, "taken_at": AT.isoformat(), "url": url}
    ).encode()


def test_a_recording_holds_only_its_own_host_s_calls() -> None:
    """Once two episodes can overlap in time, slicing a batch by time alone
    puts the warehouse's calls in the mail half and the mail's in the
    warehouse's -- and the induced skill does everything twice."""
    episode = Episode(
        started_at=AT,
        ended_at=AT + timedelta(seconds=10),
        host="wms.example",
        batch_ids=(BATCH,),
        gestures=1,
        calls=1,
    )
    payload = b"\n".join((_request_line("wms.example", "a"), _request_line("mail.example", "b")))

    kept = _within(payload, episode, BATCH)

    urls = [event.request.url for event, _ in kept if isinstance(event, RequestEvent)]
    assert urls == ["https://wms.example/api/suppliers"], (
        "another host's call landed in this episode's recording"
    )


def test_a_single_host_episode_s_full_shape_is_admitted_unchanged() -> None:
    """`_runs` ends a run on a host change, so a mined episode's evidence is
    already all one host -- a gesture, a call, and a tree, none of them ever
    disagreeing with the episode's own. That is the only shape this guard can
    receive from today's segmentation, and admitting one call from it (the
    original version of this test) is not the same claim as admitting the
    whole episode: this guard is invisible only if nothing in that shape is
    ever dropped."""
    episode = Episode(
        started_at=AT,
        ended_at=AT + timedelta(seconds=10),
        host="wms.example",
        batch_ids=(BATCH,),
        gestures=1,
        calls=1,
    )
    payload = b"\n".join(
        (
            _gesture_line("https://wms.example/screen"),
            _request_line("wms.example", "a"),
            _snapshot_line("https://wms.example/screen"),
        )
    )

    kept = _within(payload, episode, BATCH)

    assert len(kept) == 3, "a same-host event was dropped by a guard meant to be invisible today"


def test_a_url_less_event_does_not_land_in_either_of_two_overlapping_episodes() -> None:
    """Two tabs' episodes can overlap once `_runs` stops ending a run on every
    host change (Task 4). A gesture with no url at all -- the same shape as a
    relative-URL request, a `file://` tab, or a snapshot whose tab url the
    extension could not read -- names no host to agree with either episode's.
    Segmentation itself never mines a `host=""` episode for it either:
    `_segment` drops any run with no calls, and a stream of url-less gestures
    has none. Letting an absent host stand in for a match would put this one
    event in both recordings; it belongs in neither."""
    wms = Episode(
        started_at=AT,
        ended_at=AT + timedelta(seconds=10),
        host="wms.example",
        batch_ids=(BATCH,),
        gestures=1,
        calls=1,
    )
    mail = Episode(
        started_at=AT,
        ended_at=AT + timedelta(seconds=10),
        host="mail.example",
        batch_ids=(BATCH,),
        gestures=1,
        calls=1,
    )
    payload = _gesture_line()  # no "url" on the gesture at all

    assert _within(payload, wms, BATCH) == []
    assert _within(payload, mail, BATCH) == []


def test_a_snapshot_is_judged_by_time_not_host() -> None:
    """A snapshot's own `url` is the tab's, read by `service-worker.js`'s
    `takeTreeSoon`, while an episode's host comes from a gesture's frame url
    -- and for a portal that hosts its screens in an iframe the two can
    disagree. Segmentation never had a snapshot branch, so a snapshot's host
    was never part of what defined an episode; host-checking it here would
    silently drop it for exactly the cross-host portal `_capture`'s gesture
    branch already documents."""
    episode = Episode(
        started_at=AT,
        ended_at=AT + timedelta(seconds=10),
        host="wms.example",
        batch_ids=(BATCH,),
        gestures=1,
        calls=1,
    )
    payload = _snapshot_line("https://mail.example/tab")  # a different host than the episode's

    (kept,) = _within(payload, episode, BATCH)

    assert isinstance(kept[0], SnapshotEvent)


def _episode(start: int, end: int, host: str, touched: tuple[int, int] | None) -> Episode:
    return Episode(
        started_at=AT + timedelta(seconds=start),
        ended_at=AT + timedelta(seconds=end),
        host=host,
        batch_ids=(BATCH,),
        gestures=1,
        calls=1,
        touched_from=AT + timedelta(seconds=touched[0]) if touched else None,
        touched_until=AT + timedelta(seconds=touched[1]) if touched else None,
    )


def _candidate(*episodes: Episode) -> TaskCandidate:
    """A candidate holding those episodes, in that order. Only the episodes
    matter here -- `occurrences` reads nothing else."""
    host = episodes[0].host
    return TaskCandidate(
        id=CandidateId(f"cnd-{host}"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        signature="POST api/suppliers",
        host=host,
        title=f"Create a supplier on {host}",
        episodes=episodes,
    )


def test_flipping_between_two_tabs_is_one_job() -> None:
    """The halves overlap because the operator went back to the mail while the
    warehouse screen was still open. That is one job, not two."""
    mail = _episode(0, 120, "mail.example", touched=(0, 100))
    wms = _episode(60, 200, "wms.example", touched=(70, 190))

    assert occurrences(_candidate(mail), _candidate(wms))


def test_a_mailbox_left_open_is_not_part_of_the_work() -> None:
    """Overlapping in time proves nothing on its own: the tab was open, the
    client polled, and nobody touched it."""
    mail = _episode(0, 3600, "mail.example", touched=(0, 30))
    wms = _episode(1800, 2000, "wms.example", touched=(1810, 1990))

    assert not occurrences(_candidate(mail), _candidate(wms))


def test_an_episode_with_no_touched_window_keeps_the_rule_that_mined_it() -> None:
    mail = _episode(0, 100, "mail.example", touched=None)
    wms = _episode(60, 200, "wms.example", touched=None)

    assert not occurrences(_candidate(mail), _candidate(wms)), (
        "an old overlapping pair must not start pairing retroactively"
    )


def test_one_interleaved_pair_counts_once_not_twice() -> None:
    """`_workflows` sums both directions against TOGETHER_TIMES, so a symmetric
    rule would let a single pair clear the bar on its own."""
    mail, wms = (
        _candidate(_episode(0, 120, "mail.example", (0, 100))),
        _candidate(_episode(60, 200, "wms.example", (70, 190))),
    )

    assert len(occurrences(mail, wms)) + len(occurrences(wms, mail)) == 1


def test_two_episodes_that_start_in_the_same_second_still_count_once() -> None:
    """Both timestamps come from event data, so a tie is not exotic. A `>` guard
    lets a tied pair qualify in BOTH directions, and `_workflows` sums the two
    -- offering one coincidence as a job, which is what the guard exists to
    prevent."""
    mail = _candidate(_episode(0, 120, "mail.example", (0, 100)))
    wms = _candidate(_episode(0, 200, "wms.example", (10, 190)))

    assert len(occurrences(mail, wms)) + len(occurrences(wms, mail)) == 1
    assert _workflows([mail, wms]) == [], "one pair reached the threshold on its own"


def test_the_reason_says_what_actually_happened() -> None:
    """The reason is what a person reads when deciding whether two things are
    one job. "One after the other" is simply false about somebody who kept both
    tabs open."""
    mail = _candidate(
        _episode(0, 120, "mail.example", (0, 100)),
        _episode(3600, 3720, "mail.example", (3600, 3700)),
    )
    wms = _candidate(
        _episode(60, 200, "wms.example", (70, 190)),
        _episode(3660, 3800, "wms.example", (3670, 3790)),
    )

    assert _plainly(JoinKind.WORKFLOW, mail, wms) == (
        "worked in both at once 2 times -- mail.example and wms.example"
    )
