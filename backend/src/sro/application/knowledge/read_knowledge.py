from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.skill.parameter import Evidence


@dataclass(frozen=True, slots=True)
class TaughtSkill:
    skill_id: str
    name: str
    system: str
    facility: str
    version: int
    stage: str
    taught_by: str
    taught_at: str
    clean_streak: int
    proposed_parameters: int


@dataclass(frozen=True, slots=True)
class KnowledgeSummary:
    system_counts: dict[str, int]
    kind_counts: dict[str, int]
    evidence_counts: dict[str, int]
    learned_from_runs: int

    superseded: int
    skills: tuple[TaughtSkill, ...]


class ReadKnowledge:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def summary(self, ctx: RequestContext) -> KnowledgeSummary:
        async with self._uow as uow:
            entries = await uow.knowledge.search(ctx.tenant_id, limit=10_000)
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=200)

        taught = tuple(
            TaughtSkill(
                skill_id=skill.id.value,
                name=skill.name,
                system=skill.objective_key.target_system,
                facility=skill.objective_key.facility,
                version=version.version,
                stage=version.stage.value,
                taught_by=version.provenance.induced_by.value,
                taught_at=version.provenance.induced_at.isoformat(),
                clean_streak=version.track_record.clean_streak,
                proposed_parameters=sum(
                    1 for p in version.parameters if p.evidence is Evidence.PROPOSED
                ),
            )
            for skill in skills
            if (version := skill.versions[-1] if skill.versions else None) is not None
        )

        return KnowledgeSummary(
            system_counts=_count(entries, lambda e: e.system),
            kind_counts=_count(entries, lambda e: e.kind.value),
            evidence_counts=_count(entries, lambda e: e.evidence.value),
            learned_from_runs=sum(1 for e in entries if e.source.startswith("run")),
            superseded=sum(1 for e in entries if not e.current),
            skills=taught,
        )

    async def search(
        self,
        ctx: RequestContext,
        *,
        text: str = "",
        system: str | None = None,
        kind: EntryKind | None = None,
        min_evidence: EvidenceLevel | None = None,
        limit: int = 50,
    ) -> tuple[KnowledgeEntry, ...]:
        async with self._uow as uow:
            return await uow.knowledge.search(
                ctx.tenant_id,
                system=system,
                kinds=(kind,) if kind else (),
                terms=text,
                min_evidence=min_evidence,
                limit=limit,
            )


def _count(entries: tuple[KnowledgeEntry, ...], by: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        key = by(entry)  # type: ignore[operator]
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: -pair[1]))
