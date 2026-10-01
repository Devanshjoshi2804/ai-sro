"""The offers an operator has standing: a job a card or a question in their chats is waiting on.

One offer is one run (`uq_workflow_runs_one_per_offer`), so whoever starts that job for the
operator some other way starts it under the offer, and a second answer finds the first run.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.asking import JOB, NEEDS, asked_under
from sro.domain.chat.standing import stands
from sro.domain.recording.sensitivity import is_secret_field

K_OFFERS_SEEN = 50

K_SHOWN_OFFERS = 5


@dataclass(frozen=True, slots=True)
class OpenOffer:
    id: str
    workflow_id: str
    title: str
    values: Mapping[str, str]
    # The run this offer started, when it did and that run is still going.
    run_id: str = ""


async def standing_offers(
    uow: UnitOfWork, ctx: RequestContext, now: datetime
) -> tuple[OpenOffer, ...]:
    """This operator's offers, newest first: open ones, and ones whose run is still going.

    An offer whose run has ended is spent: the card stays in the chat, but the job asked for
    again is new work."""
    async with uow:
        threads = await uow.threads.list_for_tenant(
            ctx.tenant_id, opened_by=ctx.principal_id, limit=K_OFFERS_SEEN
        )
        offers: list[OpenOffer] = []
        for thread in threads:
            asked = asked_under(thread.messages)
            decision = asked.decision if asked is not None else None
            if (
                asked is None
                or not decision
                or not decision.get("workflow_id")
                # A run's own question, or an offer set aside to resume, is not an offer to start.
                or decision.get("from_run")
                or decision.get("resume")
                or decision.get("kind") not in (JOB, NEEDS)
            ):
                continue
            values = decision.get("values")
            offers.append(
                OpenOffer(
                    id=str(decision.get("offer") or asked.id.value),
                    workflow_id=str(decision["workflow_id"]),
                    title=str(decision.get("title") or ""),
                    values={
                        str(k): str(v)
                        for k, v in (values.items() if isinstance(values, Mapping) else ())
                        if not is_secret_field(str(k))
                    },
                )
            )
        taken = await uow.workflow_runs.started_by_offers(ctx.tenant_id, [o.id for o in offers])
        standing: list[OpenOffer] = []
        for offer in offers:
            if offer.id not in taken:
                standing.append(offer)
                continue
            run = await uow.workflow_runs.get(ctx.tenant_id, taken[offer.id])
            if run is not None and stands(run, now):
                standing.append(replace(offer, run_id=run.id))
    return tuple(standing)


def open_ones(offers: tuple[OpenOffer, ...]) -> list[OpenOffer]:
    return [one for one in offers if not one.run_id][:K_SHOWN_OFFERS]
