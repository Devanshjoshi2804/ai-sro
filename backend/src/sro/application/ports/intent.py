from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Extraction:
    items: tuple[dict[str, str], ...] = ()

    missing: tuple[str, ...] = ()

    note: str = ""


@dataclass(frozen=True, slots=True)
class Reading:
    wants: str = "act"

    verb: str = ""

    entity: str = ""

    continues: bool = False

    confidence: float = 0.0


class IntentParser(Protocol):
    @property
    def available(self) -> bool: ...

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction: ...

    async def read(self, utterance: str, *, after: str = "") -> Reading: ...
