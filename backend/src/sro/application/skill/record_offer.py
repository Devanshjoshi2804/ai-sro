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
nothing: the belt behind `RecordOffer`'s own check should not leave a
half-offer behind it.

`RecordOffer` below is what `POST /v1/offers` calls. It is the class and the
function is the writer it ends on, because the checks a body has to pass --
is this a job this tenant has, is this a fate -- are answered against the
store and must all be answered before anything is written.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.shared.errors import DomainError, NotFound
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import FATES, Offer, clamped, fate_of, new_offer_id


class OfferRefused(DomainError):
    """The body named something that is not an offer this tenant could make.

    A body field naming a job that does not exist is not a missing endpoint,
    so this is the rig's 400 at `new_agent_arch/src/rig/api.py:1551` and not
    the 404 `/v1/workflows/{id}/evidence` answers: there the workflow IS the
    resource asked for, here it is one field of a request to create another.

    Never carries the value it refused. `str(exc)` is the `detail` of a
    problem document, and a refusal quoting the body puts the body in the
    access log of every proxy between the browser and here.
    """

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


class RecordOffer:
    """What a browser showed, and what became of it, checked before it is kept.

    A class taking a `RequestContext`, and the container method it replaces
    is why. `record_offer` below is a bare function, as `spent_today` is, and
    a bare function is normally called from the container without a class
    around it -- but that one took a bare `tenant_id`, so the route would have
    unpacked the caller itself, putting the tenant boundary in the interface
    layer at the one seam where passing the wrong tenant is the failure. The
    clock is held for the reason `ServeShapes` holds one: `clamped` needs an
    instant no route may read.

    The order below is the whole of this class. Both checks are answered
    against the store, and both are answered before `record_offer` mints an
    id -- a body that is refused must leave nothing behind, and a row written
    and then refused is one `counsel` reads for the next day either way.

    The session is entered here and nowhere else. `record_offer` takes the
    unit of work already open, because a `SqlUnitOfWork` has no repositories
    on it until `__aenter__` builds them.
    """

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
        """The offer as stored. `OfferRefused` on a job or a fate that is not one.

        `at` is the browser's own reading of when it showed the offer, and is
        allowed to be absent -- a nudge the extension reports late has one and
        a page that reports as it happens need not. Absent, the row carries
        this clock's instant rather than one the route read: which day an
        offer falls on decides when the job it belongs to comes back, and that
        is not the interface layer's to decide.
        """
        now = self._clock.now()
        async with self._uow as uow:
            try:
                # Tenant-scoped, and this is the whole of the check: a job of
                # somebody else's is one this tenant does not have.
                await uow.workflows.get(ctx.tenant_id, workflow_id)
            except NotFound as exc:
                raise OfferRefused("no such workflow") from exc
            if fate not in FATES:
                # Named forwards, never back: the caller is told what a fate
                # can be, and is not read their own string.
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
