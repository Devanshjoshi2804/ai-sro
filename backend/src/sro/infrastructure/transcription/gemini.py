from __future__ import annotations

import json
import logging
from typing import Any

from sro.application.ports.transcription import TranscribedSegment
from sro.domain.prompts.transcribe import TRANSCRIBE

logger = logging.getLogger(__name__)


class GeminiTranscriber:
    def __init__(self, *, client: Any) -> None:
        self._client = client

    @property
    def available(self) -> bool:
        return True

    async def transcribe(
        self, audio: bytes, *, content_type: str
    ) -> tuple[TranscribedSegment, ...]:
        from google.genai import types

        response = await self._client.aio.models.generate_content(
            model=TRANSCRIBE.model,
            contents=[
                TRANSCRIBE.instructions,
                types.Part.from_bytes(data=audio, mime_type=content_type.split(";")[0].strip()),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=dict(TRANSCRIBE.output_schema),
            ),
        )
        return _parse(response.text)


def _parse(text: str | None) -> tuple[TranscribedSegment, ...]:
    try:
        document = json.loads(text or "{}")
        segments = document["segments"]
    except (ValueError, KeyError, TypeError):
        logger.warning("transcription returned something that is not segments")
        return ()

    kept: list[TranscribedSegment] = []
    for segment in segments:
        try:
            if str(segment["text"]).strip():
                kept.append(
                    TranscribedSegment(
                        start_ms=int(segment["start_ms"]),
                        end_ms=int(segment["end_ms"]),
                        text=str(segment["text"]).strip(),
                    )
                )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(kept)
