"""A12 -- the carryover pool: what a pass could not place, kept for the next one.

Load-bearing rather than decorative. Model abstraction over raw event streams was
measured at roughly 74% recall -- against 17,165 ground-truth events a
model-generated log held 15,420, of which 12,741 were correct. A quarter of every
window is dropped or mislabelled on any given reading. Without a pool those
gestures are gone; with one they are read again next to different neighbours.

Keyed by tenant, not by stream. That is the whole mechanism by which one
operator's Blue Yonder half meets another operator's SAP half.

The ageing rule itself is not here: it is SQL, and it lives with the repository.
"""

from __future__ import annotations

from dataclasses import dataclass

K_POOL_AGE = 6
"""Readings of patience. After six, an entry stops being PRIVILEGED.

Retirement is not removal from the window, and that is a decision rather than
an accident. mine() draws `fresh` from every gesture in the tenant, so a
retired gesture is packed again on the next pass at its own strength: what it
loses is K_POOL_BONUS, not its place. The alternative -- retirement takes it
out of the window, as this module's docstring used to imply -- is permanent
blindness, because nothing ever un-retires: a gesture the budget dropped six
times could then never be read again, not even on the day a second capture
finally brings in the other half of its job. Keyed by tenant, that late-arriving
cross-system join is the one thing this pool exists for.

So the pool is a decaying priority, not a queue with an exit. Six readings of a
boost, then compete on merit -- and the cost of the boost is bounded, which is
what the cap is for.
"""

K_POOL_DAYS = 7

RETIRED_PASSES = "passes"
RETIRED_STALE = "stale"


@dataclass(frozen=True, slots=True)
class PoolEntry:
    """One gesture waiting for a better reading, and how long it has waited.

    Two clocks, because they measure opposite things and one counter cannot be
    both. `age` counts readings this entry was SHOWN and not cited, and runs
    out at K_POOL_AGE. `waited` counts passes it was PASSED OVER, and drives
    priority so the day rotates. Using age for both made an entry that had been
    read six times outrank one never seen at all.

    `reason` is why it retired, empty while it is still live. Evidence that
    leaves the prompt without a record is the failure this architecture exists
    to avoid.
    """

    gesture_id: str
    tenant: str
    age: int
    entered_at: str
    reason: str = ""
    waited: int = 0
