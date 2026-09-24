from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import SpendRepository
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import DaySpend, ModelSpend
from sro.infrastructure.db.models import ModelSpendRow


class SqlSpendRepository(SpendRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, spent: ModelSpend) -> None:
        self._session.add(
            ModelSpendRow(
                id=spent.id,
                tenant_id=spent.tenant,
                model=spent.model,
                at=spent.at,
                in_tokens=spent.in_tokens,
                out_tokens=spent.out_tokens,
                thought_tokens=spent.thought_tokens,
                cost_usd=spent.cost_usd,
                unpriced=spent.unpriced,
            )
        )
        await self._session.flush()

    async def today(self, tenant_id: TenantId, *, now: datetime) -> DaySpend:
        aware = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        midnight = aware.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        spent = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(ModelSpendRow.cost_usd), 0.0),
                    func.count().filter(ModelSpendRow.unpriced),
                ).where(ModelSpendRow.tenant_id == tenant_id.value, ModelSpendRow.at >= midnight)
            )
        ).one()
        return DaySpend(cost_usd=float(spent[0]), blind=int(spent[1]))
