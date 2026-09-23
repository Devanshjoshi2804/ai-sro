from __future__ import annotations

import json
import logging
from typing import Any

from sro.application.ports.transcription import TranscribedSegment

logger = logging.getLogger(__name__)

_PROMPT = (
    "Transcribe this narration of a warehouse operator demonstrating a task. "
    "Return every utterance with its start and end offset in milliseconds. "
    "Transcribe only what is said: do not summarise, infer, or add steps."
)

_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_ms": {"type": "integer"},
                    "end_ms": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["start_ms", "end_ms", "text"],
            },
        }
    },
    "required": ["segments"],
}


class GeminiTranscriber:
    def __init__(self, model: str, *, client: Any) -> None:
        self._model = model
        self._client = client

    @property
    def available(self) -> bool:
        return True

    async def transcribe(
        self, audio: bytes, *, content_type: str
    ) -> tuple[TranscribedSegment, ...]:
        from google.genai import types

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[
                _PROMPT,
                types.Part.from_bytes(data=audio, mime_type=content_type.split(";")[0].strip()),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_SCHEMA,
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
