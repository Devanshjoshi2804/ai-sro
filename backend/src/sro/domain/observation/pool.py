from __future__ import annotations

from dataclasses import dataclass

K_POOL_AGE = 6

K_POOL_DAYS = 7

RETIRED_PASSES = "passes"
RETIRED_STALE = "stale"
RETIRED_DRIVING = "own driving"


@dataclass(frozen=True, slots=True)
class PoolEntry:
    gesture_id: str
    tenant: str
    age: int
    entered_at: str
    reason: str = ""
    waited: int = 0
