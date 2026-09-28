"""The rest of a conversation, once `POST /v1/ask` has named a job or a mail
has offered one: asking what an offer still needs, sending a drafted reply,
and looking for what the mail asks for.

Nothing here catches a refusal: `sro.interface.http.errors` maps
`AskerUnavailable` to 503 and `OverCap` to 429 once, for every route.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.domain.chat.asking import Pending
from sro.domain.chat.thread import ThreadId
from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    AskAboutOfferRequest,
    AskAboutOfferResponse,
    FromTheMailResponse,
    SendTheDraftRequest,
    SentTheDraftResponse,
)

router = APIRouter(tags=["chat"], dependencies=[TenantOnly])


@router.post("/chat/about-an-offer", status_code=status.HTTP_200_OK)
async def ask_about_an_offer(
    body: AskAboutOfferRequest, container: ContainerDep, ctx: ContextDep
) -> AskAboutOfferResponse:
    """Ask, in this operator's conversation, for what an offer still needs.

    200 and no run. This is the card handing a decision to the place decisions
    are made here: the question lands in the thread, the operator answers it in
    words, and when the last answer lands the conversation starts the run
    itself. Nothing about the job is settled by this call.
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
            ctx, pending, about=body.about, mail_thread=body.mail_thread, offer=body.offer
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
