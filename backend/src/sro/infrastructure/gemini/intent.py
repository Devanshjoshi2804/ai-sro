from __future__ import annotations

import copy
import json
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any

from sro.application.ports.intent import Extraction, Reading
from sro.domain.prompts.read_sentence import EXTRACT_VALUES, READ_SENTENCE

if TYPE_CHECKING:  # pragma: no cover - import cost on a hot path
    from google.genai.types import GenerateContentResponse

logger = logging.getLogger(__name__)


class GeminiIntentParser:
    def __init__(self, *, client: Any) -> None:
        self._client = client

    @property
    def available(self) -> bool:
        return True

    async def read(self, utterance: str, *, after: str = "") -> Reading:
        from google.genai import types

        untrusted = {"before": after} if after else {}
        response = await _answered(
            self._client.aio.models.generate_content(
                model=READ_SENTENCE.model,
                contents=[
                    READ_SENTENCE.instructions,
                    READ_SENTENCE.evidence({}, {**untrusted, "sentence": utterance}),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=dict(READ_SENTENCE.output_schema),
                ),
            )
        )
        if response is None:
            return Reading()
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

        schema: dict[str, Any] = copy.deepcopy(dict(EXTRACT_VALUES.output_schema))
        schema["properties"]["items"]["items"]["properties"] = {
            name: {"type": "string"} for name in parameters
        }
        untrusted = {"context": context} if context else {}
        response = await _answered(
            self._client.aio.models.generate_content(
                model=EXTRACT_VALUES.model,
                contents=[
                    EXTRACT_VALUES.instructions,
                    EXTRACT_VALUES.evidence(
                        {"parameters": list(parameters)}, {**untrusted, "request": utterance}
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=schema
                ),
            )
        )
        if response is None:
            return Extraction(note="the reader did not answer, so nothing was read from this")
        return _parse(response.text, parameters)


async def _answered(call: Awaitable[GenerateContentResponse]) -> GenerateContentResponse | None:
    try:
        return await call
    except Exception:
        logger.warning("the model did not answer; falling back to what can be decided without it")
        return None


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
