"""A12 — the carryover pool: what a pass could not place, kept for the next one.

Load-bearing rather than decorative. Model abstraction over raw event streams was
measured at roughly 74% recall -- against 17,165 ground-truth events a
model-generated log held 15,420, of which 12,741 were correct. A quarter of every
window is dropped or mislabelled on any given reading. Without a pool those
gestures are gone; with one they are read again next to different neighbours.

Keyed by tenant, not by stream. That is the whole mechanism by which one
operator's Blue Yonder half meets another operator's SAP half.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from rig.store import Store

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
            # leaves a retired row retired -- retirement is a decision, and
            # the gesture goes on being packed as ordinary evidence either way.
            cursor = connection.execute(
                "INSERT OR IGNORE INTO pool"
                " (gesture_id, tenant, age, retired, reason, entered_at)"
                " VALUES (?, ?, 0, 0, '', ?)",
                (gesture_id, tenant, now),
            )
            added += cursor.rowcount
    return added


def age_pool(store: Store, tenant: str, shown: Iterable[str] | None = None) -> int:
    """One READING older, and only for evidence a reading actually saw.

    `shown` is the gesture ids that were in the window. An entry the budget
    left out was not read, was not passed over, and has not used up any
    patience -- so it does not age. Measured on a synthetic all-tabs day of
    3,240 gestures, which is the scale broad capture produces: the window
    holds ~200, a day needs 17 passes to be seen once, K_POOL_AGE is 6, and
    ageing every entry every pass retired 2,630 of 3,240 having never once put
    them in front of the model. The mechanism built to stop the same tail
    losing forever guaranteed it instead.

    Same shape as the refused-pass rule below, one level down: that one counts
    calls the model answered, this one counts entries the model was shown.
    None means every entry ages, which is what a caller with no window wants.

    A reading, not a call, either: mine() ages the pool only on a pass the
    model actually answered. Six refused calls -- an expired key, a model name
    the API 404s, a day of 503s -- retired the whole pool having read nothing.

    Past either cap an entry retires: no longer offered ahead of fresh evidence
    (see K_POOL_AGE for what that does and does not mean), still in the store,
    and still packed into every later window on its own merits.

    Two caps, because a pool that only counts passes keeps an entry forever in a
    tenant nobody is mining, and one that only counts days retires an entry a
    busy tenant has already reconsidered fifty times. Whichever comes first, and
    the row says which.
    """
    stale_before = (datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS)).isoformat()
    with store.connect() as connection:
        if shown is None:
            connection.execute(
                "UPDATE pool SET age = age + 1 WHERE tenant = ? AND retired = 0", (tenant,)
            )
        else:
            ids = tuple(dict.fromkeys(shown))
            if ids:
                marks = ",".join("?" * len(ids))
                connection.execute(
                    f"UPDATE pool SET age = age + 1 WHERE tenant = ? AND retired = 0"
                    f" AND gesture_id IN ({marks})",
                    (tenant, *ids),
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


def waiting(store: Store, tenant: str) -> list[PoolEntry]:
    """Live entries with the age each has waited.

    `pool_ids` answers "what is carried"; this answers "and how long has it
    been waiting", which is what stops a window repeating itself. See
    window.K_POOL_WAIT.
    """
    return [
        PoolEntry(
            gesture_id=row["gesture_id"],
            tenant=row["tenant"],
            age=row["age"],
            entered_at=row["entered_at"],
            reason=row["reason"],
        )
        for row in store.query(
            "SELECT * FROM pool WHERE tenant = ? AND retired = 0 ORDER BY entered_at, gesture_id",
            (tenant,),
        )
    ]


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
