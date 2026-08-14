"""Find what is known, structurally first.

The order matters more than the ranking. Filter by system, kind and entity, and
only then let similarity order what survived. A nearest neighbour over the whole
store returns another system's endpoint with total confidence, and a wrong
answer that is confident and fast is the failure mode this whole design is
arranged against.
"""

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
    """Keep only claims strong enough to drive a call. A screen's help text is
    worth showing an operator and is not worth building a request from."""


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
                # Terms still narrow when a vector is present: similarity is an
                # ordering, and on a store this size it will always return
                # twenty of something.
                terms=question.text if not vector else "",
                embedding=vector,
                min_evidence=SUPPORTS_AUTOMATION if question.automation_only else None,
                limit=question.limit,
            )
        return found
