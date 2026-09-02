from datetime import UTC, datetime, timedelta

from sro.application.observation.segment import Observed, segment
from sro.domain.shared.identifiers import BatchId

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
