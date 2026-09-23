from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.knowledge.retrieve import Question, Retrieve
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap
from sro.domain.knowledge.entry import EntryKind, KnowledgeEntry
from sro.domain.lookup.plan import (
    INSTRUCTIONS,
    K_MAX_LOOKUPS,
    LOOKUP_SCHEMA,
    Lookup,
    Plan,
    open_question_for,
    uncited,
    unknown_targets,
)
from sro.domain.shared.prices import Answer

logger = logging.getLogger(__name__)

WHAT_TO_SHOW = (
    EntryKind.ENDPOINT,
    EntryKind.SCREEN,
    EntryKind.FIELD,
    EntryKind.QUIRK,
    EntryKind.QUESTION,
)

K_SHOWN = 40


@dataclass(frozen=True, slots=True)
class Planned:
    plan: Plan
    answer: Answer | None = None

    refused: str | None = None


class PlanLookups:
    def __init__(
        self,
        uow: UnitOfWork,
        retrieve: Retrieve,
        asker: Asker | None,
        *,
        model: str,
        clock: Clock,
        cap_usd: float,
    ) -> None:
        self._uow = uow
        self._retrieve = retrieve
        self._asker = asker
        self._model = model
        self._clock = clock
        self._cap = cap_usd

    async def execute(
        self, ctx: RequestContext, *, question: str, system: str | None = None
    ) -> Planned:
        asked = question.strip()
        if not asked:
            return Planned(Plan(question=""), refused="a question with nothing in it")

        asker = asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap)
        if why:
            raise OverCap(why)

        known = list(
            await self._retrieve.execute(
                ctx,
                Question(text=asked, system=system, kinds=WHAT_TO_SHOW, limit=K_SHOWN),
            )
        )
        if not known:
            return Planned(
                Plan(question=asked, why="this deployment knows nothing about these systems"),
                refused="nothing retrieved",
            )

        stopped = open_question_for(asked, known)
        if stopped is not None:
            return Planned(Plan(question=asked, asks=stopped, why=stopped.question))

        answer = await asker.ask(
            model=self._model,
            instructions=INSTRUCTIONS,
            evidence=_shown(asked, known),
            schema=LOOKUP_SCHEMA,
        )
        if answer.error or not isinstance(answer.data, dict):
            return Planned(Plan(question=asked), answer=answer, refused=answer.error or "no answer")

        lookups = _read(answer.data)
        if unknown := unknown_targets(lookups, known):
            return Planned(
                Plan(question=asked),
                answer=answer,
                refused=f"named {', '.join(unknown)}, which nothing here has seen",
            )
        if bare := uncited(lookups, known):
            return Planned(
                Plan(question=asked),
                answer=answer,
                refused=f"{', '.join(bare)} cites nothing it was shown",
            )

        return Planned(
            Plan(
                question=asked,
                lookups=tuple(lookups[:K_MAX_LOOKUPS]),
                why=str(answer.data.get("why") or ""),
            ),
            answer=answer,
        )


def _read(data: dict[str, object]) -> list[Lookup]:
    raw = data.get("lookups")
    if not isinstance(raw, list):
        return []
    found: list[Lookup] = []
    for one in raw:
        if not isinstance(one, dict):
            continue
        how = one.get("how")
        target = str(one.get("target") or "").strip()
        if how not in ("call", "screen") or not target:
            continue
        params = one.get("params")
        cites = one.get("cites")
        found.append(
            Lookup(
                system=str(one.get("system") or ""),
                how=how,
                target=target,
                params=(
                    {str(k): str(v) for k, v in params.items()} if isinstance(params, dict) else {}
                ),
                why=str(one.get("why") or ""),
                cites=tuple(str(c) for c in cites if c) if isinstance(cites, list) else (),
            )
        )
    return found


def _shown(question: str, known: list[KnowledgeEntry]) -> str:
    lines = [f"QUESTION: {question}", ""]
    for kind in WHAT_TO_SHOW:
        of_kind = [entry for entry in known if entry.kind is kind]
        if not of_kind:
            continue
        lines.append(f"{kind.value.upper()}S THIS DEPLOYMENT HAS SEEN")
        for entry in of_kind:
            lines.append(f"  {entry.key} :: {entry.title}")
            body = entry.body if isinstance(entry.body, dict) else {}
            if params := body.get("params"):
                lines.append(f"      params: {params}")
            if routes := body.get("seen_on_routes"):
                shown = routes[:6] if isinstance(routes, list) else routes
                lines.append(f"      seen on: {shown}")
        lines.append("")
    return "\n".join(lines)
