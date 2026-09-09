"""What a browser offered, and what became of it.

Ported from `new_agent_arch/src/rig/api.py:1548`. The one door in phase 4a
that writes, and the other half of `/v1/shapes`: shapes go out so the
extension can recognise a tail, and this is what came back -- the labelled
record `counsel` reads to decide what a job is offered at and when a job it
was refused three times running is offered again.

**A browser's, not the tenant's.** The rig let either through and read the
browser's id out of the body; here the browser is the one that proved itself
with `X-Device-Secret`, exactly as `/v1/shapes` names it, and a request that
proves no browser is refused rather than recorded under nobody. A job's rest
is per browser: an offer recorded against a browser the body merely named
would let one operator's extension spend a colleague's rest, or earn it, and a
row with no browser on it is evidence about a shift nobody worked. Refused
with 403 and not 404 for `tenant_only`'s reason -- the caller's tenant
credential was accepted, so this is not an enumeration channel.

**Nothing is written until the body has passed.** `RecordOffer` answers both
of its questions -- is this a job this tenant has, is this a fate -- before
`record_offer` mints an id, and the shape of the body is answered before that
by `RecordOfferRequest`. A row written and then refused is a row `counsel`
reads for the rest of the day.

**A refusal never echoes what it refused.** `OfferRefused` carries no value
out of the body, because `str(exc)` becomes the `detail` of a problem document
and a refusal quoting the body writes the body into every access log between
the browser and here.

Nothing here catches a domain error: `sro.interface.http.errors` maps them
once, for every route -- `OfferRefused` to the rig's own 400, and a body whose
shape is wrong to the 422 FastAPI's validation already answers.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sro.interface.http.asking import AskingDeviceDep
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import OfferRecordedResponse, RecordOfferRequest

router = APIRouter(tags=["offers"])


@router.post("/offers", status_code=status.HTTP_201_CREATED)
async def record_offer(
    container: ContainerDep,
    ctx: ContextDep,
    asking: AskingDeviceDep,
    body: RecordOfferRequest,
) -> OfferRecordedResponse:
    """One offer this browser showed, and what the operator did with it."""
    if asking is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="an offer is a browser's to record, and this request names none",
        )
    recorded = await container.record_offer().execute(
        ctx,
        workflow_id=body.workflow_id,
        device_id=asking,
        k=body.k,
        fate=body.fate,
        run_id=body.run_id,
        # The browser's reading, as it wrote it, for `clamped` to hold against
        # the server's. Passed on and never defaulted here: which day an offer
        # falls on decides when its job comes back, and a route that read a
        # clock would decide that.
        at=body.at.isoformat() if body.at else None,
    )
    return OfferRecordedResponse(offer_id=recorded.id)
