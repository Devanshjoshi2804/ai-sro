"""What stops a run before it starts.

Two limits, both computed from what recent runs actually did rather than from a
counter somebody has to remember to increment. Derived state cannot drift from
the thing it describes, and a restart cannot lose it.

Both fail *closed to a human*: the answer is never "retry harder", it is "a
person decides now". Retrying into a system that is already failing is how a
degraded WMS becomes an unavailable one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

FAILURE_WINDOW = timedelta(minutes=15)
"""How far back the breaker looks. Long enough to see a pattern, short enough
that a system which has recovered is usable again without an intervention."""

TRIP_AFTER = 3
"""Failed runs against one system inside the window. Deliberately small: the
third consecutive failure is not bad luck, and the fourth attempt is the one
that turns an outage into an incident."""

WRITE_WINDOW = timedelta(hours=1)
MAX_WRITES_PER_WINDOW = 60
"""Blast radius. A skill looping on a scheduler can do more damage in an hour
than any single wrong write, and no legitimate operator-driven workload here
needs more than one write a minute sustained."""

MAX_ITEMS_PER_BATCH = 25
"""A batch bigger than this is a migration, and a migration is somebody's
decision rather than a chat message."""


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class RunFact:
    """The little a safety decision needs to know about a past run."""

    finished_at: datetime
    failed: bool
    writes: int


@dataclass(frozen=True, slots=True)
class Assessment:
    state: BreakerState
    reason: str | None = None

    @property
    def permitted(self) -> bool:
        return self.state is BreakerState.CLOSED


def assess(facts: tuple[RunFact, ...], now: datetime, *, requested_writes: int = 1) -> Assessment:
    """Whether another run against this system may start."""
    if requested_writes > MAX_ITEMS_PER_BATCH:
        return Assessment(
            BreakerState.OPEN,
            f"{requested_writes} items in one request is beyond the {MAX_ITEMS_PER_BATCH} "
            "this system will do without a person deciding",
        )

    recent_failures = [
        fact for fact in facts if fact.failed and now - fact.finished_at <= FAILURE_WINDOW
    ]
    if len(recent_failures) >= TRIP_AFTER:
        return Assessment(
            BreakerState.OPEN,
            f"{len(recent_failures)} runs against this system have failed in the last "
            f"{int(FAILURE_WINDOW.total_seconds() // 60)} minutes; a person should look "
            "before anything else is sent",
        )

    written = sum(fact.writes for fact in facts if now - fact.finished_at <= WRITE_WINDOW)
    if written + requested_writes > MAX_WRITES_PER_WINDOW:
        return Assessment(
            BreakerState.OPEN,
            f"{written} writes already went to this system in the last hour, and the "
            f"limit is {MAX_WRITES_PER_WINDOW}",
        )

    return Assessment(BreakerState.CLOSED)
