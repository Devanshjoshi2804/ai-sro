from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims
from sro.application.ports.repositories import UnitOfWork
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry


@dataclass(frozen=True, slots=True)
class Ambiguity:
    system: str
    key: str

    question: str
    options: tuple[str, ...]
    because: tuple[str, ...] = ()


class AskAbout:
    def __init__(self, uow: UnitOfWork, record: RecordClaims) -> None:
        self._uow = uow
        self._record = record

    async def raise_question(self, ctx: RequestContext, ambiguity: Ambiguity) -> None:
        async with self._uow as uow:
            existing = await uow.knowledge.search(
                ctx.tenant_id, terms=ambiguity.key, kinds=(EntryKind.QUESTION,), limit=5
            )
        if any(entry.key == ambiguity.key for entry in existing):
            return

        await self._record.execute(
            ctx,
            (
                Claim(
                    system=ambiguity.system,
                    kind=EntryKind.QUESTION,
                    key=ambiguity.key,
                    title=ambiguity.question,
                    body={
                        "question": ambiguity.question,
                        "options": list(ambiguity.options),
                        "because": list(ambiguity.because),
                    },
                    source="ambiguity",
                    evidence=EvidenceLevel.ASSERTED,
                ),
            ),
        )

    async def answer(
        self, ctx: RequestContext, *, system: str, key: str, chosen: str, by: str
    ) -> None:
        await self._record.execute(
            ctx,
            (
                Claim(
                    system=system,
                    kind=EntryKind.QUESTION,
                    key=key,
                    title=f"{key}: {chosen}",
                    body={"answer": chosen, "answered_by": by},
                    source=f"operator:{by}",
                    evidence=EvidenceLevel.OBSERVED,
                ),
            ),
        )

    async def settled(self, ctx: RequestContext, *, key: str) -> str | None:
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, terms=key, kinds=(EntryKind.QUESTION,), limit=10
            )
        for entry in found:
            if entry.key == key and entry.current:
                answer = entry.body.get("answer")
                if isinstance(answer, str):
                    return answer
        return None

    async def outstanding(self, ctx: RequestContext) -> tuple[KnowledgeEntry, ...]:
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, kinds=(EntryKind.QUESTION,), limit=200
            )
        return tuple(entry for entry in found if entry.current and "answer" not in entry.body)
