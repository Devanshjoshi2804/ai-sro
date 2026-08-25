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
    Judgement,
    Reading,
    StepReading,
    TaskName,
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


_NAMING = (
    "You are naming a task that an operator of a warehouse management system "
    "performs over and over. You are given what the task is made of: the system "
    "it happens in, how often it is done, how long it takes, and the calls each "
    "doing of it makes, in order.\n\n"
    "Answer with one short line an operator would recognise on a list — what the "
    "task accomplishes, not what the software does. 'Adjust an LPN quantity after "
    "a short ship', not 'POST inventory adjust'. No system names, no URLs, no "
    "HTTP verbs, under about eight words.\n\n"
    "If the evidence does not say clearly enough what the task accomplishes, "
    "answer with an empty title rather than a guess: a wrong name on a list is "
    "worse than a dull one, because somebody will teach it believing the name."
)

_NAME_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "because": {"type": "string"}},
    "required": ["title"],
}

_JUDGING = {
    "variant": (
        "Two tasks were observed in the same system by the same operator, and "
        "their steps are close but not identical. Decide whether they are the "
        "same piece of work done two ways — an extra page visited, a step done "
        "in a different order — or two genuinely different tasks that happen to "
        "touch the same screens.\n\n"
        "Say no unless the evidence is clear. These are shown to a person as a "
        "suggestion, and a confident wrong one costs more than a missed one."
    ),
    "workflow": (
        "Two tasks were observed in different systems, one immediately after the "
        "other, more than once. Decide whether they are two halves of one piece "
        "of work — something checked in one system and then recorded in the "
        "other — or two unrelated tasks that happen to be done at the same time "
        "of day.\n\n"
        "Say no unless the evidence is clear. Doing two things in a row is not "
        "the same as doing one thing across two systems."
    ),
}

_JUDGEMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"joined": {"type": "boolean"}, "because": {"type": "string"}},
    "required": ["joined", "because"],
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

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[_INSTRUCTIONS, "EVIDENCE\n" + evidence],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=_SCHEMA
                ),
            )
        except Exception:
            # An induction that loses its narrative is still an induction: the
            # calls are the skill. Failing the whole thing because a hosted
            # model answered 500 would throw away two demonstrations.
            logger.warning("the interpreter did not answer; inducing without a reading")
            return Reading(caveat="the interpreter did not answer")
        return _parse(response.text)

    async def name_task(self, evidence: str) -> TaskName:
        answer = await self._ask(_NAMING, evidence, _NAME_SCHEMA)
        if answer is None:
            return TaskName()
        return TaskName(
            title=str(answer.get("title", "")).strip(),
            because=str(answer.get("because", "")).strip(),
        )

    async def judge_join(self, kind: str, first: str, second: str) -> Judgement:
        instructions = _JUDGING.get(kind)
        if instructions is None:
            return Judgement()
        answer = await self._ask(
            instructions, f"FIRST\n{first}\n\nSECOND\n{second}", _JUDGEMENT_SCHEMA
        )
        if answer is None:
            return Judgement()
        return Judgement(
            joined=bool(answer.get("joined")), because=str(answer.get("because", "")).strip()
        )

    async def _ask(
        self, instructions: str, evidence: str, schema: dict[str, Any]
    ) -> dict[str, Any] | None:
        """A structured answer, or `None` for anything that went wrong.

        Both callers of this are proposals about candidates -- a sentence on a
        list and a suggestion beside it. Neither is worth an exception: what a
        candidate *is* was decided before this was asked, and stands whatever
        comes back.
        """
        from google.genai import types

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[instructions, evidence],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=schema
                ),
            )
        except Exception:
            logger.warning("the interpreter did not answer; the derived answer stands")
            return None
        try:
            answer = json.loads(response.text or "{}")
        except ValueError:
            logger.warning("the interpreter's answer could not be read")
            return None
        return answer if isinstance(answer, dict) else None


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
