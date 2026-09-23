from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import SpendRepository
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import DaySpend
from sro.infrastructure.db.models import ChatRow, IntentRow, MiningPassRow, WorkflowRunRow

_BILLED = (
    (
        IntentRow.tenant_id,
        IntentRow.cost_usd,
        IntentRow.created_at,
        and_(IntentRow.unpriced, IntentRow.error.is_(None)),
    ),
    (
        MiningPassRow.tenant_id,
        MiningPassRow.cost_usd,
        MiningPassRow.started_at,
        and_(MiningPassRow.unpriced, MiningPassRow.error.is_(None)),
    ),
    (
        WorkflowRunRow.tenant_id,
        WorkflowRunRow.cost_usd,
        WorkflowRunRow.started_at,
        and_(WorkflowRunRow.unpriced, WorkflowRunRow.cost_usd == 0.0),
    ),
    (
        ChatRow.tenant_id,
        ChatRow.cost_usd,
        ChatRow.at,
        and_(ChatRow.unpriced, ChatRow.error.is_(None)),
    ),
)


class SqlSpendRepository(SpendRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def today(self, tenant_id: TenantId, *, now: datetime) -> DaySpend:
        aware = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        midnight = aware.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        usd, blind = 0.0, 0
        for tenant_column, cost, clock, blind_is in _BILLED:
            spent = (
                await self._session.execute(
                    select(func.coalesce(func.sum(cost), 0.0), func.count().filter(blind_is)).where(
                        tenant_column == tenant_id.value, clock >= midnight
                    )
                )
            ).one()
            usd, blind = usd + float(spent[0]), blind + int(spent[1])
        return DaySpend(cost_usd=usd, blind=blind)
