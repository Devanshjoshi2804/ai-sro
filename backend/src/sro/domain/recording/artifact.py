"""Capture outputs stored as blobs rather than rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation


class ArtifactKind(StrEnum):
    RAW_EVENTS = "raw_events"
    """Unabridged CDP stream. Frames are re-derivable from this without re-recording."""

    VIDEO = "video"
    SCREENSHOT = "screenshot"
    """Still capture. One per action frame, plus any taken on demand."""

    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    PAYLOAD = "payload"
    """A request or response body too large to store inline."""


@dataclass(frozen=True, slots=True)
class MediaArtifact:
    kind: ArtifactKind
    uri: str
    content_type: str
    size_bytes: int
    created_at: datetime
    duration_ms: int | None = None

    frame_index: int | None = None
    """Set when the artifact belongs to one action frame -- a screenshot, or a
    payload blob referenced by a captured request."""

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
