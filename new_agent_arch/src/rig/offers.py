"""What was offered, and what became of it.

Written by the extension, which made the offer, over `POST /v1/offers`. Read
by `counsel` below, per job, when its shape is served: the labelled record of
whether recognition was right. Offers that kept diverging move the job's
threshold past the gesture they diverged at; offers refused three times
running rest the job for a day.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from rig.store import Store

K_OFFER_AFTER = 2
"""How many gestures a tail must match before a job is offered, unless its
offers have said otherwise. The extension holds the same value under the same
name in `recognise.js`; a served shape's `offer_after` is what overrides it."""

K_WINDOW = 10
"""How many of a job's newest offers are read. Older ones were made against a
threshold that has since moved, or against a page that has."""

K_ENOUGH = 3
"""Offers before their fates are read at all: in a row to quiet a job, and in
the window to move its threshold. One operator's one afternoon is not a
verdict on the job."""

K_QUIET_HOURS = 24
"""How long a job refused `K_ENOUGH` times running is left alone. A rest, not a
retirement: the job is still proven, and tomorrow's shift may want it."""

REFUSED = ("dismissed", "did_it")
"""The two fates that mean the offer was understood and not wanted."""

FATES = ("accepted", "dismissed", "did_it", "expired", "diverged")
"""accepted: Yes was pressed and a run started. dismissed: No thanks. did_it:
the operator made the workflow's write themselves while it asked. expired: the
nudge's lifetime passed. diverged: the tail stopped matching the prefix."""


def record_offer(
    store: Store,
    *,
    tenant: str,
    workflow_id: str,
    k: int,
    fate: str,
    run_id: str | None,
    device_id: str,
    at: str,
) -> str:
    if fate not in FATES:
        raise ValueError(f"{fate!r} is not a fate an offer can have")
    # The browser's clock, in whatever form it wrote it (`toISOString` says
    # `Z`); stored the way every server row is, so `since` compares.
    when = datetime.fromisoformat(at)
    at = (when if when.tzinfo else when.replace(tzinfo=UTC)).astimezone(UTC).isoformat()
    offer_id = "off_" + secrets.token_hex(8)
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO offers (id, tenant, workflow_id, device_id, k, fate, run_id, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (offer_id, tenant, workflow_id, device_id, k, fate, run_id, at),
        )
    return offer_id


@dataclass(frozen=True, slots=True)
class Counsel:
    offer_after: int
    """The k the extension should offer this job at."""
    quiet_until: str | None
    """When the job may be offered again, or None when it may be now."""

    def as_json(self) -> dict[str, object]:
        return {"offer_after": self.offer_after, "quiet_until": self.quiet_until}


def counsel(store: Store, *, tenant: str, workflow_id: str, now: datetime | None = None) -> Counsel:
    """What a job's newest offers say about offering it again.

    Quiet: the newest `K_ENOUGH` offers were all refused, and the last of them
    was under `K_QUIET_HOURS` ago. Any other fate in between -- accepted,
    expired, diverged -- breaks the run: an offer the operator did not answer
    is not one they turned down.

    Later: at least `K_ENOUGH` offers in the window and half or more of them
    diverged, so the job is offered one gesture past the deepest k it diverged
    at. The threshold only ever moves up here; it comes back down when the
    diverged offers age out of the window, which they do as later offers land.
    """
    rows = store.query(
        "SELECT k, fate, at FROM offers WHERE tenant = ? AND workflow_id = ?"
        " ORDER BY at DESC LIMIT ?",
        (tenant, workflow_id, K_WINDOW),
    )
    now = now or datetime.now(UTC)
    refused = 0
    for row in rows:
        if row["fate"] not in REFUSED:
            break
        refused += 1
    quiet_until = None
    if refused >= K_ENOUGH:
        until = datetime.fromisoformat(rows[0]["at"]) + timedelta(hours=K_QUIET_HOURS)
        if until > now:
            quiet_until = until.isoformat()
    offer_after = K_OFFER_AFTER
    diverged = [int(row["k"]) for row in rows if row["fate"] == "diverged"]
    if len(rows) >= K_ENOUGH and 2 * len(diverged) >= len(rows):
        offer_after = max(offer_after, max(diverged) + 1)
    return Counsel(offer_after=offer_after, quiet_until=quiet_until)
