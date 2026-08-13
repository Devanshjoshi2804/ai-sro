"""Recording aggregate. See docs/06-glossary.md#recording."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sro.domain.recording.artifact import ArtifactKind, MediaArtifact
from sro.domain.recording.events import ActionFrame
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import (
    BrowserSessionId,
    PrincipalId,
    RecordingId,
    TenantId,
)
from sro.domain.shared.objective import ObjectiveKey


class RecordingStatus(StrEnum):
    CAPTURING = "capturing"
    SEALED = "sealed"
    ABANDONED = "abandoned"


@dataclass(eq=False)
class Recording:
    """One demonstration. Mutable while capturing, immutable once sealed.

    Skill provenance cites recordings, so a sealed recording must never change --
    every state transition goes through a method, never a direct assignment.
    """

    id: RecordingId
    tenant_id: TenantId
    objective_key: ObjectiveKey
    demonstrator: PrincipalId
    started_at: datetime
    browser_session_id: BrowserSessionId | None = None
    label: str | None = None
    status: RecordingStatus = RecordingStatus.CAPTURING
    ended_at: datetime | None = None
    abandon_reason: str | None = None

    _frames: list[ActionFrame] = field(default_factory=list, repr=False)
    _artifacts: list[MediaArtifact] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None:
            raise InvariantViolation("Recording.started_at must be timezone-aware")

    @property
    def frames(self) -> tuple[ActionFrame, ...]:
        return tuple(self._frames)

    @property
    def artifacts(self) -> tuple[MediaArtifact, ...]:
        return tuple(self._artifacts)

    @property
    def is_open(self) -> bool:
        return self.status is RecordingStatus.CAPTURING

    @property
    def has_narration(self) -> bool:
        return self.artifact(ArtifactKind.AUDIO) is not None

    def artifact(self, kind: ArtifactKind) -> MediaArtifact | None:
        """Most recent artifact of a kind. Re-uploads supersede rather than fail."""
        matches = [a for a in self._artifacts if a.kind is kind]
        return matches[-1] if matches else None

    def artifacts_of(self, kind: ArtifactKind) -> tuple[MediaArtifact, ...]:
        """All artifacts of a kind. Screenshots and payload blobs are many-per-recording."""
        return tuple(a for a in self._artifacts if a.kind is kind)

    def screenshot_for(self, frame_index: int) -> MediaArtifact | None:
        matches = [
            a
            for a in self._artifacts
            if a.kind is ArtifactKind.SCREENSHOT and a.frame_index == frame_index
        ]
        return matches[-1] if matches else None

    def attach_browser_session(self, session_id: BrowserSessionId) -> None:
        self._require_open("attach a browser session")
        if self.browser_session_id is not None:
            raise InvariantViolation("Recording already has a browser session")
        self.browser_session_id = session_id

    def append_frame(self, frame: ActionFrame) -> ActionFrame:
        """Append with an aggregate-assigned index.

        The caller's index is overwritten: the two-run diff aligns positionally,
        so a gap from a retrying capture adapter would mis-pair steps silently.
        """
        self._require_open("append a frame")
        placed = (
            frame
            if frame.index == len(self._frames)
            else ActionFrame(
                index=len(self._frames),
                occurred_at=frame.occurred_at,
                action=frame.action,
                ax_graph=frame.ax_graph,
                requests=frame.requests,
                console=frame.console,
                page_events=frame.page_events,
                state_before=frame.state_before,
                state_after=frame.state_after,
            )
        )
        self._frames.append(placed)
        return placed

    def attach_artifact(self, artifact: MediaArtifact) -> None:
        self._require_open("attach an artifact")
        self._artifacts.append(artifact)

    def seal(self, at: datetime) -> None:
        self._require_open("seal")
        if not self._frames:
            raise InvariantViolation("cannot seal a recording with no frames; abandon it instead")
        self._require_after_start(at)
        self.status = RecordingStatus.SEALED
        self.ended_at = at

    def abandon(self, at: datetime, reason: str) -> None:
        self._require_open("abandon")
        self._require_after_start(at)
        self.status = RecordingStatus.ABANDONED
        self.ended_at = at
        self.abandon_reason = reason

    def _require_open(self, what: str) -> None:
        if not self.is_open:
            raise InvariantViolation(f"cannot {what}: recording is {self.status}")

    def _require_after_start(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise InvariantViolation("timestamps must be timezone-aware")
        if at < self.started_at:
            raise InvariantViolation("recording cannot end before it started")
