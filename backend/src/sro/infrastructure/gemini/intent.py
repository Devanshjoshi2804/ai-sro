"""Reading parameter values out of a sentence, with Gemini.

Extraction only. The skill is already chosen and its parameters are already
declared; what comes back is checked against that list, so a value for a
parameter the skill does not have is dropped rather than sent.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sro.application.ports.intent import Extraction

logger = logging.getLogger(__name__)

_INSTRUCTIONS = (
    "Read the operator's request and pull out the values for the named "
    "parameters. One set per thing they are asking to be done: 'update these "
    "six SKUs' is six sets.\n\n"
    "Copy values exactly as written. Do not convert units, pad identifiers, or "
    "tidy them up. If the request refers to something you were not given — a "
    "spreadsheet, 'this morning's count', 'the usual ones' — return no items and "
    "say what is missing in the note. Never invent a value to fill a set."
)


class GeminiIntentParser:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def available(self) -> bool:
        return True

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction:
        from google.genai import types

        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {name: {"type": "string"} for name in parameters},
                    },
                },
                "missing": {"type": "array", "items": {"type": "string"}},
                "note": {"type": "string"},
            },
            "required": ["items"],
        }

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[
                _INSTRUCTIONS,
                f"Parameters: {', '.join(parameters) or 'none'}",
                f"Context: {context}" if context else "",
                f"Request: {utterance}",
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=schema
            ),
        )
        return _parse(response.text, parameters)


def _parse(text: str | None, declared: tuple[str, ...]) -> Extraction:
    try:
        answer = json.loads(text or "{}")
    except ValueError:
        logger.warning("the intent parser did not answer with an extraction")
        return Extraction(note="the request could not be read")

    allowed = set(declared)
    items = tuple(
        {k: str(v) for k, v in item.items() if k in allowed and str(v).strip()}
        for item in answer.get("items", [])
        if isinstance(item, dict)
    )
    return Extraction(
        items=tuple(item for item in items if item),
        missing=tuple(str(m) for m in answer.get("missing", []) if str(m) in allowed),
        note=str(answer.get("note", "")),
    )
