from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class TranscribedSegment:
    start_ms: int
    end_ms: int
    text: str

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.end_ms < self.start_ms:
            raise InvariantViolation("a transcribed segment cannot end before it starts")


class Transcriber(Protocol):
    @property
    def available(self) -> bool: ...

    async def transcribe(
        self, audio: bytes, *, content_type: str
    ) -> tuple[TranscribedSegment, ...]: ...
