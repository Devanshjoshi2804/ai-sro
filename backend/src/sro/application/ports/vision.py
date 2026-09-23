from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.domain.recording.events import ActionKind


@dataclass(frozen=True, slots=True)
class Screen:
    image: bytes
    mime_type: str
    width: int
    height: int

    text_digest: str = ""


@dataclass(frozen=True, slots=True)
class ProposedGesture:
    action: ActionKind
    x: int | None = None
    y: int | None = None

    value: str | None = None
    reasoning: str = ""

    done: bool = False

    refusal: str | None = None

    wait: bool = False


class VisionDriver(Protocol):
    async def propose(
        self,
        *,
        goal: str,
        screen: Screen,
        allowed: tuple[ActionKind, ...],
        history: tuple[str, ...] = (),
    ) -> ProposedGesture: ...


class VisionUnavailable(Exception):
    code = "vision_unavailable"
