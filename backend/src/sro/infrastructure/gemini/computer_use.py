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
    "wait_5_seconds": ActionKind.HOVER,
}
"""Its predefined functions to ours. Absence is a refusal, never a nearest
match: a `drag_and_drop` turned into a click is a different gesture performed
confidently. Navigation is absent on purpose and excluded at the tool as well."""

_INSTRUCTIONS = (
    "You are helping finish one step of a warehouse task that was demonstrated "
    "by an operator and can no longer be replayed as recorded. Propose exactly "
    "one gesture towards the step's goal, using what is visible now. "
    "Do not attempt the whole task. Do not enter credentials. If the step "
    "already appears done, say so instead of acting. If you cannot see how to "
    "proceed, refuse and say why."
)

_EXCLUDED = [
    "open_web_browser",
    "navigate",
    "go_back",
    "go_forward",
    "search",
    "drag_and_drop",
]
"""Predefined functions this rung must not have.

The model requires its own tool -- a plain JSON schema is refused with 400 -- so
the way to bound it is to remove the functions rather than to ask it politely.
Navigation is excluded for the reason the step allow-list exists: a gesture
demonstrated on one screen must not become "go somewhere else and try there".
"""


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
                f"Visible controls (label: x,y, already 0-1000):\n{screen.text_digest}"
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
                tools=[
                    types.Tool(
                        computer_use=types.ComputerUse(
                            environment=types.Environment.ENVIRONMENT_BROWSER,
                            excluded_predefined_functions=_EXCLUDED,
                        )
                    )
                ]
            ),
        )
        return _from_response(response, screen, allowed)


def _from_response(
    response: Any, screen: Screen, allowed: tuple[ActionKind, ...]
) -> ProposedGesture:
    """The model answers with a function call, or with prose meaning it did not act.

    Prose is treated as a refusal rather than parsed for intent: a sentence that
    is not a call is the model declining to name a gesture, and guessing one out
    of it is exactly the confident-wrong-action this rung is bounded against.
    """
    call = next(
        (
            part.function_call
            for candidate in (response.candidates or [])
            for part in (candidate.content.parts or [] if candidate.content else [])
            if part.function_call is not None
        ),
        None,
    )
    # Assembled from the text parts rather than `response.text`, which warns
    # (correctly) that it is dropping the function call we came for.
    said = " ".join(
        part.text.strip()
        for candidate in (response.candidates or [])
        for part in (candidate.content.parts or [] if candidate.content else [])
        if part.text
    ).strip()
    if call is None:
        return ProposedGesture(
            action=ActionKind.HOVER,
            refusal=said[:400] or "the model named no gesture",
        )
    return _gesture(call.name or "", dict(call.args or {}), said, screen, allowed)


def _gesture(
    name: str,
    args: dict[str, Any],
    said: str,
    screen: Screen,
    allowed: tuple[ActionKind, ...],
) -> ProposedGesture:
    """A named call becomes a gesture, or a refusal. Never an approximation."""
    kind = _ACTIONS.get(name.lower())
    if kind is None:
        return ProposedGesture(
            action=ActionKind.HOVER,
            refusal=f"proposed {name!r}, which this driver cannot perform",
        )
    if kind not in allowed:
        return ProposedGesture(action=kind, refusal=f"{kind} is not allowed for this step")

    value = args.get("text", args.get("value", args.get("keys")))
    return ProposedGesture(
        action=kind,
        x=_pixels(args.get("x"), screen.width),
        y=_pixels(args.get("y"), screen.height),
        value=str(value) if value is not None else None,
        reasoning=said[:400],
    )


def _pixels(value: object, extent: int) -> int | None:
    if not isinstance(value, int | float):
        return None
    return round(float(value) / _NORMALISED * extent)
