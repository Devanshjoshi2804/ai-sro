"""What was offered on Postgres, and what a sentence at the chat door cost.

The rules here are the rig's -- ``record_offer`` and ``counsel``'s two selects
in ``rig/offers.py``, the ``chats`` insert and select in ``rig/api.py`` -- and
they were SQLite there. What had to be translated rather than copied is marked
where it happens:

* ``ORDER BY at DESC, rowid DESC`` becomes ``ORDER BY at DESC, seq DESC`` on an
  identity column. SQLite's ``rowid`` is a real column with a real order;
  Postgres promises nothing at all about the order of two rows that tie on
  ``at``, and several offers of one job routinely carry the same second because
  the extension sends whole-second ISO instants. The three newest offers of a
  browser decide whether a job is rested, so the tie has to break on arrival.
* The rig kept every clock as text and compared it as text. ``at`` is
  ``timestamptz`` here because both indexes order on it and an offset-less
  string sorts beside an offset-bearing one with neither being wrong. The
  records still carry ISO strings, so this converts on both edges.
* ``k > 0`` stays in the query rather than moving to ``counsel_over``. An
  arrival nudge is not evidence either way, and the domain says so, but keeping
  it out is what lets ``LIMIT`` mean what it says: a window of ten that a run of
  nudges could fill is not a window of ten offers.

The row-to-record mapping lives here rather than in ``mappers.py``: a
repository's mapping belongs with the repository, and neither shape is read by
anything else.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import ChatRepository, OfferRepository
from sro.domain.chat.reading import ChatReading
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import Offer

# The domain's three-column window row, aliased apart from the table of the
# same name. ``counsel_over`` reads k, fate and at and has no use for the rest.
from sro.domain.skill.offers import OfferRow as OfferWindow
from sro.infrastructure.db.models import ChatRow, OfferRow


def _when(moment: str) -> datetime:
    """An ISO instant as a real timestamp, in UTC when it said nothing.

    The extension writes ``toISOString``, which always says ``Z``; a naive
    string that slipped through is read as UTC rather than as the server's local
    zone, because a naive local instant beside the UTC ones lands an offer hours
    from where it belongs in a window of ten.
    """
    parsed = datetime.fromisoformat(moment)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class SqlOfferRepository(OfferRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, offer: Offer) -> None:
        # Plain insert, no upsert: an offer is a thing that happened once, and
        # its id is minted where it is made. Two offers of one job in one second
        # are two rows, which is why ``seq`` exists.
        self._session.add(
            OfferRow(
                id=offer.id,
                tenant_id=offer.tenant,
                workflow_id=offer.workflow_id,
                device_id=offer.device_id,
                k=offer.k,
                fate=offer.fate,
                run_id=offer.run_id,
                at=_when(offer.at),
            )
        )

    async def newest(
        self, tenant_id: TenantId, workflow_id: str, *, limit: int
    ) -> tuple[OfferWindow, ...]:
        return await self._window(
            OfferRow.tenant_id == tenant_id.value,
            OfferRow.workflow_id == workflow_id,
            limit=limit,
        )

    async def newest_for_device(
        self, tenant_id: TenantId, workflow_id: str, device_id: DeviceId, *, limit: int
    ) -> tuple[OfferWindow, ...]:
        return await self._window(
            OfferRow.tenant_id == tenant_id.value,
            OfferRow.workflow_id == workflow_id,
            OfferRow.device_id == device_id.value,
            limit=limit,
        )

    async def fates(self, tenant_id: TenantId, workflow_id: str) -> Mapping[str, int]:
        # No ``k > 0`` and no limit, unlike the window above: this is the tally
        # of what the job was offered for and what came of it, and an arrival
        # nudge is still an offer that was made.
        query = (
            select(OfferRow.fate, func.count())
            .where(OfferRow.tenant_id == tenant_id.value, OfferRow.workflow_id == workflow_id)
            .group_by(OfferRow.fate)
        )
        rows = (await self._session.execute(query)).all()
        return {fate: int(many) for fate, many in rows}

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[Offer, ...]:
        # The whole offer, and every one of them: the audit asks what this
        # tenant's browsers were shown, so neither the window's ``k > 0`` nor
        # its limit applies. The ``seq`` tiebreak does, for the same reason it
        # does there -- several offers routinely carry one second.
        query = (
            select(OfferRow)
            .where(OfferRow.tenant_id == tenant_id.value, OfferRow.at >= _when(since))
            .order_by(OfferRow.at.desc(), OfferRow.seq.desc())
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(
            Offer(
                id=row.id,
                tenant=row.tenant_id,
                workflow_id=row.workflow_id,
                device_id=row.device_id,
                k=row.k,
                fate=row.fate,
                run_id=row.run_id,
                at=row.at.isoformat(),
            )
            for row in rows
        )

    async def _window(self, *where: ColumnElement[bool], limit: int) -> tuple[OfferWindow, ...]:
        query = (
            select(OfferRow.k, OfferRow.fate, OfferRow.at)
            .where(*where, OfferRow.k > 0)
            .order_by(OfferRow.at.desc(), OfferRow.seq.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(query)).all()
        return tuple(OfferWindow(k=k, fate=fate, at=at.isoformat()) for k, fate, at in rows)


class SqlChatRepository(ChatRepository):
    """The bill for the chat door, and nothing else it read.

    There is no column for the sentence and there is no method that would write
    one. The row exists for the cap and the spend line; the words are an
    operator's about their own warehouse.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, reading: ChatReading) -> None:
        self._session.add(
            ChatRow(
                id=reading.id,
                tenant_id=reading.tenant,
                workflow_id=reading.workflow_id,
                in_tokens=reading.in_tokens,
                out_tokens=reading.out_tokens,
                thought_tokens=reading.thought_tokens,
                cost_usd=reading.cost_usd,
                unpriced=reading.unpriced,
                error=reading.error,
                at=_when(reading.at),
            )
        )

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[ChatReading, ...]:
        query = (
            select(ChatRow)
            .where(ChatRow.tenant_id == tenant_id.value, ChatRow.at >= _when(since))
            # The id breaks the tie, as `seq` does for offers: `at` comes off
            # the record rather than off a server clock, so two readings can
            # carry one instant and there is no arrival column to fall back on.
            .order_by(ChatRow.at.desc(), ChatRow.id.desc())
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(
            ChatReading(
                id=row.id,
                tenant=row.tenant_id,
                at=row.at.isoformat(),
                workflow_id=row.workflow_id,
                in_tokens=row.in_tokens,
                out_tokens=row.out_tokens,
                thought_tokens=row.thought_tokens,
                cost_usd=row.cost_usd,
                unpriced=row.unpriced,
                error=row.error,
            )
            for row in rows
        )
