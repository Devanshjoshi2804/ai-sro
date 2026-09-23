from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.knowledge.vectors import embed_or_none
from sro.application.ports.embedding import Embedder
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.knowledge.supersede import Verdict, judge


@dataclass(frozen=True, slots=True)
class Claim:
    system: str
    kind: EntryKind
    key: str
    title: str
    body: dict[str, object]
    source: str
    evidence: EvidenceLevel

    def as_text(self) -> str:
        return f"{self.title} — {self.key}"


@dataclass(frozen=True, slots=True)
class Recorded:
    unchanged: int = 0
    believed: int = 0
    recorded_not_believed: int = 0

    @property
    def total(self) -> int:
        return self.unchanged + self.believed + self.recorded_not_believed


class RecordClaims:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory, embedder: Embedder) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids
        self._embedder = embedder

    async def execute(self, ctx: RequestContext, claims: tuple[Claim, ...]) -> Recorded:
        if not claims:
            return Recorded()

        now = self._clock.now()
        unchanged = believed = not_believed = 0

        async with self._uow as uow:
            decided: list[tuple[Claim, KnowledgeEntry | None, Verdict]] = []
            for claim in claims:
                existing = await uow.knowledge.current(
                    ctx.tenant_id, system=claim.system, kind=claim.kind, key=claim.key
                )
                verdict = judge(
                    existing, source=claim.source, body=claim.body, evidence=claim.evidence
                )
                if verdict is Verdict.UNCHANGED:
                    unchanged += 1
                else:
                    decided.append((claim, existing, verdict))

            vectors = await _vectors(self._embedder, tuple(claim for claim, _, _ in decided))

            for (claim, existing, verdict), vector in zip(decided, vectors, strict=True):
                entry = KnowledgeEntry(
                    id=self._ids.new_knowledge_id(),
                    tenant_id=ctx.tenant_id,
                    system=claim.system,
                    kind=claim.kind,
                    key=claim.key,
                    title=claim.title,
                    body=claim.body,
                    source=claim.source,
                    evidence=claim.evidence,
                    observed_at=now,
                    embedding=vector,
                )
                if verdict is Verdict.RECORDED_NOT_BELIEVED:
                    not_believed += 1
                    entry.superseded_by = existing.id if existing else None
                else:
                    believed += 1
                    if existing is not None:
                        existing.superseded(entry)
                        await uow.knowledge.save(existing)
                await uow.knowledge.add(entry)

            await uow.commit()

        return Recorded(unchanged=unchanged, believed=believed, recorded_not_believed=not_believed)


async def _vectors(embedder: Embedder, claims: tuple[Claim, ...]) -> tuple[tuple[float, ...], ...]:
    return await embed_or_none(embedder, tuple(claim.as_text() for claim in claims))
