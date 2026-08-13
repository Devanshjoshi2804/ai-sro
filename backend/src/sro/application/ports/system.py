"""Ambient effects: time and id generation."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import RecordingId, SkillId


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time. Must be timezone-aware; entities reject naive datetimes."""
        ...


class IdFactory(Protocol):
    def new_recording_id(self) -> RecordingId: ...

    def new_skill_id(self) -> SkillId: ...

    def new_run_id(self) -> RunId: ...
