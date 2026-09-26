from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.skill.job_facts import runnable_jobs
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.chat.reading import INSTRUCTIONS, UNDERSTAND_SCHEMA, ChatReading, new_chat_id
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.learned import demanded
from sro.domain.skill.workflow import Workflow


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


async def understand(
    utterance: str,
    workflows: list[Workflow],
    asker: Asker,
    model: str,
    asked_by: Mapping[str, Sequence[str]] = MappingProxyType({}),
) -> Understood:
    held = [
        {
            "id": w.id,
            "title": w.title,
            "narrative": w.narrative,
            "parameters": [
                {"name": p.get("name"), "seen": p.get("seen_values", [])}
                for p in w.parameters
                if isinstance(p, dict)
            ],
            **({"asked_by": list(said)} if (said := asked_by.get(w.id)) else {}),
        }
        for w in workflows
    ]
    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=json.dumps(
            {"said": utterance, "jobs": held},
            indent=2,
            ensure_ascii=False,
        ),
        schema=UNDERSTAND_SCHEMA,
    )
    if answer.data is None:
        return Understood(None, answer)
    by_id = {w.id: w for w in workflows}
    chosen = by_id.get(str(answer.data.get("workflow_id") or ""))
    if chosen is None:
        return Understood(None, answer)
    declared = {p.get("name") for p in chosen.parameters if isinstance(p, dict)}
    raw = answer.data.get("values")
    pairs = (
        (p.get("name"), p.get("value"))
        for p in (raw if isinstance(raw, list) else ())
        if isinstance(p, dict)
    )
    read = [(k, v) for k, v in pairs if isinstance(k, str) and isinstance(v, str)]
    values = {k: v for k, v in read if k in declared}
    unasked = sorted({k for k, _ in read if k not in declared})
    aside = {k: v for k, v in read if k not in declared}
    items = _things(answer.data.get("items"), declared)
    nearly = answer.data.get("also")
    also = [
        one
        for one in (nearly if isinstance(nearly, list) else [])
        if isinstance(one, str) and one in by_id and one != chosen.id
    ]
    named = {name for name, _ in read}
    settled = (
        bool(also) and _fills(chosen, named) and not any(_fills(by_id[one], named) for one in also)
    )
    if settled:
        also = []
    sure = (bool(answer.data.get("sure", True)) or settled) and not also
    supplied = [{**values, **item} for item in items] or [values]
    items = [item for item in items if item]
    wanted = {
        name
        for parameter in chosen.parameters
        if isinstance(parameter, dict)
        and isinstance(name := parameter.get("name"), str)
        and demanded(parameter)
    }
    missing = sorted(
        name
        for name in declared
        if isinstance(name, str) and name in wanted and any(name not in one for one in supplied)
    )
    return Understood(
        chosen.id, answer, values, missing, sure, also, items, aside=aside, unasked=unasked
    )


def _fills(job: Workflow, said: set[str]) -> bool:
    declared = {
        str(name)
        for one in job.parameters
        if isinstance(one, dict) and (name := one.get("name")) and demanded(one)
    }
    return declared <= said


def _things(raw: object, declared: set[object]) -> list[dict[str, str]]:
    things: list[dict[str, str]] = []
    for one in raw if isinstance(raw, list) else ():
        if not isinstance(one, dict):
            continue
        said_values = one.get("values")
        pairs = (
            (pair.get("name"), pair.get("value"))
            for pair in (said_values if isinstance(said_values, list) else [])
            if isinstance(pair, dict)
        )
        said = {
            name: value
            for name, value in pairs
            if isinstance(name, str) and name in declared and isinstance(value, str)
        }
        things.append(said)
    return things


async def read_utterance(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    utterance: str,
    asker: Asker,
    model: str,
    now: datetime,
) -> Understood:
    facts = await runnable_jobs(uow, tenant_id, await uow.workflows.known(tenant_id))
    workflows = [one.workflow for one in facts]
    asked_by = {one.workflow.id: texts(mails_behind(one.workflow, one.by_id)) for one in facts}
    got = await understand(
        utterance, workflows, asker, model, {w: said for w, said in asked_by.items() if said}
    )
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
