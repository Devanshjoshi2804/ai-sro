"""The chat door. Saying it offers the work; pressing start authorises it.

Flash reads the utterance against the workflows the rig holds and answers
which one, with which values, and what is still missing. Nothing performs from
here: the answer is an offer the form renders, and `POST /v1/runs` is the press.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from rig.models import Answer, Asker
from rig.workflows import Workflow

UNDERSTAND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "workflow_id": {"type": "string", "nullable": True},
        # A list of pairs, not a map: the Gemini Developer API refuses
        # `additionalProperties`, and a map of parameter name to value is
        # exactly that. Found the first time this door met the real API.
        "values": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
                "required": ["name", "value"],
                "propertyOrdering": ["name", "value"],
            },
        },
        "missing": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["workflow_id", "values", "missing"],
    "propertyOrdering": ["workflow_id", "values", "missing"],
}

INSTRUCTIONS = """An operator has said what they want done. You are given the jobs this system
can do, each with the parameters it takes and the values it has seen. Answer
which job they mean (its id, or null if none fits), the values they gave for
its parameters, and which parameters are still missing. Never invent a value.

A job is a kind of work, not the one time it was done. Its title and narrative
were read from a demonstration and carry that demonstration's values: "Create
Work Area NEWTESTS" is the job of creating a work area, done once with the name
NEWTESTS. An operator asking for the same work with other values -- a work area
called NEWTEST9 -- means that job. Match on what the job does. Answer null only
when no job here does that kind of work at all. When two jobs do the same work,
name the one whose demonstration is closest to what was said."""


@dataclass(frozen=True, slots=True)
class Understood:
    workflow_id: str | None
    values: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    answer: Answer | None = None


async def understand(
    utterance: str, workflows: list[Workflow], asker: Asker, model: str
) -> Understood:
    held = [
        {
            "id": w.id,
            "title": w.title,
            "narrative": w.narrative,
            "parameters": [
                {"name": p.get("name"), "seen": p.get("seen_values", [])}
                for p in w.parameters
                if isinstance(p, dict)
            ],
        }
        for w in workflows
    ]
    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=json.dumps({"said": utterance, "jobs": held}, indent=2, ensure_ascii=False),
        schema=UNDERSTAND_SCHEMA,
    )
    if answer.data is None:
        return Understood(None, answer=answer)
    # A job the rig does not hold is not a job: the model naming one is a
    # hallucination, not an offer, and the form has nothing to render for it.
    by_id = {w.id: w for w in workflows}
    chosen = by_id.get(str(answer.data.get("workflow_id") or ""))
    if chosen is None:
        return Understood(None, answer=answer)
    # Values are what the run is performed with. A key the workflow never
    # declared is a value nothing asked for, arriving from a sentence a stranger
    # could have written -- so the offer carries only the parameters this
    # workflow itself names.
    declared = {p.get("name") for p in chosen.parameters if isinstance(p, dict)}
    raw = answer.data.get("values")
    pairs = (
        (p.get("name"), p.get("value"))
        for p in (raw if isinstance(raw, list) else ())
        if isinstance(p, dict)
    )
    values = {k: v for k, v in pairs if isinstance(k, str) and k in declared and isinstance(v, str)}
    # Read and ignored. `missing` stays in the schema because a model asked to
    # name what is absent picks values more carefully than one that is not --
    # but a parameter it leaves out of `missing` is a parameter the form never
    # asks for, and the run then performs with whatever the recording happened
    # to contain. What is missing is not an opinion: it is `declared` minus what
    # arrived.
    missing = sorted(n for n in declared if isinstance(n, str) and n not in values)
    return Understood(chosen.id, values, missing, answer)
