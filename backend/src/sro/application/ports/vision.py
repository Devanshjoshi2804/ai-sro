"""The rung below UI replay: a model looking at the screen.

The model **proposes one gesture**. It never touches the browser, never chooses
when to stop, and never learns what a run is for beyond the step it was asked
about. Everything it returns is executed by the same driver that executes a
taught step, so actionability checks and trusted events still apply, and the
same recording of what happened is produced either way.

One gesture at a time on purpose. A driver handed a whole goal would decide for
itself when it was finished, and "the model said it was done" is not a
post-condition anybody can audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.domain.recording.events import ActionKind


@dataclass(frozen=True, slots=True)
class Screen:
    """What the model is shown. Redacted before it leaves the deployment."""

    image: bytes
    mime_type: str
    width: int
    height: int

    text_digest: str = ""
    """The visible text and control names, when the page yields them. Cheaper
    and more exact than pixels, and the thing to prefer when both exist."""


@dataclass(frozen=True, slots=True)
class ProposedGesture:
    action: ActionKind
    x: int | None = None
    y: int | None = None
    """Screen coordinates in the screenshot's own pixel space. The adapter
    converts whatever the model returns into these, because a normalised
    coordinate silently means a different pixel on a different viewport."""

    value: str | None = None
    reasoning: str = ""

    done: bool = False
    """The model believes the step is already satisfied. Recorded as a claim,
    never as a verification: what proves a step is the assertion extracted from
    the demonstration."""

    refusal: str | None = None
    """The model declined. A refusal is an outcome with a reason, not an error."""


class VisionDriver(Protocol):
    async def propose(
        self,
        *,
        goal: str,
        screen: Screen,
        allowed: tuple[ActionKind, ...],
        history: tuple[str, ...] = (),
    ) -> ProposedGesture:
        """One gesture towards ``goal``, given what is on screen now."""
        ...


class VisionUnavailable(Exception):
    """No vision backend, or egress is switched off for this deployment.

    Not a ``DomainError``: the skill and the screen were both fine. Distinct
    from a refusal, which means the model looked and declined.
    """
