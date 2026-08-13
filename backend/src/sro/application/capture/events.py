"""Protocol-neutral events the capture adapter emits."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.events import InputAction
from sro.domain.recording.network import CapturedRequest


@dataclass(frozen=True, slots=True)
class InputEvent:
    at: datetime
    action: InputAction


@dataclass(frozen=True, slots=True)
class RequestEvent:
    request: CapturedRequest

    @property
    def at(self) -> datetime:
        return self.request.started_at


@dataclass(frozen=True, slots=True)
class SnapshotEvent:
    snapshot: AxGraph

    @property
    def at(self) -> datetime:
        return self.snapshot.taken_at


CaptureEvent = InputEvent | RequestEvent | SnapshotEvent
