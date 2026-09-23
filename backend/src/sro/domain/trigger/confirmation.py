from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType

from sro.domain.execution.run import RunId
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import (
    ConfirmationId,
    PrincipalId,
    SkillId,
    TenantId,
    TriggerId,
)

ANSWER_WITHIN = timedelta(hours=24)


class Answer(StrEnum):
    WAITING = "waiting"
    APPROVED = "approved"
    DECLINED = "declined"

    EXPIRED = "expired"


@dataclass(eq=False)
class Confirmation:
    id: ConfirmationId
    tenant_id: TenantId
    trigger_id: TriggerId
    asked_at: datetime
    expires_at: datetime

    skill_id: SkillId | None = None
    workflow_id: str | None = None

    values: Mapping[str, str] = field(default_factory=dict)

    because: str = ""

    answer: Answer = Answer.WAITING
    answered_at: datetime | None = None
    answered_by: PrincipalId | None = None
    run_id: RunId | None = None
    note: str = ""

    def __post_init__(self) -> None:
        named = [name for name in (self.skill_id, self.workflow_id) if name]
        if len(named) != 1:
            raise InvariantViolation(
                "a confirmation asks about one thing: name a skill or a job, not "
                + ("both" if named else "neither")
            )
        for name, at in (("asked_at", self.asked_at), ("expires_at", self.expires_at)):
            if at.tzinfo is None:
                raise InvariantViolation(f"Confirmation.{name} must be timezone-aware")
        if self.expires_at <= self.asked_at:
            raise InvariantViolation("a confirmation that has already expired asks nothing")
        self.values = MappingProxyType(dict(self.values))

    @property
    def runs(self) -> str:
        return (self.skill_id.value if self.skill_id else None) or str(self.workflow_id)

    def waiting_at(self, now: datetime) -> bool:
        return self.answer is Answer.WAITING and now < self.expires_at

    def approve(self, by: PrincipalId, at: datetime, run_id: RunId) -> None:
        self._require_waiting(at)
        self.answer = Answer.APPROVED
        self.answered_by = by
        self.answered_at = at
        self.run_id = run_id

    def decline(self, by: PrincipalId, at: datetime, note: str = "") -> None:
        self._require_waiting(at)
        self.answer = Answer.DECLINED
        self.answered_by = by
        self.answered_at = at
        self.note = note

    def expire(self, at: datetime) -> None:
        if self.answer is not Answer.WAITING:
            return
        self.answer = Answer.EXPIRED
        self.answered_at = at

    def _require_waiting(self, at: datetime) -> None:
        if self.answer is not Answer.WAITING:
            raise InvariantViolation(f"this was already {self.answer}")
        if at >= self.expires_at:
            raise InvariantViolation(
                "this expired without an answer; nothing was run and nothing can be now"
            )
