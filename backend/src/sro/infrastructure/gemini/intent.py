from __future__ import annotations

import copy
import json
import logging
from dataclasses import replace
from typing import Any

from sro.application.ports.intent import Extraction, Reading
from sro.application.shared.asking import ask
from sro.domain.prompts.read_sentence import EXTRACT_VALUES, READ_SENTENCE
from sro.infrastructure.gemini.asker import GeminiAsker

logger = logging.getLogger(__name__)


class GeminiIntentParser:
    def __init__(self, *, client: Any) -> None:
        self._asker = GeminiAsker(client=client)

    @property
    def available(self) -> bool:
        return True

    async def read(self, utterance: str, *, after: str = "") -> Reading:
        untrusted = {"before": after} if after else {}
        answer = (
            await ask(
                self._asker,
                READ_SENTENCE,
                trusted={},
                untrusted={**untrusted, "sentence": utterance},
            )
        ).data
        if answer is None:
            logger.warning("the intent parser did not answer with a reading")
            return Reading()
        values = answer.get("values")
        return Reading(
            wants=str(answer["wants"]),
            verb=str(answer["verb"]),
            entity=str(answer["entity"]),
            continues=bool(answer["continues"]),
            values={str(k): str(v) for k, v in values.items()} if isinstance(values, dict) else {},
            confidence=float(str(answer["confidence"])),
        )

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction:
        schema: dict[str, Any] = copy.deepcopy(dict(EXTRACT_VALUES.output_schema))
        schema["properties"]["items"]["items"]["properties"] = {
            name: {"type": "string"} for name in parameters
        }
        untrusted = {"context": context} if context else {}
        answer = await ask(
            self._asker,
            replace(EXTRACT_VALUES, output_schema=schema),
            trusted={},
            untrusted={
                "parameters": json.dumps(list(parameters), ensure_ascii=False),
                **untrusted,
                "request": utterance,
            },
        )
        if answer.data is None:
            logger.warning("the intent parser did not answer with an extraction")
            return Extraction(note="the reader did not answer, so nothing was read from this")
        return _parse(answer.data, parameters)


def _parse(answer: dict[str, object], declared: tuple[str, ...]) -> Extraction:
    allowed = set(declared)
    found = answer["items"]
    missing = answer.get("missing")
    items = tuple(
        {k: str(v) for k, v in item.items() if k in allowed and str(v).strip()}
        for item in (found if isinstance(found, list) else [])
        if isinstance(item, dict)
    )
    return Extraction(
        items=tuple(item for item in items if item),
        missing=tuple(
            str(m) for m in (missing if isinstance(missing, list) else []) if str(m) in allowed
        ),
        note=str(answer.get("note", "")),
    )
