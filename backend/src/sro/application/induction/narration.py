"""Narration lined up against frames.

**Narration labels; evidence decides.** What the operator said becomes a note on
a step, a branch a reviewer is asked about, and a flag that a human belongs in
the loop. It never becomes a parameter, a step, or a request: those come from
the two-run diff, which is the whole reason this system does not guess.

The distinction is kept in the data too. A step's ``intent`` stays derived from
what was observed; the words go in ``narration``. One field holding either would
make a transcript indistinguishable from evidence at review time.
"""

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
"""Spoken conditionals. A branch is *proposed* from these, never taken: the
demonstration only ever walked one path, so the other one has no evidence."""

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
    """Something the operator said would happen differently. Surfaced for a
    reviewer to confirm; never an executable path."""

    requires_human: bool = False


def align(
    frames: tuple[ActionFrame, ...], segments: tuple[NarrationSegment, ...]
) -> dict[int, StepNarration]:
    """What was said during each frame's window.

    A frame's window runs from when it happened to when the next one did; the
    last frame's window stays open, because the operator's summing-up ("and that
    is the adjustment queued for approval") arrives after the final click and is
    the most useful sentence in the recording.
    """
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
    """The first sentence that describes a path this demonstration did not take."""
    for sentence in (part.strip() for text in said for part in text.split(".")):
        if sentence and _mentions(sentence, _BRANCH_MARKERS):
            return sentence
    return None


def _mentions(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)
