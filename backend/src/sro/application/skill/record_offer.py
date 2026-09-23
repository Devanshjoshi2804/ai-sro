from __future__ import annotations

from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.shared.errors import DomainError, NotFound
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import FATES, Offer, clamped, fate_of, new_offer_id


class OfferRefused(DomainError):
    code = "offer_refused"


async def record_offer(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    workflow_id: str,
    device_id: DeviceId,
    k: int,
    fate: str,
    run_id: str | None,
    at: str,
    now: datetime,
) -> Offer:
    offer = Offer(
        id=new_offer_id(),
        tenant=tenant_id.value,
        workflow_id=workflow_id,
        device_id=device_id.value,
        k=k,
        fate=fate_of(fate),
        at=clamped(at, now),
        run_id=run_id,
    )
    await uow.offers.record(offer)
    await uow.commit()
    return offer


class RecordOffer:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self,
        ctx: RequestContext,
        *,
        workflow_id: str,
        device_id: DeviceId,
        k: int,
        fate: str,
        run_id: str | None,
        at: str | None,
    ) -> Offer:
        now = self._clock.now()
        async with self._uow as uow:
            try:
                await uow.workflows.get(ctx.tenant_id, workflow_id)
            except NotFound as exc:
                raise OfferRefused("no such workflow") from exc
            if fate not in FATES:
                raise OfferRefused(f"fate must be one of {', '.join(FATES)}")
            return await record_offer(
                uow,
                tenant_id=ctx.tenant_id,
                workflow_id=workflow_id,
                device_id=device_id,
                k=k,
                fate=fate,
                run_id=run_id,
                at=at or now.isoformat(),
                now=now,
            )
