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
}

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


class GeminiVisionDriver:
    def __init__(self, api_key: str, model: str, *, client: Any | None = None) -> None:
        self._model = model
        if client is not None:
            self._client = client
            return
        from google import genai

        self._client = genai.Client(api_key=api_key)

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
    call = next(
        (
            part.function_call
            for candidate in (response.candidates or [])
            for part in (candidate.content.parts or [] if candidate.content else [])
            if part.function_call is not None
        ),
        None,
    )
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
    if name.lower() == "wait_5_seconds":
        return ProposedGesture(action=ActionKind.HOVER, wait=True, reasoning=said[:400])
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
