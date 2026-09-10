"""Driving the interface, for when replaying the call is not enough.

The port is deliberately about one gesture. A driver that took a whole plan
would decide for itself what to do when a control could not be found, and that
decision -- retry, escalate, stop -- belongs where it can be recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.application.ports.vision import Screen
from sro.domain.recording.events import ActionKind
from sro.domain.skill.locator import LocatorStrategy


@dataclass(frozen=True, slots=True)
class ResolvedLocator:
    """A locator with its parameters filled in, ready to try."""

    strategy: LocatorStrategy
    query: str
    within: str | None = None
    visible_only: bool = True


@dataclass(frozen=True, slots=True)
class UiOutcome:
    performed: bool
    matched_by: LocatorStrategy | None = None
    """Which locator worked. Recorded because a step that only ever matches on
    the last fallback is a step about to break."""

    candidates: int = 0
    """How many controls the winning locator matched. More than one is a
    warning: the driver acted on the first visible match."""

    detail: str | None = None


class UiDriver(Protocol):
    async def perform(
        self,
        *,
        action: ActionKind,
        locators: tuple[ResolvedLocator, ...],
        value: str | None = None,
    ) -> UiOutcome:
        """Try each locator in order and act on the first that resolves."""
        ...

    async def current_url(self) -> str | None:
        """Where the driven browser is, for the run's record."""
        ...

    async def capture(self) -> Screen:
        """What is on screen, for a rung that has to look at it."""
        ...

    def for_session(self, debugger_url: str) -> UiDriver:
        """The same driver, bound to a particular browser.

        Anything that opens its own browser has to drive that one: a driver
        pointed at the deployment's default will navigate one Chrome and look
        at another, which is indistinguishable from a model that cannot see."""
        ...

    async def perform_at(
        self, *, action: ActionKind, x: int, y: int, value: str | None = None
    ) -> UiOutcome:
        """Act at a point, for a gesture that came from pixels rather than a
        locator. Kept apart from ``perform`` so a coordinate can never be
        mistaken for a control the demonstration actually identified."""
        ...


class UiUnavailable(Exception):
    """No browser to drive. Not a ``DomainError``: the plan was fine.

    Distinct from "the control was not found", which is a fact about the page
    and means the skill has drifted from the system it was taught on.
    """

    code = "ui_unavailable"
