"""Browser state and out-of-band events. See docs/11-capture-completeness.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sro.domain.recording.network import StackFrame
from sro.domain.shared.errors import InvariantViolation


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
