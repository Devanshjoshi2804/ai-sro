"""No intent parser. Chat still resolves a skill and asks for its values."""

from __future__ import annotations

from sro.application.ports.intent import Extraction


class NoIntentParser:
    @property
    def available(self) -> bool:
        return False

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction:
        return Extraction(missing=parameters, note="no intent parser is configured")
