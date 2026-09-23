from __future__ import annotations

from enum import StrEnum

from sro.domain.knowledge.entry import EvidenceLevel, KnowledgeEntry


class Verdict(StrEnum):
    UNCHANGED = "unchanged"

    SUPERSEDES = "supersedes"

    RECORDED_NOT_BELIEVED = "recorded_not_believed"


def judge(
    existing: KnowledgeEntry | None,
    *,
    source: str,
    body: dict[str, object],
    evidence: EvidenceLevel,
) -> Verdict:
    if existing is None:
        return Verdict.SUPERSEDES

    if existing.source == source and existing.body == body:
        return Verdict.UNCHANGED

    if evidence.rank >= existing.evidence.rank:
        return Verdict.SUPERSEDES

    return Verdict.RECORDED_NOT_BELIEVED
