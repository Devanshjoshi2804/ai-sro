from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.application.ports.vision import Screen
from sro.domain.recording.events import ActionKind
from sro.domain.skill.locator import LocatorStrategy


@dataclass(frozen=True, slots=True)
class ResolvedLocator:
    strategy: LocatorStrategy
    query: str
    within: str | None = None
    visible_only: bool = True


@dataclass(frozen=True, slots=True)
class UiOutcome:
    performed: bool
    matched_by: LocatorStrategy | None = None

    candidates: int = 0

    detail: str | None = None


class UiDriver(Protocol):
    async def perform(
        self,
        *,
        action: ActionKind,
        locators: tuple[ResolvedLocator, ...],
        value: str | None = None,
    ) -> UiOutcome: ...

    async def current_url(self) -> str | None: ...

    async def capture(self) -> Screen: ...

    def for_session(self, debugger_url: str) -> UiDriver: ...

    async def perform_at(
        self, *, action: ActionKind, x: int, y: int, value: str | None = None
    ) -> UiOutcome: ...


class UiUnavailable(Exception):
    code = "ui_unavailable"
