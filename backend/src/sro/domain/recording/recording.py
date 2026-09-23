from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sro.domain.recording.artifact import ArtifactKind, MediaArtifact
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.narration import NarrationSegment
from sro.domain.recording.network import CapturedRequest
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import (
    BrowserSessionId,
    DeviceId,
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
    id: RecordingId
    tenant_id: TenantId
    demonstrator: PrincipalId
    started_at: datetime

    objective_key: ObjectiveKey | None = None

    browser_session_id: BrowserSessionId | None = None
    device_id: DeviceId | None = None
    label: str | None = None
    status: RecordingStatus = RecordingStatus.CAPTURING
    ended_at: datetime | None = None
    abandon_reason: str | None = None

    _frames: list[ActionFrame] = field(default_factory=list, repr=False)
    _artifacts: list[MediaArtifact] = field(default_factory=list, repr=False)
    _narration: list[NarrationSegment] = field(default_factory=list, repr=False)

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
    def narration(self) -> tuple[NarrationSegment, ...]:
        return tuple(self._narration)

    @property
    def is_open(self) -> bool:
        return self.status is RecordingStatus.CAPTURING

    @property
    def has_narration(self) -> bool:
        return self.artifact(ArtifactKind.AUDIO) is not None

    def artifact(self, kind: ArtifactKind) -> MediaArtifact | None:
        matches = [a for a in self._artifacts if a.kind is kind]
        return matches[-1] if matches else None

    def attach_browser_session(self, session_id: BrowserSessionId) -> None:
        self._require_open("attach a browser session")
        if self.browser_session_id is not None:
            raise InvariantViolation("Recording already has a browser session")
        self.browser_session_id = session_id

    def append_frame(self, frame: ActionFrame) -> ActionFrame:
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
            )
        )
        self._frames.append(placed)
        return placed

    def absorb_late_evidence(self, *, requests: tuple[CapturedRequest, ...]) -> bool:
        self._require_open("absorb late evidence")
        if not self._frames or not requests:
            return False
        self._frames[-1] = self._frames[-1].absorbing(requests=requests)
        return True

    def attach_artifact(self, artifact: MediaArtifact) -> None:
        self._require_open("attach an artifact")
        self._artifacts.append(artifact)

    def attach_narration(self, segments: tuple[NarrationSegment, ...]) -> None:
        self._require_open("attach narration")
        self._narration = sorted(segments, key=lambda segment: segment.starts_at)

    def name_objective(self, key: ObjectiveKey) -> None:
        self._require_open("name the objective")
        if self.objective_key is not None and self.objective_key != key:
            raise InvariantViolation("a recording's objective cannot be renamed once it is set")
        self.objective_key = key

    def seal(self, at: datetime) -> None:
        self._require_open("seal")
        if not self._frames:
            raise InvariantViolation("cannot seal a recording with no frames; abandon it instead")
        if self.objective_key is None:
            raise InvariantViolation(
                "cannot seal a recording that has no objective; "
                "nothing it did says what task it was"
            )
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
