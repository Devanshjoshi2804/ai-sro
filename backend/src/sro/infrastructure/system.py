from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.thread import MessageId, ThreadId
from sro.domain.execution.run import RunId
from sro.domain.knowledge.entry import KnowledgeId
from sro.domain.shared.identifiers import (
    CandidateId,
    ConfirmationId,
    DeviceId,
    RecordingId,
    SkillId,
    TriggerId,
)


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidFactory(IdFactory):
    def new_recording_id(self) -> RecordingId:
        return RecordingId(f"rec_{uuid.uuid4().hex}")

    def new_skill_id(self) -> SkillId:
        return SkillId(f"skl_{uuid.uuid4().hex}")

    def new_run_id(self) -> RunId:
        return RunId(f"run_{uuid.uuid4().hex}")

    def new_knowledge_id(self) -> KnowledgeId:
        return KnowledgeId(f"kb_{uuid.uuid4().hex}")

    def new_thread_id(self) -> ThreadId:
        return ThreadId(f"thr_{uuid.uuid4().hex}")

    def new_message_id(self) -> MessageId:
        return MessageId(f"msg_{uuid.uuid4().hex}")

    def new_device_id(self) -> DeviceId:
        return DeviceId(f"dev_{uuid.uuid4().hex}")

    def new_trigger_id(self) -> TriggerId:
        return TriggerId(f"trg_{uuid.uuid4().hex}")

    def new_confirmation_id(self) -> ConfirmationId:
        return ConfirmationId(f"cnf_{uuid.uuid4().hex}")

    def new_candidate_id(self) -> CandidateId:
        return CandidateId(f"cnd_{uuid.uuid4().hex}")
