"""One offer the extension made, and what became of it.

Ported from `record_offer` in `new_agent_arch/src/rig/offers.py`. The rig's
version minted the id, checked the fate and pulled the browser's clock back
in one function that also wrote the row; here the record is built from the
domain's own pieces and handed to `OfferRepository`, and the two guards it
applied on the way are still applied here because nothing else applies them:

* **`fate_of`.** The `fate` column has no CHECK constraint, so the store will
  take any string at all. A fate nothing recognises is not a rejected offer
  and not an accepted one -- it is a row `counsel` silently reads as neither
  refused nor diverged, for as long as it stays in the window.
* **`clamped`.** `at` is the browser's clock, in whatever form it wrote it.
  `counsel` reads the newest offers and rests a job for a day after the last
  refusal, so a browser a year fast would otherwise own the window, and the
  rest, for a year.

Both run before the row exists. A refused fate writes nothing and commits
nothing: the belt behind the route's own check should not leave a half-offer
behind it.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import Offer, clamped, fate_of, new_offer_id


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
    """The offer as stored, id and all. `ValueError` on a fate that is not one.

    `at` is the browser's reading and `now` is the rig's; the row carries the
    earlier of the two. Both are parameters rather than a clock read in here,
    so the caller's clock is the one a test can move.
    """
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
