"""Reading a demonstration with Gemini.

Structured output, so what comes back is checked against a shape before anything
uses it. What it is asked for is narrow on purpose: describe what happened and
name the values that look like inputs. It is never asked what the system *should*
do, or to invent a step nobody performed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sro.application.ports.interpretation import (
    CandidateParameter,
    Reading,
    StepReading,
)

logger = logging.getLogger(__name__)

_INSTRUCTIONS = (
    "You are reading one recorded demonstration of a warehouse task, performed by "
    "an operator in a warehouse management system. You are given every gesture, "
    "every HTTP call it caused, the responses, and anything the operator said.\n\n"
    "Describe what was done, step by step, in the words the system and the "
    "operator use. Then name the values that look like inputs to the task — the "
    "identifiers and quantities that would be different next time — and give the "
    "exact literal each one had in this run, copied character for character from "
    "the evidence.\n\n"
    "Rules: describe only what is in the evidence. Do not invent a step nobody "
    "performed. Do not name a parameter whose value you cannot find. A value that "
    "is the same on every run of this task — a site code, a warehouse id — is not "
    "a parameter. If part of the demonstration makes no sense to you, say so in "
    "the caveat rather than guessing."
)

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "when_to_use": {"type": "string"},
        "caveat": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "what": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["index", "what"],
            },
        },
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "description": {"type": "string"},
                    "step_index": {"type": "integer"},
                },
                "required": ["name", "value"],
            },
        },
    },
    "required": ["title", "summary", "steps"],
}


class GeminiInterpreter:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def available(self) -> bool:
        return True

    async def read(self, evidence: str) -> Reading:
        from google.genai import types

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[_INSTRUCTIONS, "EVIDENCE\n" + evidence],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=_SCHEMA
            ),
        )
        return _parse(response.text)


def _parse(text: str | None) -> Reading:
    """A bad shape is a reading with nothing in it, not an exception.

    The demonstration is still perfectly usable without a narrative: the calls
    are the skill, and the description is what makes it findable.
    """
    try:
        answer = json.loads(text or "{}")
    except ValueError:
        logger.warning("the interpreter did not answer with a reading")
        return Reading(caveat="the interpreter's answer could not be read")

    steps = tuple(
        StepReading(
            index=int(step["index"]),
            what=str(step.get("what", "")),
            why=str(step.get("why", "")),
        )
        for step in answer.get("steps", [])
        if isinstance(step, dict) and "index" in step
    )
    parameters = tuple(
        CandidateParameter(
            name=str(parameter.get("name", "")),
            value=str(parameter.get("value", "")),
            description=str(parameter.get("description", "")),
            step_index=parameter.get("step_index"),
        )
        for parameter in answer.get("parameters", [])
        if isinstance(parameter, dict)
    )
    return Reading(
        title=str(answer.get("title", "")),
        summary=str(answer.get("summary", "")),
        when_to_use=str(answer.get("when_to_use", "")),
        steps=steps,
        parameters=parameters,
        caveat=str(answer.get("caveat", "")),
    )
