from __future__ import annotations

from datetime import datetime

from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import K_ENOUGH, K_WINDOW, Counsel, OfferRow, counsel_over


async def counsel(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    workflow_id: str,
    device_id: DeviceId | None = None,
    now: datetime,
) -> Counsel:
    window = await uow.offers.newest(tenant_id, workflow_id, limit=K_WINDOW)
    resting: tuple[OfferRow, ...] = ()
    if device_id is not None:
        resting = await uow.offers.newest_for_device(
            tenant_id, workflow_id, device_id, limit=K_ENOUGH
        )
    return counsel_over(window, resting, now)
