"""What happens when the same thing is claimed twice.

The learning loop lives here. A scraped catalogue says an endpoint exists; a run
later proves what it answers. Both are claims about one key, and deciding
between them by timestamp would let a re-scrape undo everything execution has
learned. Evidence decides, and time only breaks ties.
"""

from __future__ import annotations

from enum import StrEnum

from sro.domain.knowledge.entry import EvidenceLevel, KnowledgeEntry


class Verdict(StrEnum):
    UNCHANGED = "unchanged"
    """The same claim, from the same source, saying the same thing. Ingest is
    re-runnable precisely because this exists."""

    SUPERSEDES = "supersedes"
    """The new claim replaces the old one, which stays, pointing forward."""

    RECORDED_NOT_BELIEVED = "recorded_not_believed"
    """Weaker evidence contradicting stronger. Kept -- a scrape disagreeing
    with a verified run is a fact about the scrape worth having -- but it does
    not become what the system believes."""


def judge(
    existing: KnowledgeEntry | None,
    *,
    source: str,
    body: dict[str, object],
    evidence: EvidenceLevel,
) -> Verdict:
    """What to do with a claim, given what is already believed about its key.

    Takes the incoming claim's three deciding fields rather than a whole entry:
    the caller has not minted one yet, and building a throwaway entity to ask a
    question is how identity fields end up carrying placeholder values.
    """
    if existing is None:
        return Verdict.SUPERSEDES

    if existing.source == source and existing.body == body:
        return Verdict.UNCHANGED

    if evidence.rank >= existing.evidence.rank:
        return Verdict.SUPERSEDES

    return Verdict.RECORDED_NOT_BELIEVED
