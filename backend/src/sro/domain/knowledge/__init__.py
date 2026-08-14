"""What is known about a system. Start at ``entry.py``, then ``supersede.py``."""

from sro.domain.knowledge.entry import (
    SUPPORTS_AUTOMATION,
    EntryKind,
    EvidenceLevel,
    KnowledgeEntry,
    KnowledgeId,
)
from sro.domain.knowledge.supersede import Verdict, judge

__all__ = [
    "SUPPORTS_AUTOMATION",
    "EntryKind",
    "EvidenceLevel",
    "KnowledgeEntry",
    "KnowledgeId",
    "Verdict",
    "judge",
]
