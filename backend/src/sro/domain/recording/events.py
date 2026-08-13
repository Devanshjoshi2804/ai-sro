"""One human action and everything that followed. See docs/06-glossary.md#action-frame."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum

from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.network import CapturedRequest, InitiatorKind
from sro.domain.recording.state import BrowserState, ConsoleLevel, ConsoleMessage, PageEvent
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
    """``ctrl``, ``shift``, ``alt``, ``meta`` -- a shift-click is a different action."""

    secret: bool = False
    """The value was typed into a credential field.

    The one thing capture does not keep. Everything else is evidence of what
    happened; a password is an access token to the customer's system, and
    storing it would turn the evidence plane into a credential store. What is
    recorded is that a credential was entered, and where -- enough to replay the
    step from the vault, and useless to anyone who reads the recording.
    """

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
    """A step of a demonstration, with its complete observable context."""

    index: int
    occurred_at: datetime
    action: InputAction

    ax_graph: AxGraph | None = None
    """The page as the human saw it when they acted."""

    requests: tuple[CapturedRequest, ...] = field(default_factory=tuple)
    console: tuple[ConsoleMessage, ...] = ()
    page_events: tuple[PageEvent, ...] = ()
    state_before: BrowserState | None = None
    state_after: BrowserState | None = None

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
        """A copy carrying evidence that arrived after this frame was stored.

        Capture is drained on an interval, so a response that finishes just
        after a drain belongs to an action already written down. Without this
        the request is discarded and the step loses the very call the skill
        would replay.
        """
        return replace(
            self,
            requests=self.requests + requests,
            console=self.console + console,
            page_events=self.page_events + page_events,
        )

    @property
    def primary_request(self) -> CapturedRequest | None:
        """The call this frame is about, out of the analytics and prefetch noise.

        Preference order: a successful mutation whose initiator is a script (the
        click handler), then any successful mutation, then any success, then the
        first call at all. Script-initiated is the strongest signal available --
        it is the one the human's click actually caused.
        """
        if not self.requests:
            return None
        ordered = sorted(self.requests, key=lambda r: r.started_at)

        def rank(request: CapturedRequest) -> int:
            initiator = request.initiator
            script = initiator is not None and initiator.kind is InitiatorKind.SCRIPT
            if request.succeeded and request.is_mutation and script:
                return 0
            if request.succeeded and request.is_mutation:
                return 1
            if request.succeeded:
                return 2
            return 3

        return min(ordered, key=rank)

    @property
    def api_requests(self) -> tuple[CapturedRequest, ...]:
        """Calls worth cataloguing. Excludes assets, keeps everything else."""
        return tuple(
            request
            for request in self.requests
            if request.resource_type.lower() in {"xhr", "fetch", "websocket", "document"}
        )

    @property
    def errors(self) -> tuple[str, ...]:
        """Failure signals in this frame -- the 'why' behind a branch."""
        return tuple(
            [message.text for message in self.console if message.level is ConsoleLevel.ERROR]
            + [
                f"{r.method} {r.url} -> {r.status}"
                for r in self.requests
                if r.status is not None and r.status >= 400
            ]
            + [r.failure_reason for r in self.requests if r.failure_reason]
        )
