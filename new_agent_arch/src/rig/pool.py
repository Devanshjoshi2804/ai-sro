"""A12 — the carryover pool: what a pass could not place, kept for the next one.

Load-bearing rather than decorative. Model abstraction over raw event streams was
measured at roughly 74% recall -- against 17,165 ground-truth events a
model-generated log held 15,420, of which 12,741 were correct. A quarter of every
window is dropped or mislabelled on any given reading. Without a pool those
gestures are gone; with one they are read again next to different neighbours.

Keyed by tenant, not by stream. That is the whole mechanism by which one
operator's Blue Yonder half meets another operator's SAP half.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from rig.store import Store

K_POOL_AGE = 6
K_POOL_DAYS = 7

RETIRED_PASSES = "passes"
RETIRED_STALE = "stale"


@dataclass(frozen=True, slots=True)
class PoolEntry:
    gesture_id: str
    tenant: str
    age: int
    entered_at: str
    reason: str = ""


def add_unclaimed(store: Store, tenant: str, window_ids: list[str], claimed: set[str]) -> int:
    """Anything the pass did not cite enters at age 0; anything it did leaves.

    `claimed` is cleared in full rather than only where it intersects the
    window. A pooled gesture is packed into the window alongside the fresh ones
    (window.pack), so the pass can cite evidence that is already in the pool --
    and a caller that passes only this pass's own gesture ids as `window_ids`
    would then leave that citation in the pool to age out and retire despite
    having been placed. The two arguments are siblings and only one of them is
    about the window.
    """
    added = 0
    now = datetime.now(tz=UTC).isoformat()
    with store.connect() as connection:
        for gesture_id in claimed:
            connection.execute(
                "DELETE FROM pool WHERE tenant = ? AND gesture_id = ?",
                (tenant, gesture_id),
            )
        for gesture_id in window_ids:
            if gesture_id in claimed:
                continue
            # OR IGNORE: a gesture that has sat unplaced through three passes
            # keeps the age those passes gave it. Re-entering must not reset the
            # clock, or nothing in a recurring window ever retires. It also
            # leaves a retired row retired -- retirement is a decision, and a
            # later pass reaching that gesture another way still cites it.
            cursor = connection.execute(
                "INSERT OR IGNORE INTO pool"
                " (gesture_id, tenant, age, retired, reason, entered_at)"
                " VALUES (?, ?, 0, 0, '', ?)",
                (gesture_id, tenant, now),
            )
            added += cursor.rowcount
    return added


def age_pool(store: Store, tenant: str) -> int:
    """One pass older. Past either cap it retires: out of the prompt, still in
    the store, and citable if a later pass reaches it another way.

    Two caps, because a pool that only counts passes keeps an entry forever in a
    tenant nobody is mining, and one that only counts days retires an entry a
    busy tenant has already reconsidered fifty times. Whichever comes first, and
    the row says which.
    """
    stale_before = (datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS)).isoformat()
    with store.connect() as connection:
        connection.execute(
            "UPDATE pool SET age = age + 1 WHERE tenant = ? AND retired = 0", (tenant,)
        )
        passes = connection.execute(
            "UPDATE pool SET retired = 1, reason = ? WHERE tenant = ? AND retired = 0 AND age > ?",
            (RETIRED_PASSES, tenant, K_POOL_AGE),
        ).rowcount
        stale = connection.execute(
            "UPDATE pool SET retired = 1, reason = ?"
            " WHERE tenant = ? AND retired = 0 AND entered_at < ?",
            (RETIRED_STALE, tenant, stale_before),
        ).rowcount
    return passes + stale


def pool_ids(store: Store, tenant: str) -> list[str]:
    return [
        row["gesture_id"]
        for row in store.query(
            "SELECT gesture_id FROM pool WHERE tenant = ? AND retired = 0"
            " ORDER BY entered_at, gesture_id",
            (tenant,),
        )
    ]


def retired_entries(store: Store, tenant: str) -> list[PoolEntry]:
    """What the pool stopped offering, and why. The only silent loss left is a
    claimed gesture's row, and that one left because it was placed."""
    return [
        PoolEntry(
            gesture_id=row["gesture_id"],
            tenant=row["tenant"],
            age=row["age"],
            entered_at=row["entered_at"],
            reason=row["reason"],
        )
        for row in store.query(
            "SELECT * FROM pool WHERE tenant = ? AND retired = 1 ORDER BY entered_at, gesture_id",
            (tenant,),
        )
    ]
