from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime

from sro.application.chat.candidates import candidate_of, chore_named, rank_jobs, sign_in_names
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.asking import ask
from sro.application.skill.job_facts import JobFacts, job_facts
from sro.domain.chat.reading import ChatReading, new_chat_id
from sro.domain.chat.request import Candidate, read_of
from sro.domain.execution.compiled import why_not
from sro.domain.prompts.read_request import READ_REQUEST
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer

K_A_CHORE = "signing in is the session broker's work, never a request's"


@dataclass(frozen=True, slots=True)
class Understood:
    workflow_id: str | None
    answer: Answer
    values: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    sure: bool = True

    also: list[str] = field(default_factory=list)

    items: list[dict[str, str]] = field(default_factory=list)

    aside: dict[str, str] = field(default_factory=dict)

    unasked: list[str] = field(default_factory=list)

    cannot_run: list[str] = field(default_factory=list)

    refused: dict[str, str] = field(default_factory=dict)


def shown(candidate: Candidate) -> dict[str, object]:
    return {
        "id": candidate.id,
        "title": candidate.title,
        "fields": [
            {
                "name": one.name,
                "labels": list(one.labels),
                "aliases": sorted(w for w, f in candidate.aliases.items() if f == one.name),
                "seen": list(candidate.seen.get(one.name, ())),
                "filled_before": one.kind != "never",
            }
            for one in candidate.fields
        ],
        **({"asked_by": list(candidate.asked_by)} if candidate.asked_by else {}),
    }


async def understand(
    thread: str, candidates: Sequence[Candidate], asker: Asker, *, question: str = ""
) -> Understood:
    if not candidates:
        return Understood(None, Answer(data={}))
    answer = await ask(
        asker,
        READ_REQUEST,
        trusted={"question": question} if question else {},
        untrusted={
            "thread": thread,
            "candidates": json.dumps(
                [shown(one) for one in candidates], indent=2, ensure_ascii=False
            ),
        },
    )
    if answer.data is None:
        return Understood(None, answer)
    read = read_of(answer.data, candidates, thread)
    return Understood(
        read.job,
        answer,
        read.values,
        read.missing,
        read.sure,
        read.also,
        read.items,
        aside=read.aside,
        unasked=sorted(read.aside),
        refused=read.refused,
    )


async def read_request(
    text: str, facts: Sequence[JobFacts], asker: Asker, *, held: Mapping[str, int]
) -> Understood:
    chore = chore_named(text, facts)
    if chore is not None:
        return Understood(chore.workflow.id, Answer(data={}), cannot_run=[K_A_CHORE])
    logins = sign_in_names(facts)
    ranked = rank_jobs(text, facts, held=held)
    return await understand(text, [candidate_of(one, logins=logins) for one in ranked], asker)


async def held_runs(uow: UnitOfWork, tenant_id: TenantId) -> dict[str, int]:
    return {job: held for job, (_, held) in (await uow.workflow_runs.tallies(tenant_id)).items()}


async def offer_check(
    uow: UnitOfWork,
    tenant_id: TenantId,
    got: Understood,
    facts: Sequence[JobFacts],
    *,
    now: datetime,
) -> Understood:
    picked = next((one for one in facts if one.workflow.id == got.workflow_id), None)
    if picked is None or got.cannot_run:
        return got
    given = {**{name: value for one in got.items for name, value in one.items()}, **got.values}
    compiled = (
        (await job_facts(uow, tenant_id, [picked.workflow], now=now, values=given))[0].compiled
        if given
        else picked.compiled
    )
    return got if compiled.runnable else replace(got, cannot_run=why_not(compiled.reasons))


async def read_utterance(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    utterance: str,
    asker: Asker,
    now: datetime,
) -> Understood:
    facts = await job_facts(uow, tenant_id, await uow.workflows.known(tenant_id), now=now)
    got = await read_request(utterance, facts, asker, held=await held_runs(uow, tenant_id))
    got = await offer_check(uow, tenant_id, got, facts, now=now)
    answer = got.answer
    await uow.chats.record(
        ChatReading(
            id=new_chat_id(),
            tenant=tenant_id.value,
            at=now.isoformat(),
            workflow_id=got.workflow_id,
            in_tokens=answer.in_tokens,
            out_tokens=answer.out_tokens,
            thought_tokens=answer.thought_tokens,
            cost_usd=answer.cost_usd,
            unpriced=answer.unpriced,
            error=answer.error,
        )
    )
    await uow.commit()
    return got
