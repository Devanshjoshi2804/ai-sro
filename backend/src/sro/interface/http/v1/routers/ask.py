"""One box, in front of both worlds.

An operator types a sentence, or a page they are on asks them something, and
the sentence is either an instruction -- a job this deployment has watched
somebody do -- or a question, whose answer is somewhere in the systems they
work in. `container.read_chat()` resolves the first. `POST /v1/lookups`
resolves the second. This decides which, so the extension does not have to.

The deciding is a word rule in `domain/lookup/asking`, no model, and here
rather than in the browser for the reason every rule in this codebase lives on
one side of the wire: a rule with a copy in two languages drifts on one of
them.

Both doors keep their own behaviour exactly. A job comes back as an offer
somebody presses; a lookup goes and looks, because a read writes nothing and
waiting for a press to answer a question is the shortcut this was built to
avoid.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.domain.lookup.asking import is_a_question
from sro.domain.observation.attempts import DONE, NOTHING
from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import AskRequest, AskResponse, ChatResponse, LookupResponse

router = APIRouter(tags=["ask"], dependencies=[TenantOnly])


@router.post("/ask", status_code=status.HTTP_200_OK)
async def ask(body: AskRequest, container: ContainerDep, ctx: ContextDep) -> AskResponse:
    """Whichever of the two this sentence was, answered by the half that owns it."""
    if not is_a_question(body.said):
        read = await container.read_chat().execute(ctx, utterance=body.said)
        await container.record_attempt().execute(
            ctx,
            asked_for="ask for a job in words",
            came_of=DONE if read.workflow_id else NOTHING,
            why="" if read.workflow_id else "no job of this tenant's matched what was asked for",
            about={"workflow": read.workflow_id or ""},
        )
        return AskResponse(kind="job", job=ChatResponse.of(read))

    planned = await container.plan_lookups().execute(ctx, question=body.said)
    if not body.execute or not planned.plan.ready:
        await container.record_attempt().execute(
            ctx,
            asked_for="ask a question",
            came_of=NOTHING if not planned.plan.ready else DONE,
            why="" if planned.plan.ready else "nothing here knows how to look that up",
        )
        return AskResponse(kind="lookup", lookup=LookupResponse.of(planned))
    answers = await container.run_lookups().execute(
        ctx, plan=planned.plan, allow_focus=body.allow_focus
    )
    await container.record_attempt().execute(ctx, asked_for="ask a question", came_of=DONE)
    return AskResponse(kind="lookup", lookup=LookupResponse.of(planned, answers))
