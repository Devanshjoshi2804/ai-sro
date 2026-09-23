from __future__ import annotations

from sro.application.ports.intent import Extraction, Reading


class NoIntentParser:
    @property
    def available(self) -> bool:
        return False

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction:
        return Extraction(missing=parameters, note="no intent parser is configured")

    async def read(self, utterance: str, *, after: str = "") -> Reading:
        return Reading(confidence=0.0)
