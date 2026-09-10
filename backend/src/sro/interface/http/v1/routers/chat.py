"""One sentence, read against the jobs this tenant was seen doing.

Ported from `new_agent_arch/src/rig/api.py:1495`. Tenant-only, as it is there
(`dependencies=[Depends(tenant_only)]`): reading a sentence is a model call
against the tenant's day, and a browser proving itself with its own secret must
not be able to spend the tenant's budget by typing into a box.

**Not `POST /v1/intent/resolve`.** That one resolves an utterance over this
tenant's *skills*, with no model call in it at all. This one resolves over the
*workflows* a mining pass read out of what an operator was seen doing, and it
bills for the reading. Two resolvers, two vocabularies, one verb between them.

Offers, never starts. What comes back is a form the operator confirms; the
press that authorises a run is a different door.

Nothing here catches a refusal: `sro.interface.http.errors` maps
`AskerUnavailable` to 503 and `OverCap` to 429 once, for every route.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"], dependencies=[TenantOnly])


@router.post("/chat", status_code=status.HTTP_200_OK)
async def read_chat(body: ChatRequest, container: ContainerDep, ctx: ContextDep) -> ChatResponse:
    """Which job the operator meant, with what values, missing what.

    200 rather than 201: nothing is created. The reading leaves a `chats` row
    behind because the tenant was billed for it, but the answer is an offer and
    the operator may walk away from it.
    """
    return ChatResponse.of(await container.read_chat().execute(ctx, utterance=body.utterance))
