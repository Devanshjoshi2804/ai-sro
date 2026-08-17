"""Reading parameter values out of a sentence, with Gemini.

Extraction only. The skill is already chosen and its parameters are already
declared; what comes back is checked against that list, so a value for a
parameter the skill does not have is dropped rather than sent.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sro.application.ports.intent import Extraction, Reading

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


_READING = """You read one sentence from a warehouse operator and say what it means.

You never decide what runs. What you return is checked against the tasks that
actually exist, and anything you name that does not exist is discarded, so
guessing buys nothing.

wants:      "ask" if they want to be told something, "act" if they want
            something done. "Show the list", "how many are there" and "which
            ones are used for parcel" are all asking, however they are phrased.
verb:       what they want done, in their words: list, create, adjust, release.
entity:     what they want it done to, singular: transport mode, wave, LPN.
continues:  true only when the sentence has no subject of its own and leans on
            the previous one -- "I want them in detail", "do it again". A
            sentence that names its own subject does not continue, however
            conversational it sounds.
values:     anything they supplied that looks like a value, by name if they
            gave one.
confidence: 0 to 1, how sure you are. Be honest; a low number costs a
            clarifying question and a wrong high one costs a wrong action.
"""


class GeminiIntentParser:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def available(self) -> bool:
        return True

    async def read(self, utterance: str, *, after: str = "") -> Reading:
        """What the sentence means. Never what to run."""
        from google.genai import types

        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "wants": {"type": "string", "enum": ["ask", "act"]},
                "verb": {"type": "string"},
                "entity": {"type": "string"},
                "continues": {"type": "boolean"},
                "values": {"type": "object"},
                "confidence": {"type": "number"},
            },
            "required": ["wants", "verb", "entity", "continues", "confidence"],
        }
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[
                _READING,
                f"The sentence before this one: {after}" if after else "",
                f"Sentence: {utterance}",
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=schema
            ),
        )
        try:
            answer = json.loads(response.text or "{}")
        except ValueError:
            logger.warning("the intent parser did not answer with a reading")
            return Reading()
        values = answer.get("values")
        return Reading(
            wants=str(answer.get("wants", "act")),
            verb=str(answer.get("verb", "")),
            entity=str(answer.get("entity", "")),
            continues=bool(answer.get("continues", False)),
            values={str(k): str(v) for k, v in values.items()} if isinstance(values, dict) else {},
            confidence=float(answer.get("confidence", 0.0)),
        )

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
