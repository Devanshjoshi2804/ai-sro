"""Browser state and out-of-band events. See docs/11-capture-completeness.md."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from sro.domain.recording.network import Cookie, StackFrame
from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True)
class BrowserState:
    """Cookies and web storage at one instant, per origin.

    Snapshotted at each action so a state change is attributable to the action
    that caused it -- which is how a login step or a facility switch becomes
    visible rather than implicit.
    """

    taken_at: datetime
    origin: str
    cookies: tuple[Cookie, ...] = ()
    local_storage: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    session_storage: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if self.taken_at.tzinfo is None:
            raise InvariantViolation("BrowserState.taken_at must be timezone-aware")
        object.__setattr__(self, "local_storage", MappingProxyType(dict(self.local_storage)))
        object.__setattr__(self, "session_storage", MappingProxyType(dict(self.session_storage)))


class ConsoleLevel(StrEnum):
    LOG = "log"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


@dataclass(frozen=True, slots=True)
class ConsoleMessage:
    """A console entry with its stack.

    Kept because a WMS that logs a validation failure is stating why a branch was
    taken -- the cheapest 'why' signal in the whole capture.
    """

    at: datetime
    level: ConsoleLevel
    text: str
    source: str | None = None
    url: str | None = None
    stack: tuple[StackFrame, ...] = ()

    def __post_init__(self) -> None:
        if self.at.tzinfo is None:
            raise InvariantViolation("ConsoleMessage.at must be timezone-aware")


class PageEventKind(StrEnum):
    NAVIGATED = "navigated"
    LOADED = "loaded"
    DIALOG_OPENED = "dialog_opened"
    DIALOG_HANDLED = "dialog_handled"
    DOWNLOAD_STARTED = "download_started"
    FRAME_ATTACHED = "frame_attached"
    FRAME_DETACHED = "frame_detached"
    POPUP_OPENED = "popup_opened"


@dataclass(frozen=True, slots=True)
class PageEvent:
    at: datetime
    kind: PageEventKind
    url: str | None = None
    detail: str | None = None
    """Dialog text, download filename, frame id -- whatever the kind carries."""

    def __post_init__(self) -> None:
        if self.at.tzinfo is None:
            raise InvariantViolation("PageEvent.at must be timezone-aware")
