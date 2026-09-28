from __future__ import annotations

import json
import logging
from typing import Any

from sro.application.ports.interpretation import CandidateParameter, Reading, StepReading
from sro.domain.prompts.interpret import INTERPRET

logger = logging.getLogger(__name__)


class GeminiInterpreter:
    def __init__(self, *, client: Any) -> None:
        self._client = client

    @property
    def available(self) -> bool:
        return True

    async def read(self, evidence: str) -> Reading:
        from google.genai import types

        try:
            response = await self._client.aio.models.generate_content(
                model=INTERPRET.model,
                contents=[INTERPRET.instructions, INTERPRET.evidence({}, {"evidence": evidence})],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=dict(INTERPRET.output_schema),
                ),
            )
        except Exception:
            logger.warning("the interpreter did not answer; inducing without a reading")
            return Reading(caveat="the interpreter did not answer")
        return _parse(response.text)


def _parse(text: str | None) -> Reading:
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
