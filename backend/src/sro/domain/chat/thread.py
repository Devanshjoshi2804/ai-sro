"""A conversation about work, kept because the work is auditable.

A thread is not a transcript of a chatbot. It is the record of what was asked,
what the system decided that meant, and what was done about it — which is the
first thing anybody reads after an incident. So messages are append-only and
carry the decision that produced them, not just prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import Identifier, PrincipalId, TenantId


class ThreadId(Identifier): ...


class MessageId(Identifier): ...


class Speaker(StrEnum):
    OPERATOR = "operator"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    """Things that happened rather than things anybody said: a run finished, a
    skill was induced."""


@dataclass(frozen=True, slots=True)
class Message:
    id: MessageId
    speaker: Speaker
    text: str
    said_at: datetime

    decision: dict[str, object] = field(default_factory=dict)
    """What the system worked out, alongside what it said.

    Kept structured as well as in prose because "why did it do that" is
    answered by the resolution, not by the sentence that reported it.
    """

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

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None:
            raise InvariantViolation("Thread.opened_at must be timezone-aware")

    @property
    def messages(self) -> tuple[Message, ...]:
        return tuple(self._messages)

    @property
    def title(self) -> str:
        """What the operator asked for first. Threads are found by what they
        were about, and a title anybody typed separately is a title nobody
        typed."""
        first = next((m for m in self._messages if m.speaker is Speaker.OPERATOR), None)
        return (first.text[:80] if first else "New thread").strip()

    def say(self, message: Message) -> Message:
        """Append. Nothing in a thread is ever edited or removed."""
        self._messages.append(message)
        return message
