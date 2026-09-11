"""One reading of this tenant's unread gestures, asked for on purpose.

Same shape as `mine.py` and the same reason: this spends the tenant's model
budget, hundreds of calls at once in the worst case, so a device token opening
its own doors must not be able to trigger it.

**Not fired on ingest.** `POST /v1/observations` stores evidence and answers
202 without reading a byte of it; the reading is a separate, billed pass, and
that separation is the whole of what its own docstring means by "read later".

Nothing here catches a refusal: `sro.interface.http.errors` maps
`AskerUnavailable` to 503 and `OverCap` to 429 once, for every route.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import ReadGesturesResponse

router = APIRouter(tags=["gestures"], dependencies=[TenantOnly])


@router.post("/gestures/read", status_code=status.HTTP_200_OK)
async def read_gestures(container: ContainerDep, ctx: ContextDep) -> ReadGesturesResponse:
    """Read every one of this tenant's gestures that has no reading yet.

    No body: the tenant comes from the caller, same as `/v1/mine`. 200 rather
    than 202, and for the same reason -- the caller is billed for whatever
    this reads, so answering "accepted" and hanging up would leave nobody
    holding the receipt.
    """
    read = await container.read_gestures().execute(ctx)
    return ReadGesturesResponse(read=read)
