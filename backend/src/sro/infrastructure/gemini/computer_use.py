"""Gemini's computer-use model, asked for exactly one gesture.

The model returns actions from its own fixed set. They are mapped onto the
``ActionKind`` the rest of the system already knows, and anything that does not
map is refused rather than approximated -- a `drag` translated into a click is a
different gesture performed confidently.

Coordinates come back normalised to 0-1000 and are converted here into the
screenshot's own pixels, because a normalised coordinate silently means a
different point on a different viewport.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sro.application.ports.vision import ProposedGesture, Screen
from sro.domain.recording.events import ActionKind

logger = logging.getLogger(__name__)

_NORMALISED = 1000

_ACTIONS: dict[str, ActionKind] = {
    "click_at": ActionKind.CLICK,
    "click": ActionKind.CLICK,
    "type_text_at": ActionKind.TYPE,
    "type_text": ActionKind.TYPE,
    "key_combination": ActionKind.PRESS,
    "press": ActionKind.PRESS,
    "scroll_document": ActionKind.SCROLL,
    "scroll_at": ActionKind.SCROLL,
    "hover_at": ActionKind.HOVER,
    "navigate": ActionKind.NAVIGATE,
}
"""Its vocabulary to ours. Absence is a refusal, never a nearest match."""

_INSTRUCTIONS = (
    "You are helping finish one step of a warehouse task that was demonstrated "
    "by an operator and can no longer be replayed as recorded. Propose exactly "
    "one gesture towards the step's goal, using what is visible now. "
    "Do not attempt the whole task. Do not enter credentials. If the step "
    "already appears done, say so instead of acting. If you cannot see how to "
    "proceed, refuse and say why."
)

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "x": {"type": "integer"},
        "y": {"type": "integer"},
        "value": {"type": "string"},
        "reasoning": {"type": "string"},
        "done": {"type": "boolean"},
        "refusal": {"type": "string"},
    },
    "required": ["action", "reasoning"],
}


class GeminiVisionDriver:
    """The SDK is imported inside the adapter: a deployment that sends nothing
    to a hosted model should not load one in order to boot."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def destination(self) -> str:
        return f"gemini:{self._model}"

    async def propose(
        self,
        *,
        goal: str,
        screen: Screen,
        allowed: tuple[ActionKind, ...],
        history: tuple[str, ...] = (),
    ) -> ProposedGesture:
        from google.genai import types

        prompt = "\n\n".join(
            part
            for part in (
                _INSTRUCTIONS,
                f"Step goal: {goal}",
                f"Allowed actions: {', '.join(sorted({a.value for a in allowed}))}",
                "Already tried this step:\n" + "\n".join(history) if history else "",
                f"Visible controls (label: x,y):\n{screen.text_digest}"
                if screen.text_digest
                else "",
                "Answer with one gesture. Coordinates are 0-1000, left to right and top "
                "to bottom of the screenshot.",
            )
            if part
        )

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[
                prompt,
                types.Part.from_bytes(data=screen.image, mime_type=screen.mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=_SCHEMA
            ),
        )
        return _gesture(response.text, screen, allowed)


def _gesture(text: str | None, screen: Screen, allowed: tuple[ActionKind, ...]) -> ProposedGesture:
    """Model output is data crossing a trust boundary; a bad shape is a refusal."""
    try:
        answer = json.loads(text or "{}")
    except ValueError:
        return ProposedGesture(
            action=ActionKind.HOVER, refusal="the model did not answer with a gesture"
        )

    if refusal := answer.get("refusal"):
        return ProposedGesture(action=ActionKind.HOVER, refusal=str(refusal))

    if answer.get("done"):
        return ProposedGesture(
            action=ActionKind.HOVER, done=True, reasoning=str(answer.get("reasoning", ""))
        )

    kind = _ACTIONS.get(str(answer.get("action", "")).lower())
    if kind is None:
        return ProposedGesture(
            action=ActionKind.HOVER,
            refusal=f"proposed {answer.get('action')!r}, which this driver cannot perform",
        )
    if kind not in allowed:
        return ProposedGesture(
            action=kind,
            refusal=f"{kind} is not allowed for this step",
        )

    return ProposedGesture(
        action=kind,
        x=_pixels(answer.get("x"), screen.width),
        y=_pixels(answer.get("y"), screen.height),
        value=str(answer["value"]) if answer.get("value") is not None else None,
        reasoning=str(answer.get("reasoning", ""))[:400],
    )


def _pixels(value: object, extent: int) -> int | None:
    if not isinstance(value, int | float):
        return None
    return round(float(value) / _NORMALISED * extent)
