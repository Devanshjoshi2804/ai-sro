"""Narration to timed segments, through Gemini.

The audio leaves the deployment, so this adapter is bound only when a key is
configured and transcription is switched on. See docs/12-execution-and-agents.md
on egress: capture stays in the customer's infrastructure, sending does not.
"""

from __future__ import annotations

import json
import logging

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
    """The SDK is imported here rather than at module scope.

    A deployment that never sends anything to a hosted model should not load a
    hosted model's client to boot, and the composition root imports this module
    either way.
    """

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

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
    """Model output is data crossing a trust boundary; a bad shape is silence.

    A demonstration is still perfectly usable without narration, so a malformed
    response must not fail the upload the operator is waiting on.
    """
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
