"""One question, asked of every system that could answer it.

The read half of the chat door. `POST /v1/chat` reads a sentence against the
jobs an operator was seen DOING and offers one back; this reads a question
against what the systems KNOW and goes and gets the answer. Two doors because
they are two questions: a job is mined from evidence, a lookup is planned from
knowledge, and `umbrella` is explicit that looking something up is a step of a
job and never a job itself.

Tenant-only, as the chat door is, and for the same reason: this spends the
tenant's budget on a model call and then drives the tenant's browser. A device
proving itself with its own secret must not be able to do either by typing
into a box.

**Reads only, and that is structural rather than promised.** The plan can only
express a GET or a screen; the address must be one this deployment has already
watched answer; the schema has no shape for a write. A question arriving from
somewhere untrusted -- a mail the operator has open, say -- reaches this door
as text, and there is nothing for "and then delete the old one" to become.

`execute=false` plans and stops, which is what makes the plan readable before
anything leaves the building.

Nothing here catches a refusal: `sro.interface.http.errors` maps
`AskerUnavailable` to 503 and `OverCap` to 429 once, for every route.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import LookupRequest, LookupResponse

router = APIRouter(tags=["lookups"], dependencies=[TenantOnly])


@router.post("/lookups", status_code=status.HTTP_200_OK)
async def look(body: LookupRequest, container: ContainerDep, ctx: ContextDep) -> LookupResponse:
    """Where the answer lives, and -- unless asked not to -- the answer.

    200 rather than 201: nothing is created. A lookup leaves no row of its own
    behind; what it costs is billed through the model call, and what it found
    belongs to whoever asked rather than to this deployment.
    """
    planned = await container.plan_lookups().execute(
        ctx, question=body.question, system=body.system
    )
    if not body.execute or not planned.plan.ready:
        # A plan that stops on an open question, or one that was refused, has
        # nothing to execute -- and executing "no lookups" would say a question
        # was answered by nobody rather than that it was never asked.
        return LookupResponse.of(planned)

    answers = await container.run_lookups().execute(
        ctx, plan=planned.plan, allow_focus=body.allow_focus
    )
    return LookupResponse.of(planned, answers)
