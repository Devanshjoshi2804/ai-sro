from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import TenantId


class EvidenceLevel(StrEnum):
    ASSERTED = "asserted"

    OBSERVED = "observed"

    REPRODUCED = "reproduced"

    ROUND_TRIP = "round_trip"

    @property
    def rank(self) -> int:
        return _RANK[self]

    def outranks(self, other: EvidenceLevel) -> bool:
        return self.rank > other.rank


_RANK = {
    EvidenceLevel.ASSERTED: 0,
    EvidenceLevel.OBSERVED: 1,
    EvidenceLevel.REPRODUCED: 2,
    EvidenceLevel.ROUND_TRIP: 3,
}

SUPPORTS_AUTOMATION = EvidenceLevel.REPRODUCED


class EntryKind(StrEnum):
    SCREEN = "screen"
    ENDPOINT = "endpoint"
    FIELD = "field"
    FORM = "form"
    FLOW = "flow"
    STATUS = "status"
    QUIRK = "quirk"
    QUESTION = "question"


class KnowledgeId(str):
    __slots__ = ()


@dataclass(eq=False)
class KnowledgeEntry:
    id: KnowledgeId
    tenant_id: TenantId
    system: str
    kind: EntryKind
    key: str
    title: str
    body: dict[str, object]
    source: str

    evidence: EvidenceLevel
    observed_at: datetime
    superseded_by: KnowledgeId | None = None
    embedding: tuple[float, ...] = field(default_factory=tuple, repr=False)

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.system.strip():
            raise InvariantViolation("a knowledge entry needs a system and a key")
        if self.observed_at.tzinfo is None:
            raise InvariantViolation("KnowledgeEntry.observed_at must be timezone-aware")

    @property
    def current(self) -> bool:
        return self.superseded_by is None

    def superseded(self, by: KnowledgeEntry) -> None:
        if by.id == self.id:
            raise InvariantViolation("an entry cannot supersede itself")
        self.superseded_by = by.id
