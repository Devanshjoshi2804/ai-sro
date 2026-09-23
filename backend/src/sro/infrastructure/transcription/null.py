from __future__ import annotations

from sro.application.ports.transcription import TranscribedSegment, Transcriber


class NullTranscriber(Transcriber):
    @property
    def available(self) -> bool:
        return False

    async def transcribe(
        self, audio: bytes, *, content_type: str
    ) -> tuple[TranscribedSegment, ...]:
        return ()
