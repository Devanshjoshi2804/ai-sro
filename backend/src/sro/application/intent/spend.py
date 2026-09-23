from __future__ import annotations

from datetime import datetime

from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import DaySpend
from sro.whose import attribute


async def spent_today(uow: UnitOfWork, tenant_id: TenantId, *, now: datetime) -> DaySpend:
    return await uow.spend.today(tenant_id, now=now)


async def over_cap(
    uow: UnitOfWork, tenant_id: TenantId, *, now: datetime, cap_usd: float
) -> str | None:
    attribute(tenant=tenant_id.value)
    if cap_usd < 0:
        return None
    day = await spent_today(uow, tenant_id, now=now)
    if day.cost_usd >= cap_usd or day.blind:
        return (
            f"daily cap reached: ${day.cost_usd:.4f} of ${cap_usd:.2f} spent today,"
            f" {day.blind} unpriced call(s)"
        )
    return None
