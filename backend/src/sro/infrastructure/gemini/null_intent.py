"""No intent parser. Chat still resolves a skill and asks for its values."""

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
        """Nothing read. The caller falls back to matching the words themselves,
        which is worse and is meant to be: a deployment with no model reads a
        sentence literally rather than pretending to understand it."""
        return Reading(confidence=0.0)
