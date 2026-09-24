"""One sentence, read against the jobs this tenant was seen doing.

Ported from `new_agent_arch/src/rig/api.py:1495`. Tenant-only, as it is there
(`dependencies=[Depends(tenant_only)]`): reading a sentence is a model call
against the tenant's day, and a browser proving itself with its own secret must
not be able to spend the tenant's budget by typing into a box.

It resolves over the *workflows* a mining pass read out of what an operator
was seen doing, and it bills for the reading.

Offers, never starts. What comes back is a form the operator confirms; the
press that authorises a run is a different door.

Nothing here catches a refusal: `sro.interface.http.errors` maps
`AskerUnavailable` to 503 and `OverCap` to 429 once, for every route.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.domain.chat.asking import Pending
from sro.domain.chat.thread import ThreadId
from sro.domain.observation.attempts import DONE, NOTHING
from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    AskAboutOfferRequest,
    AskAboutOfferResponse,
    ChatRequest,
    ChatResponse,
    FromTheMailResponse,
    RunStartedRequest,
    SendTheDraftRequest,
    SentTheDraftResponse,
)

router = APIRouter(tags=["chat"], dependencies=[TenantOnly])


@router.post("/chat", status_code=status.HTTP_200_OK)
async def read_chat(body: ChatRequest, container: ContainerDep, ctx: ContextDep) -> ChatResponse:
    """Which job the operator meant, with what values, missing what.

    200 rather than 201: nothing is created. The reading leaves a `chats` row
    behind because the tenant was billed for it, but the answer is an offer and
    the operator may walk away from it.
    """
    read = await container.read_chat().execute(ctx, utterance=body.utterance)
    await container.record_attempt().execute(
        ctx,
        asked_for="ask for a job in words",
        came_of=DONE if read.workflow_id else NOTHING,
        why="" if read.workflow_id else "no job of this tenant's matched what was asked for",
        about={"workflow": read.workflow_id or ""},
    )
    return ChatResponse.of(read)


@router.post("/chat/about-an-offer", status_code=status.HTTP_200_OK)
async def ask_about_an_offer(
    body: AskAboutOfferRequest, container: ContainerDep, ctx: ContextDep
) -> AskAboutOfferResponse:
    """Ask, in this operator's conversation, for what an offer still needs.

    200 and no run. This is the card handing a decision to the place decisions
    are made here: the question lands in the thread, the operator answers it in
    words, and when the last answer lands the existing conversation path emits
    the `job` decision the browser starts. Nothing about the job is settled by
    this call.
    """
    pending = Pending(
        workflow_id=body.workflow_id,
        title=body.title,
        values=body.values,
        missing=tuple(body.missing),
        items=tuple(body.items),
        limits=body.limits,
        mail_thread=body.mail_thread,
        watched=body.watched,
    )
    return AskAboutOfferResponse(
        asked=await container.ask_about_the_offer().execute(
            ctx, pending, about=body.about, mail_thread=body.mail_thread
        )
    )


@router.post("/chat/send-the-draft", status_code=status.HTTP_200_OK)
async def send_the_draft(
    body: SendTheDraftRequest, container: ContainerDep, ctx: ContextDep
) -> SentTheDraftResponse:
    """Send the mail the operator read. The press is the authorisation.

    The one door in this system that writes to somebody outside it, and the
    narrowest: it takes two ids and no words. What goes out is the draft that
    was put in front of a person, read back from their own thread.
    """
    return SentTheDraftResponse(
        sent_to=await container.send_the_draft().execute(
            ctx, ThreadId(body.thread_id), body.message_id
        )
    )


@router.post("/chat/run-started", status_code=status.HTTP_204_NO_CONTENT)
async def run_started(body: RunStartedRequest, container: ContainerDep, ctx: ContextDep) -> None:
    """Say, in this operator's conversation, which run came of it.

    204 and nothing back: the caller already holds the run, and what this does
    is put it where the rest of the decision already lives. Nothing is started
    or changed by it.
    """
    await container.say_the_run_started().execute(ctx, run_id=body.run_id, title=body.title)


@router.post("/chat/from-the-mail", status_code=status.HTTP_200_OK)
async def from_the_mail(container: ContainerDep, ctx: ContextDep) -> FromTheMailResponse:
    """Read this operator's recent mail for the jobs it asks for.

    A look, not a subscription: the caller asks, and what comes back is what
    this look found. Nothing runs, and nothing about the mail is stored -- what
    lands is an offer in the operator's own thread, which the panel already
    draws a card and a press from.

    `POST` on a path that reads, because it is not a read: it spends the
    tenant's model budget, calls the operator's connector, and writes offers
    into a thread. A `GET` that did those is a `GET` a cache or a prefetch may
    fire.

    As the caller and nobody else. The mailbox is reached with this principal's
    own connector grant -- there is no parameter here for whose mail to read,
    which is a stronger guarantee than a check somebody has to remember.
    """
    return FromTheMailResponse.of(await container.from_the_mail().execute(ctx))
