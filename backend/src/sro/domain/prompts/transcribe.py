from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = "Transcribe this narration of a warehouse operator demonstrating a task."

_TASK = (
    "Return every utterance with its start and end offset in milliseconds. "
    "Transcribe only what is said: do not summarise, infer, or add steps."
)

TRANSCRIBE = Prompt(
    name="transcribe",
    version=1,
    model="gemini-3.8-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract="The narration, as audio.",
    output_schema={
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
    },
    edge_cases=(
        EdgeCase("a stretch of silence", "no segment"),
        EdgeCase("a stumble or a false start", "transcribed as said"),
        EdgeCase("a step done but not said aloud", "not added"),
    ),
)
