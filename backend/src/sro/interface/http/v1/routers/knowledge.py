"""What the organisation knows. Read-only."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Query

from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    KnowledgeEntryModel,
    KnowledgeSummaryModel,
    TaughtSkillModel,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/summary")
async def summary(container: ContainerDep, ctx: ContextDep) -> KnowledgeSummaryModel:
    """One person teaches; the tenant knows. This is that, counted."""
    found = await container.read_knowledge().summary(ctx)
    return KnowledgeSummaryModel(
        system_counts=found.system_counts,
        kind_counts=found.kind_counts,
        evidence_counts=found.evidence_counts,
        learned_from_runs=found.learned_from_runs,
        superseded=found.superseded,
        skills=[TaughtSkillModel(**asdict(skill)) for skill in found.skills],
    )


@router.get("")
async def search(
    container: ContainerDep,
    ctx: ContextDep,
    q: Annotated[str, Query()] = "",
    system: Annotated[str | None, Query()] = None,
    kind: Annotated[EntryKind | None, Query()] = None,
    min_evidence: Annotated[EvidenceLevel | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[KnowledgeEntryModel]:
    entries = await container.read_knowledge().search(
        ctx, text=q, system=system, kind=kind, min_evidence=min_evidence, limit=limit
    )
    return [
        KnowledgeEntryModel(
            id=str(entry.id),
            system=entry.system,
            kind=entry.kind.value,
            key=entry.key,
            title=entry.title,
            source=entry.source,
            evidence=entry.evidence.value,
            observed_at=entry.observed_at,
            body=dict(entry.body),
        )
        for entry in entries
    ]
