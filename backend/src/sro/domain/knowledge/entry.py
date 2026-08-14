"""What is known about a system, and how well it is known.

Every entry is a claim with the evidence behind it named. That is the rule the
knowledge base was rebuilt under after an audit found endpoints marked
"verified" whose only proof was a 404 on a route that never existed -- see
knowledge-base/SCHEMA.md.

Nothing here is ever overwritten. A verified run that contradicts a scraped
claim supersedes it and both rows stay, because "we used to believe this" is the
only way to explain an incident afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import TenantId


class EvidenceLevel(StrEnum):
    ASSERTED = "asserted"
    """Written down by a human or a model. Not evidence."""

    OBSERVED = "observed"
    """Seen once, and the exchange was stored."""

    REPRODUCED = "reproduced"
    """Re-run deliberately and matched what was stored before."""

    ROUND_TRIP = "round_trip"
    """Created, read back, changed and removed, all recorded."""

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
"""Below this, a claim may inform a human and may not drive a call."""


class EntryKind(StrEnum):
    SCREEN = "screen"
    ENDPOINT = "endpoint"
    FIELD = "field"
    FORM = "form"
    FLOW = "flow"
    STATUS = "status"
    QUIRK = "quirk"


class KnowledgeId(str):
    __slots__ = ()


@dataclass(eq=False)
class KnowledgeEntry:
    """One claim about one system.

    ``key`` is the claim's identity within its kind -- an endpoint's method and
    path, a screen's route, a field's payload name. Two entries with the same
    key are the same claim believed twice, which is what supersession is for.
    """

    id: KnowledgeId
    tenant_id: TenantId
    system: str
    kind: EntryKind
    key: str
    title: str
    body: dict[str, object]
    source: str
    """Where this came from: a knowledge-base file, or the run that proved it."""

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

    @property
    def supports_automation(self) -> bool:
        """Whether this claim may be acted on rather than merely shown."""
        return self.evidence.rank >= SUPPORTS_AUTOMATION.rank

    def superseded(self, by: KnowledgeEntry) -> None:
        """Point forward at what replaced this. The old row stays."""
        if by.id == self.id:
            raise InvariantViolation("an entry cannot supersede itself")
        self.superseded_by = by.id
