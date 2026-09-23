from __future__ import annotations

from dataclasses import dataclass

from sro.domain.recording.events import ActionFrame
from sro.domain.recording.narration import NarrationSegment

_BRANCH_MARKERS = (
    "if ",
    "if the",
    "unless",
    "otherwise",
    "in case",
    "when it does not",
    "when it doesn't",
    "what i would do",
    "sometimes",
)

_HUMAN_MARKERS = (
    "supervisor",
    "check with",
    "ask ",
    "approval",
    "approve",
    "sign off",
    "manager",
)


@dataclass(frozen=True, slots=True)
class StepNarration:
    text: str
    branch_hint: str | None = None

    requires_human: bool = False


def align(
    frames: tuple[ActionFrame, ...], segments: tuple[NarrationSegment, ...]
) -> dict[int, StepNarration]:
    if not segments:
        return {}

    placed: dict[int, StepNarration] = {}
    for position, frame in enumerate(frames):
        end = frames[position + 1].occurred_at if position + 1 < len(frames) else None
        said = [segment.text for segment in segments if segment.overlaps(frame.occurred_at, end)]
        if not said:
            continue
        text = " ".join(said)
        placed[frame.index] = StepNarration(
            text=text,
            branch_hint=_branch_hint(said),
            requires_human=_mentions(text, _HUMAN_MARKERS),
        )
    return placed


def _branch_hint(said: list[str]) -> str | None:
    for sentence in (part.strip() for text in said for part in text.split(".")):
        if sentence and _mentions(sentence, _BRANCH_MARKERS):
            return sentence
    return None


def _mentions(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)
