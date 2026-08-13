"""Optional narration transcription. Default binding is ``NullTranscriber``."""

from __future__ import annotations

from typing import Protocol


class Transcriber(Protocol):
    @property
    def available(self) -> bool:
        """Whether a backend is configured. Absence is a normal deployment,
        so callers branch on this rather than catching."""
        ...

    async def transcribe(self, audio: bytes, *, content_type: str) -> str: ...
