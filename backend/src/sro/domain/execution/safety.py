from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

FAILURE_WINDOW = timedelta(minutes=15)

TRIP_AFTER = 3

WRITE_WINDOW = timedelta(hours=1)
MAX_WRITES_PER_WINDOW = 60

MAX_ITEMS_PER_BATCH = 25


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class RunFact:
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
