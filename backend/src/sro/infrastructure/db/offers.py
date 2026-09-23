from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import ChatRepository, OfferRepository
from sro.domain.chat.reading import ChatReading
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import Offer
from sro.domain.skill.offers import OfferRow as OfferWindow
from sro.infrastructure.db.codec import when
from sro.infrastructure.db.models import ChatRow, OfferRow

_NEWEST_FIRST = (OfferRow.at.desc(), OfferRow.seq.desc())


class SqlOfferRepository(OfferRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, offer: Offer) -> None:
        self._session.add(
            OfferRow(
                id=offer.id,
                tenant_id=offer.tenant,
                workflow_id=offer.workflow_id,
                device_id=offer.device_id,
                k=offer.k,
                fate=offer.fate,
                run_id=offer.run_id,
                at=when(offer.at),
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
        query = (
            select(OfferRow.fate, func.count())
            .where(OfferRow.tenant_id == tenant_id.value, OfferRow.workflow_id == workflow_id)
            .group_by(OfferRow.fate)
        )
        rows = (await self._session.execute(query)).all()
        return {fate: int(many) for fate, many in rows}

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[Offer, ...]:
        query = (
            select(OfferRow)
            .where(OfferRow.tenant_id == tenant_id.value, OfferRow.at >= when(since))
            .order_by(*_NEWEST_FIRST)
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
            .order_by(*_NEWEST_FIRST)
            .limit(limit)
        )
        rows = (await self._session.execute(query)).all()
        return tuple(OfferWindow(k=k, fate=fate, at=at.isoformat()) for k, fate, at in rows)


class SqlChatRepository(ChatRepository):
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
                at=when(reading.at),
            )
        )

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[ChatReading, ...]:
        query = (
            select(ChatRow)
            .where(ChatRow.tenant_id == tenant_id.value, ChatRow.at >= when(since))
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
