"""No transcription backend.

Narration is optional, so this is the default binding rather than an error path.
``available`` is False and callers skip the step; nothing raises.
"""

from __future__ import annotations

from sro.application.ports.transcription import Transcriber


class NullTranscriber(Transcriber):
    @property
    def available(self) -> bool:
        return False

    async def transcribe(self, audio: bytes, *, content_type: str) -> str:
        return ""
