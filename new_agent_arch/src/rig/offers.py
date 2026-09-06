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
"""Offers before their fates are read at all: in a row, from one browser, to
rest a job for that browser; in the window, from every browser, to move its
threshold. A single dismissal is a mood; three running is an answer."""

K_QUIET_HOURS = 24
"""How long a job refused `K_ENOUGH` times running is left alone on the browser
that refused it. A rest, not a retirement: the job is still proven, the next
browser is still offered it, and tomorrow's shift on this one may want it."""

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
    now: datetime | None = None,
) -> str:
    if fate not in FATES:
        raise ValueError(f"{fate!r} is not a fate an offer can have")
    # The browser's clock, in whatever form it wrote it (`toISOString` says
    # `Z`); stored the way every server row is, so `since` compares. Never
    # ahead of the rig's own clock: `counsel` reads the newest offers and
    # rests a job for a day after the last refusal, and a browser a year
    # fast would otherwise own the window, and the rest, for a year.
    when = datetime.fromisoformat(at)
    when = (when if when.tzinfo else when.replace(tzinfo=UTC)).astimezone(UTC)
    at = min(when, now or datetime.now(UTC)).isoformat()
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
    """When the asking browser may be offered the job again; None when now."""

    def as_json(self) -> dict[str, object]:
        return {
            "offer_after": self.offer_after,
            "later": self.offer_after > K_OFFER_AFTER,
            "quiet_until": self.quiet_until,
        }


def counsel(
    store: Store,
    *,
    tenant: str,
    workflow_id: str,
    device_id: str | None = None,
    now: datetime | None = None,
) -> Counsel:
    """What a job's newest offers say about offering it again.

    Later: at least `K_ENOUGH` offers in the tenant-wide window and half or
    more of them diverged, so the job is offered one gesture past the deepest
    k it diverged at. Recognition is a property of the job, not of who was
    asked, so every browser's offers count. The threshold only ever moves up
    here; it comes back down as the diverged offers age out of the window.

    Quiet: the asking browser's newest `K_ENOUGH` offers of this job were all
    refused, and the last under `K_QUIET_HOURS` ago. Any other fate in
    between -- accepted, expired, diverged -- breaks the run: an offer the
    operator did not answer is not one they turned down. Per browser, because
    one operator's no is not the next operator's; with no browser named there
    is no rest to report.

    Arrival nudges are recorded at `k = 0` -- "you have been here before",
    nothing typed -- and are neither kind of evidence: read at `k > 0` only.
    """
    rows = store.query(
        "SELECT k, fate FROM offers WHERE tenant = ? AND workflow_id = ? AND k > 0"
        " ORDER BY at DESC, rowid DESC LIMIT ?",
        (tenant, workflow_id, K_WINDOW),
    )
    offer_after = K_OFFER_AFTER
    diverged = [int(row["k"]) for row in rows if row["fate"] == "diverged"]
    if len(rows) >= K_ENOUGH and 2 * len(diverged) >= len(rows):
        offer_after = max(offer_after, max(diverged) + 1)
    quiet_until = None
    if device_id:
        newest = store.query(
            "SELECT fate, at FROM offers"
            " WHERE tenant = ? AND workflow_id = ? AND device_id = ? AND k > 0"
            " ORDER BY at DESC, rowid DESC LIMIT ?",
            (tenant, workflow_id, device_id, K_ENOUGH),
        )
        if len(newest) == K_ENOUGH and all(row["fate"] in REFUSED for row in newest):
            until = datetime.fromisoformat(newest[0]["at"]) + timedelta(hours=K_QUIET_HOURS)
            if until > (now or datetime.now(UTC)):
                quiet_until = until.isoformat()
    return Counsel(offer_after=offer_after, quiet_until=quiet_until)
