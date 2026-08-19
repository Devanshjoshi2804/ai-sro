"""How long this system's sessions actually last, learned rather than guessed.

The obvious plan is to sign in every two hours, or every four. Both are
guesses, and a guess here is expensive in both directions: too often and the
system signs the operator's own browser out of a WMS that permits one session;
too rarely and the first thing anybody notices is a batch failing at 3am.

Nothing in the credential says. The session is three opaque cookies with no
expiry to read -- so the number has to be measured, the way anything else here
is measured: watch when a session was minted, when it last worked, and when it
first did not, and keep the answer beside everything else known about that
system. A second customer's WMS gets its own number instead of inheriting ours.

Until a session has been seen to die, there is no measurement and the refresh
falls back to a deliberately short interval. Being early costs one login.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims
from sro.application.ports.repositories import UnitOfWork
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel

UNKNOWN_LIFE = timedelta(minutes=30)
"""What to assume before anything has been observed. Short on purpose: a
needless login costs a browser slot, a missed one costs the run."""

SAFETY = 0.5
"""Refresh at half the observed life. A session that lived four hours once may
live three the next time -- the identity provider counts idle time too, and
this system is idle most of the night."""


@dataclass(frozen=True, slots=True)
class Life:
    system: str
    observed: timedelta | None
    """The shortest life seen so far, or None while nothing has expired yet."""

    minted_at: datetime | None
    last_good_at: datetime | None

    @property
    def refresh_after(self) -> timedelta:
        return (self.observed or UNKNOWN_LIFE) * SAFETY

    def stale_at(self) -> datetime | None:
        """When this session should be replaced, if we know when it began."""
        return self.minted_at + self.refresh_after if self.minted_at else None

    def worth_refreshing(self, now: datetime) -> bool:
        due = self.stale_at()
        return due is not None and now >= due


class SessionLife:
    """Watch a session's clock, and say what it has been observed to be."""

    def __init__(self, uow: UnitOfWork, record: RecordClaims) -> None:
        self._uow = uow
        self._record = record

    async def minted(self, ctx: RequestContext, *, system: str, at: datetime) -> None:
        """A fresh session exists as of now."""
        await self._write(
            ctx, system, {"minted_at": at.isoformat(), "last_good_at": at.isoformat()}
        )

    async def worked(self, ctx: RequestContext, *, system: str, at: datetime) -> None:
        known = await self.of(ctx, system=system)
        await self._write(
            ctx,
            system,
            {
                "minted_at": known.minted_at.isoformat() if known.minted_at else at.isoformat(),
                "last_good_at": at.isoformat(),
                **({"observed_seconds": known.observed.total_seconds()} if known.observed else {}),
            },
        )

    async def died(self, ctx: RequestContext, *, system: str, at: datetime) -> None:
        """A session that used to work does not any more.

        The life recorded is from minting to the last call that worked, not to
        the failure: everything in between is when it may already have been
        dead, and taking the longer number would schedule the next refresh
        after the point sessions have been seen to expire.
        """
        known = await self.of(ctx, system=system)
        if known.minted_at is None or known.last_good_at is None:
            return
        lived = known.last_good_at - known.minted_at
        if lived <= timedelta(0):
            return
        # The shortest observed life, not the latest: one long weekend where
        # nothing was asked of it does not prove the session survived it.
        shortest = min(lived, known.observed) if known.observed else lived
        await self._write(
            ctx,
            system,
            {
                "observed_seconds": shortest.total_seconds(),
                "died_at": at.isoformat(),
                "minted_at": known.minted_at.isoformat(),
                "last_good_at": known.last_good_at.isoformat(),
            },
        )

    async def of(self, ctx: RequestContext, *, system: str) -> Life:
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, terms=_key(system), kinds=(EntryKind.QUIRK,), limit=5
            )
        body: dict[str, object] = next(
            (entry.body for entry in found if entry.key == _key(system) and entry.current), {}
        )
        seconds = body.get("observed_seconds")
        return Life(
            system=system,
            observed=timedelta(seconds=float(seconds))
            if isinstance(seconds, int | float)
            else None,
            minted_at=_when(body.get("minted_at")),
            last_good_at=_when(body.get("last_good_at")),
        )

    async def _write(self, ctx: RequestContext, system: str, body: dict[str, object]) -> None:
        await self._record.execute(
            ctx,
            (
                Claim(
                    system=system,
                    kind=EntryKind.QUIRK,
                    key=_key(system),
                    title=f"how long a {system} session lasts",
                    body=body,
                    source="observed by this system",
                    # Watched, not read off a document: the strongest thing
                    # anybody can say about a credential nobody can inspect.
                    evidence=EvidenceLevel.OBSERVED,
                ),
            ),
        )


def _key(system: str) -> str:
    return f"{system}/session/life"


def _when(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
