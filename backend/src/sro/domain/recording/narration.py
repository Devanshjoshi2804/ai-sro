from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class NarrationSegment:
    starts_at: datetime
    ends_at: datetime
    text: str

    def __post_init__(self) -> None:
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise InvariantViolation("narration timestamps must be timezone-aware")
        if self.ends_at < self.starts_at:
            raise InvariantViolation("a narration segment cannot end before it starts")
        if not self.text.strip():
            raise InvariantViolation("a narration segment with no words is not evidence")

    def overlaps(self, start: datetime, end: datetime | None) -> bool:
        if end is None:
            return self.ends_at > start
        return self.starts_at < end and self.ends_at > start
