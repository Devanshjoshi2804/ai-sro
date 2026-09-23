from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum

from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.network import CapturedRequest, primary_of
from sro.domain.recording.state import ConsoleLevel, ConsoleMessage, PageEvent
from sro.domain.shared.errors import InvariantViolation

_ACTIONS_NEEDING_TARGET = frozenset({"click", "type", "select", "upload"})
_ACTIONS_NEEDING_VALUE = frozenset({"navigate", "type", "select", "press"})


class ActionKind(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    PRESS = "press"
    UPLOAD = "upload"
    SCROLL = "scroll"
    HOVER = "hover"


@dataclass(frozen=True, slots=True)
class InputAction:
    kind: ActionKind
    target: ElementFingerprint | None = None
    value: str | None = None
    modifiers: frozenset[str] = frozenset()

    secret: bool = False

    def __post_init__(self) -> None:
        if self.kind in _ACTIONS_NEEDING_TARGET and self.target is None:
            raise InvariantViolation(f"{self.kind} action requires a target element")
        if self.kind in _ACTIONS_NEEDING_VALUE and self.value is None and not self.secret:
            raise InvariantViolation(f"{self.kind} action requires a value")
        if self.secret and self.value is not None:
            raise InvariantViolation(
                "a secret input must not carry its value; capture redacts credentials "
                "at the point of observation, not later"
            )


@dataclass(frozen=True)
class ActionFrame:
    index: int
    occurred_at: datetime
    action: InputAction

    page_url: str | None = None

    ax_graph: AxGraph | None = None

    requests: tuple[CapturedRequest, ...] = field(default_factory=tuple)
    console: tuple[ConsoleMessage, ...] = ()
    page_events: tuple[PageEvent, ...] = ()

    def __post_init__(self) -> None:
        if self.index < 0:
            raise InvariantViolation("ActionFrame.index must be non-negative")
        if self.occurred_at.tzinfo is None:
            raise InvariantViolation("ActionFrame.occurred_at must be timezone-aware")

    def absorbing(
        self,
        *,
        requests: tuple[CapturedRequest, ...] = (),
        console: tuple[ConsoleMessage, ...] = (),
        page_events: tuple[PageEvent, ...] = (),
    ) -> ActionFrame:
        return replace(
            self,
            requests=self.requests + requests,
            console=self.console + console,
            page_events=self.page_events + page_events,
        )

    @property
    def primary_request(self) -> CapturedRequest | None:
        return primary_of(self.requests)

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(
            [message.text for message in self.console if message.level is ConsoleLevel.ERROR]
            + [
                f"{r.method} {r.url} -> {r.status}"
                for r in self.requests
                if r.status is not None and r.status >= 400
            ]
            + [r.failure_reason for r in self.requests if r.failure_reason]
        )
