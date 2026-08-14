"""What the operator said while they worked, on the same clock as the frames."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class NarrationSegment:
    """One utterance, placed in absolute time.

    Absolute rather than an offset into the audio: a segment is only useful once
    it can be lined up against the action frames, and the audio's own clock
    starts whenever the microphone did.
    """

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
        """Whether this was said during a window, the last of which is open.

        Half-open at both ends: an utterance that finishes exactly as the next
        action begins belongs to the action it was describing, not to the one
        that had not happened yet. Closed-ended, every sentence spoken at a step
        boundary landed on two steps.
        """
        if end is None:
            return self.ends_at > start
        return self.starts_at < end and self.ends_at > start
