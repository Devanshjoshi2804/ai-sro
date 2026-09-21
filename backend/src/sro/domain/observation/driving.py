"""Which evidence is this system's own driving rather than somebody working.

A replay presses the same buttons an operator presses, in the same browser, on
the same pages. The extension knows which tab it is driving and drops those
gestures before they are ever uploaded -- and that is the only thing standing
between a run and the evidence plane, which is one check too few. Every other
rule this system has about capture is enforced twice: the content script is not
registered on an excluded host, AND `ObservationPolicy.allows` refuses one that
arrives anyway, because "an extension that is wrong, old or lying does not get
to write into the evidence plane". An extension can be wrong about this too --
an old version, a worker evicted mid-run, a bug of exactly the kind this file
was written after -- and the cost is not a stray row. It is the system mining a
task from a robot imitating a person, and then offering that task back as
something worth automating.

So: a gesture made by a browser that was driving a run at that moment is not
evidence of anybody working.

**The two clocks.** A gesture's `at` is the browser's own clock, in unix
seconds, exactly as `recorder.js` stamped it. A run's `started_at` is this
server's. They are not comparable, and a warehouse laptop's clock is routinely
minutes out -- so the batch is what makes this answerable at all: it carries
the window on the DEVICE's clock and the moment it arrived on OURS, and the
difference between them is that browser's offset at that upload. Each batch
carries its own, so a clock corrected between two uploads costs nothing.

**A run with no end.** `finished_at` is null on runs that ended without
writing one -- 4 of 121 on this deployment, none of them still running -- so
"has not finished" cannot mean "is still driving". A window that stayed open
would silently stop every later gesture from that browser being mined, which
is a system that goes quiet rather than one that says no. So an unfinished run
drives for `LONGEST` and no more. The longest run this deployment has recorded
is 12 minutes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

WAS_OUR_OWN_DRIVING = "this browser was performing a run"
"""What an intent says about a gesture that was our own replay.

Written instead of a reading, so the gesture is marked rather than hidden:
`unread` is "has no intent row", and one merely skipped would come back on
every pass forever. An intent with no `act` is already what every later reader
treats as nothing to learn from, and this says which kind of nothing it is.
"""


def was_our_own_driving(intent: object) -> bool:
    """Whether this intent is the mark above rather than a reading."""
    return getattr(intent, "why", None) == WAS_OUR_OWN_DRIVING


LONGEST = timedelta(minutes=30)
"""How long a run with no recorded end is treated as still driving.

Comfortably past the longest run this deployment has recorded (742 seconds)
and short enough that a run which never wrote its end costs half an hour of
that browser's evidence rather than all of it, forever.
"""


@dataclass(frozen=True, slots=True)
class Driving:
    """One run's hold on one browser, in server time."""

    device_id: str
    started_at: datetime
    finished_at: datetime | None

    def held(self, at: datetime) -> bool:
        if at < self.started_at:
            return False
        end = self.finished_at or (self.started_at + LONGEST)
        return at <= end


@dataclass(frozen=True, slots=True)
class Uploaded:
    """What one batch says about the clock it was recorded on.

    `ended_at` is the device's, `received_at` is ours, and both are required of
    every upload. A batch that carries neither says nothing about its own clock
    and nothing here will guess: its gestures are left alone.
    """

    device_id: str
    ended_at: datetime | None
    received_at: datetime | None

    @property
    def skew(self) -> timedelta | None:
        """What to add to this browser's clock to read it as ours."""
        if self.ended_at is None or self.received_at is None:
            return None
        return self.received_at - self.ended_at


def our_own_driving(
    gestures: Sequence[tuple[str, str, float]],
    batches: Mapping[str, Uploaded],
    runs: Iterable[Driving],
) -> frozenset[str]:
    """The ids of gestures a run of ours was driving when they happened.

    `gestures` are `(id, batch_id, at)` -- the browser's clock, in seconds.

    Left alone rather than guessed at, in three cases, all of them the same
    rule: this refuses evidence, and refusing what it cannot place would lose
    an operator's work.

      - a gesture whose batch is not among those given
      - a batch that cannot say what its clock was doing
      - a browser that was driving nothing
    """
    by_device: dict[str, list[Driving]] = {}
    for run in runs:
        by_device.setdefault(run.device_id, []).append(run)
    if not by_device:
        return frozenset()

    ours: set[str] = set()
    for gesture_id, batch_id, at in gestures:
        batch = batches.get(batch_id)
        if batch is None:
            continue
        skew = batch.skew
        if skew is None:
            continue
        held = by_device.get(batch.device_id)
        if not held:
            continue
        # Unix seconds are absolute, so this is the browser's instant read as
        # UTC; the skew then says what that instant was on our clock.
        when = datetime.fromtimestamp(at, tz=UTC) + skew
        if any(run.held(when) for run in held):
            ours.add(gesture_id)
    return frozenset(ours)


__all__ = [
    "LONGEST",
    "WAS_OUR_OWN_DRIVING",
    "Driving",
    "Uploaded",
    "our_own_driving",
    "was_our_own_driving",
]
