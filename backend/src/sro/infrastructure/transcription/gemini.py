from __future__ import annotations

import logging
from typing import Any

from sro.application.ports.transcription import TranscribedSegment
from sro.application.shared.asking import ask
from sro.domain.prompts.transcribe import TRANSCRIBE
from sro.infrastructure.gemini.asker import GeminiAsker

logger = logging.getLogger(__name__)


class GeminiTranscriber:
    def __init__(self, *, client: Any) -> None:
        self._asker = GeminiAsker(client=client)

    @property
    def available(self) -> bool:
        return True

    async def transcribe(
        self, audio: bytes, *, content_type: str
    ) -> tuple[TranscribedSegment, ...]:
        answer = await ask(
            self._asker,
            TRANSCRIBE,
            trusted={},
            audio=(audio, content_type.split(";")[0].strip()),
        )
        if answer.data is None:
            if answer.malformed:
                logger.warning("transcription returned something that is not segments")
                return ()
            raise RuntimeError(answer.error or "transcription failed on both models")
        segments = answer.data["segments"]
        if not isinstance(segments, list):
            logger.warning("transcription returned something that is not segments")
            return ()
        return tuple(
            TranscribedSegment(
                start_ms=int(one["start_ms"]),
                end_ms=int(one["end_ms"]),
                text=str(one["text"]).strip(),
            )
            for one in segments
            if str(one["text"]).strip()
        )
