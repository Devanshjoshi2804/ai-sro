"""What was offered, and what became of it.

Written by the extension, which made the offer, over `POST /v1/offers`. Read
per job, when its shape is served: the labelled record of whether recognition
was right. Offers that kept diverging move the job's threshold past the
gesture they diverged at; offers refused three times running rest the job for
a day.

The repository queries that gather `OfferRow`s -- `record_offer`'s insert and
`counsel`'s two selects, in the rig at `new_agent_arch/src/rig/offers.py` --
move to the application layer; this module keeps only the pure rules that
decide what a job's history means.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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


def fate_of(name: str) -> str:
    """`name` if it is a fate an offer can have; raised, named, otherwise."""
    if name not in FATES:
        raise ValueError(f"{name!r} is not a fate an offer can have")
    return name


@dataclass(frozen=True, slots=True)
class OfferRow:
    """The three columns `counsel_over` reads, and no more: a whole `Offer` is
    a row the rules have no use for."""

    k: int
    fate: str
    at: str


@dataclass(frozen=True, slots=True)
class Offer:
    """One offer the extension made from a recognised prefix, and its fate."""

    id: str
    tenant: str
    workflow_id: str
    device_id: str
    k: int
    fate: str
    at: str
    run_id: str | None = None


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


def clamped(at: str, now: datetime) -> str:
    """The browser's clock, never ahead of the rig's: parsed, made aware,
    and capped at `now`. `counsel_over` reads the newest offers and rests a
    job a day after the last refusal, and a browser a year fast would
    otherwise own the window, and the rest, for a year."""
    when = datetime.fromisoformat(at)
    when = (when if when.tzinfo else when.replace(tzinfo=UTC)).astimezone(UTC)
    return min(when, now).isoformat()


def counsel_over(
    window: Sequence[OfferRow], newest_for_device: Sequence[OfferRow], now: datetime
) -> Counsel:
    """What a job's newest offers say about offering it again.

    `window`: the tenant's newest `K_WINDOW` offers of the job with k > 0,
    newest first. `newest_for_device`: the asking browser's newest `K_ENOUGH`
    of the same, newest first; empty when no browser is named.

    Later: at least `K_ENOUGH` offers in `window` and half or more of them
    diverged, so the job is offered one gesture past the deepest k it
    diverged at. Recognition is a property of the job, not of who was asked,
    so every browser's offers count. The threshold only ever moves up here;
    it comes back down as the diverged offers age out of the window.

    Quiet: `newest_for_device` has exactly `K_ENOUGH` offers of this job, all
    refused, and the last under `K_QUIET_HOURS` ago. Any other fate in
    between -- accepted, expired, diverged -- breaks the run: an offer the
    operator did not answer is not one they turned down. With no browser named
    there is no rest to report: `newest_for_device` is empty, and a job nobody
    can be said to have refused is offered.

    Arrival nudges (k = 0) are excluded by the caller's query and are neither
    kind of evidence -- "you have been here before" with nothing typed is not
    a recognition that diverged and not an offer anyone turned down. Handed
    them anyway, this reads them like any other row; keeping them out is the
    repository's `k > 0`.
    """
    offer_after = K_OFFER_AFTER
    diverged = [row.k for row in window if row.fate == "diverged"]
    if len(window) >= K_ENOUGH and 2 * len(diverged) >= len(window):
        offer_after = max(offer_after, max(diverged) + 1)
    quiet_until = None
    newest = list(newest_for_device)
    if len(newest) == K_ENOUGH and all(row.fate in REFUSED for row in newest):
        until = datetime.fromisoformat(newest[0].at) + timedelta(hours=K_QUIET_HOURS)
        if until > now:
            quiet_until = until.isoformat()
    return Counsel(offer_after=offer_after, quiet_until=quiet_until)
