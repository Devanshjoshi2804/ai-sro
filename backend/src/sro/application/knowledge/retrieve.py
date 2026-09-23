from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.knowledge.vectors import embed_or_none
from sro.application.ports.embedding import Embedder
from sro.application.ports.repositories import UnitOfWork
from sro.domain.knowledge.entry import SUPPORTS_AUTOMATION, EntryKind, KnowledgeEntry


@dataclass(frozen=True, slots=True)
class Question:
    text: str = ""
    system: str | None = None
    kinds: tuple[EntryKind, ...] = ()
    limit: int = 20

    automation_only: bool = False


class Retrieve:
    def __init__(self, uow: UnitOfWork, embedder: Embedder) -> None:
        self._uow = uow
        self._embedder = embedder

    async def execute(self, ctx: RequestContext, question: Question) -> tuple[KnowledgeEntry, ...]:
        vector: tuple[float, ...] = ()
        if question.text.strip():
            embedded = await embed_or_none(self._embedder, (question.text,))
            vector = embedded[0] if embedded else ()

        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id,
                system=question.system,
                kinds=question.kinds,
                terms=question.text,
                embedding=vector,
                min_evidence=SUPPORTS_AUTOMATION if question.automation_only else None,
                limit=question.limit,
            )
        return found
