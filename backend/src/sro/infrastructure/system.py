"""Real time and real ids. The fakes in tests/unit/fakes.py are the other half."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sro.application.ports.system import Clock, IdFactory
from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import RecordingId, SkillId


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidFactory(IdFactory):
    """Prefixed so an id is readable in a log line without a lookup."""

    def new_recording_id(self) -> RecordingId:
        return RecordingId(f"rec_{uuid.uuid4().hex}")

    def new_skill_id(self) -> SkillId:
        return SkillId(f"skl_{uuid.uuid4().hex}")

    def new_run_id(self) -> RunId:
        return RunId(f"run_{uuid.uuid4().hex}")
