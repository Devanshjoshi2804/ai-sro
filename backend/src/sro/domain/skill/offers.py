from __future__ import annotations

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

K_OFFER_AFTER = 2

K_WINDOW = 10

K_ENOUGH = 3

K_QUIET_HOURS = 24

REFUSED = ("dismissed", "did_it")

FATES = ("accepted", "dismissed", "did_it", "expired", "diverged")


def new_offer_id() -> str:
    return "off_" + secrets.token_hex(16)


def fate_of(name: str) -> str:
    if name not in FATES:
        raise ValueError(f"{name!r} is not a fate an offer can have")
    return name


@dataclass(frozen=True, slots=True)
class OfferRow:
    k: int
    fate: str
    at: str


@dataclass(frozen=True, slots=True)
class Offer:
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
    quiet_until: str | None

    def as_json(self) -> dict[str, object]:
        return {
            "offer_after": self.offer_after,
            "later": self.offer_after > K_OFFER_AFTER,
            "quiet_until": self.quiet_until,
        }


def clamped(at: str, now: datetime) -> str:
    when = datetime.fromisoformat(at)
    when = (when if when.tzinfo else when.replace(tzinfo=UTC)).astimezone(UTC)
    return min(when, now).isoformat()


def counsel_over(
    window: Sequence[OfferRow], newest_for_device: Sequence[OfferRow], now: datetime
) -> Counsel:
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
