"""A replay's own clicks are not evidence of anybody working.

The extension drops them before they are uploaded. This is the second check,
for the same reason `ObservationPolicy.allows` is one: an extension that is
wrong, old or lying does not get to write into the evidence plane. What it
costs to be missing is not a stray row -- it is a task mined from a robot
imitating a person, and offered back as worth automating.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.domain.observation.driving import LONGEST, Driving, Uploaded, our_own_driving

NOON = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
# The browser is four minutes fast, which is ordinary for a warehouse laptop
# and is the whole reason a batch carries both clocks.
FAST = timedelta(minutes=4)


def _batch(device: str = "dev-1", *, skewed: timedelta = FAST) -> Uploaded:
    """An upload that ended at noon on OUR clock, from a browser that thinks
    it is `skewed` later than that."""
    return Uploaded(device_id=device, ended_at=NOON + skewed, received_at=NOON)


def _at(server_time: datetime, *, skewed: timedelta = FAST) -> float:
    """What the browser would have stamped a gesture with at that moment."""
    return (server_time + skewed).timestamp()


def test_a_gesture_made_while_a_run_was_driving_that_browser_is_ours() -> None:
    running = Driving("dev-1", NOON - timedelta(minutes=5), NOON - timedelta(minutes=1))

    ours = our_own_driving(
        [("g1", "b1", _at(NOON - timedelta(minutes=3)))], {"b1": _batch()}, [running]
    )

    assert ours == frozenset({"g1"})


def test_the_same_instant_on_a_browser_whose_clock_is_wrong_is_still_inside_it() -> None:
    """The half that cannot be done without the batch. Compared raw, a gesture
    four minutes fast falls outside a four-minute run window and is mined."""
    running = Driving("dev-1", NOON - timedelta(minutes=5), NOON - timedelta(minutes=1))
    inside = _at(NOON - timedelta(minutes=2))

    assert our_own_driving([("g1", "b1", inside)], {"b1": _batch()}, [running]) == frozenset({"g1"})
    # And the proof that the correction is what did it: the same number, read
    # as though the clocks agreed, is after the run ended.
    assert datetime.fromtimestamp(inside, tz=UTC) > running.finished_at


def test_work_either_side_of_a_run_is_the_operator_and_is_kept() -> None:
    running = Driving("dev-1", NOON - timedelta(minutes=5), NOON - timedelta(minutes=1))

    ours = our_own_driving(
        [
            ("before", "b1", _at(NOON - timedelta(minutes=6))),
            ("after", "b1", _at(NOON - timedelta(seconds=30))),
        ],
        {"b1": _batch()},
        [running],
    )

    assert ours == frozenset()


def test_another_browser_s_work_during_this_one_s_run_is_untouched() -> None:
    """A run holds the browser it is driving and nothing else. An operator at
    the next desk is working."""
    running = Driving("dev-1", NOON - timedelta(minutes=5), NOON)

    ours = our_own_driving(
        [("g1", "b2", _at(NOON - timedelta(minutes=2)))],
        {"b2": _batch("dev-2")},
        [running],
    )

    assert ours == frozenset()


def test_a_run_that_never_wrote_an_end_stops_driving_after_a_while() -> None:
    """`finished_at` is null on runs that ended without writing one -- 4 of 121
    on this deployment, none of them still running. A window that stayed open
    would silently stop every later gesture from that browser being mined, and
    a system that goes quiet is worse than one that says no."""
    forgotten = Driving("dev-1", NOON - timedelta(hours=3), None)

    still = our_own_driving(
        [("g1", "b1", _at(NOON - timedelta(hours=3) + timedelta(minutes=5)))],
        {"b1": _batch()},
        [forgotten],
    )
    later = our_own_driving(
        [("g2", "b1", _at(NOON - timedelta(hours=3) + LONGEST + timedelta(minutes=1)))],
        {"b1": _batch()},
        [forgotten],
    )

    assert still == frozenset({"g1"}), "a run with no end drove nothing at all"
    assert later == frozenset(), "a run with no end drove that browser forever"


def test_what_cannot_be_placed_is_left_alone() -> None:
    """Three ways, one rule: this refuses evidence, and refusing what it cannot
    place would lose an operator's work."""
    running = Driving("dev-1", NOON - timedelta(minutes=5), NOON)
    inside = _at(NOON - timedelta(minutes=2))

    no_batch = our_own_driving([("g1", "missing", inside)], {"b1": _batch()}, [running])
    no_clock = our_own_driving(
        [("g1", "b1", inside)],
        {"b1": Uploaded(device_id="dev-1", ended_at=None, received_at=NOON)},
        [running],
    )
    no_runs = our_own_driving([("g1", "b1", inside)], {"b1": _batch()}, [])

    assert no_batch == frozenset()
    assert no_clock == frozenset()
    assert no_runs == frozenset()
