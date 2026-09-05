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
        "values": {"type": "object", "additionalProperties": {"type": "string"}},
        "missing": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["workflow_id", "values", "missing"],
    "propertyOrdering": ["workflow_id", "values", "missing"],
}

INSTRUCTIONS = """An operator has said what they want done. You are given the jobs this system
can do, each with the parameters it takes and the values it has seen. Answer
which job they mean (its id, or null if none fits), the values they gave for
its parameters, and which parameters are still missing. Never invent a value."""


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
    values = {
        k: v
        for k, v in (raw.items() if isinstance(raw, dict) else ())
        if k in declared and isinstance(v, str)
    }
    missing = [
        m for m in (answer.data.get("missing") or []) if isinstance(m, str) and m in declared
    ]
    return Understood(chosen.id, values, missing, answer)
