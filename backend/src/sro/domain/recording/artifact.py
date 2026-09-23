from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation


class ArtifactKind(StrEnum):
    RAW_EVENTS = "raw_events"

    VIDEO = "video"
    SCREENSHOT = "screenshot"

    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    PAYLOAD = "payload"


@dataclass(frozen=True, slots=True)
class MediaArtifact:
    kind: ArtifactKind
    uri: str
    content_type: str
    size_bytes: int
    created_at: datetime
    duration_ms: int | None = None

    frame_index: int | None = None

    label: str | None = None

    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise InvariantViolation("MediaArtifact.uri cannot be blank")
        if self.size_bytes < 0:
            raise InvariantViolation("MediaArtifact.size_bytes cannot be negative")
        if self.created_at.tzinfo is None:
            raise InvariantViolation("MediaArtifact.created_at must be timezone-aware")
        if self.frame_index is not None and self.frame_index < 0:
            raise InvariantViolation("MediaArtifact.frame_index must be non-negative")
