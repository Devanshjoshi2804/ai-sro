"""Optional narration transcription. Default binding is ``NullTranscriber``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class TranscribedSegment:
    """One utterance, as offsets into the audio.

    Offsets rather than timestamps because a transcriber knows only the file it
    was given; the caller owns the clock the microphone started on.
    """

    start_ms: int
    end_ms: int
    text: str

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.end_ms < self.start_ms:
            raise InvariantViolation("a transcribed segment cannot end before it starts")


class Transcriber(Protocol):
    @property
    def available(self) -> bool:
        """Whether a backend is configured. Absence is a normal deployment,
        so callers branch on this rather than catching."""
        ...

    async def transcribe(
        self, audio: bytes, *, content_type: str
    ) -> tuple[TranscribedSegment, ...]:
        """Timed segments, in any order. An empty result is a silent recording,
        not a failure."""
        ...
