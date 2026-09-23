from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims
from sro.application.ports.repositories import UnitOfWork
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel

UNKNOWN_LIFE = timedelta(minutes=30)

SAFETY = 0.5


@dataclass(frozen=True, slots=True)
class Life:
    system: str
    observed: timedelta | None

    minted_at: datetime | None
    last_good_at: datetime | None

    @property
    def refresh_after(self) -> timedelta:
        return (self.observed or UNKNOWN_LIFE) * SAFETY

    def stale_at(self) -> datetime | None:
        return self.minted_at + self.refresh_after if self.minted_at else None

    def worth_refreshing(self, now: datetime) -> bool:
        due = self.stale_at()
        return due is not None and now >= due


class SessionLife:
    def __init__(self, uow: UnitOfWork, record: RecordClaims) -> None:
        self._uow = uow
        self._record = record

    async def minted(self, ctx: RequestContext, *, system: str, at: datetime) -> None:
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
        known = await self.of(ctx, system=system)
        if known.minted_at is None or known.last_good_at is None:
            return
        lived = known.last_good_at - known.minted_at
        if lived <= timedelta(0):
            return
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
