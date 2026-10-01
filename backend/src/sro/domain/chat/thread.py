from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import Identifier, PrincipalId, TenantId


class ThreadId(Identifier): ...


K_ASKING = "thr_ask_"


def asking_about(tenant_id: TenantId, opened_by: PrincipalId, about: str) -> ThreadId:
    said = f"{tenant_id.value}\n{opened_by.value}\n{about}".encode()
    return ThreadId(K_ASKING + hashlib.sha256(said).hexdigest()[:32])


class MessageId(Identifier): ...


class Speaker(StrEnum):
    OPERATOR = "operator"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Said(StrEnum):
    OFFER = "offer"

    MAIL_MATCH = "mail_match"

    NOTE = "note"

    RUN = "run"

    RESULT = "result"

    QUESTION = "question"

    FAILURE = "failure"

    MAIL_LOOKED = "mail_looked"

    LOOKED = "looked"


@dataclass(frozen=True, slots=True)
class Message:
    id: MessageId
    speaker: Speaker
    text: str
    said_at: datetime

    decision: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.said_at.tzinfo is None:
            raise InvariantViolation("Message.said_at must be timezone-aware")
        if not self.text.strip() and not self.decision:
            raise InvariantViolation("a message with neither words nor a decision is nothing")


@dataclass(eq=False)
class Thread:
    id: ThreadId
    tenant_id: TenantId
    opened_by: PrincipalId
    opened_at: datetime
    _messages: list[Message] = field(default_factory=list, repr=False)
    _kept: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None:
            raise InvariantViolation("Thread.opened_at must be timezone-aware")

    @property
    def messages(self) -> tuple[Message, ...]:
        return tuple(self._messages)

    @property
    def title(self) -> str:
        first = next((m for m in self._messages if m.speaker is Speaker.OPERATOR), None)
        asked = (first.text[:60] if first else "New thread").strip()
        return f"{asked} · {done}" if (done := self._what_was_done()) else asked

    def _what_was_done(self) -> str:
        for message in reversed(self._messages):
            decision = message.decision or {}
            if decision.get("run_id"):
                matched = decision.get("matched_skill_name") or decision.get("matched_skill_id")
                return f"ran {matched}" if matched else "ran"
        return ""

    def say(self, message: Message) -> Message:
        self._messages.append(message)
        return message

    def unsaved(self) -> tuple[Message, ...]:
        return tuple(self._messages[self._kept :])

    def saved(self) -> None:
        self._kept = len(self._messages)
