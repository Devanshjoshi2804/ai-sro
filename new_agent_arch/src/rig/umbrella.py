"""A7, A8 — the pass that reads a window and proposes workflows.

One sample by default. Plurality voting over repeated samples gained 0.4% at
twenty times the cost in published work, and that paper's thesis is that voting
helps LESS as models get stronger -- so a newer model argues for expecting less
from repetition, not more. Reasoning effort is the first knob instead; it does
show a significant positive relationship with accuracy.
"""

import json
from typing import Any

from rig.models import Answer, Asker
from rig.window import Window
from rig.workflows import Step, Workflow, new_workflow_id

K_SAMPLES = 1
K_EFFORT = "high"

INSTRUCTIONS = """You are reading a stretch of one warehouse operator's working day.

Each entry below is one thing they did in a browser: the control they touched,
the calls it caused, and a short reading of it made earlier.

Find the jobs. A job is a run of doings that together accomplish one thing a
person would name -- creating a supplier, receiving a shipment, correcting a
count. A job may span more than one system: the operator may do half of it in a
warehouse system and half in an ERP, and those halves are still one job.

For every step of every job, cite the ids of the gestures that prove it. Cite
before you describe. A step you cannot cite is a step you should not report.

List anything you could not place under `unproven` rather than forcing it into a
job. Say which values look like the same thing appearing in two systems.

Do not invent a system that the evidence you cited does not touch."""

WORKFLOW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "workflows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "narrative": {"type": "string"},
                    "systems": {"type": "array", "items": {"type": "string"}},
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            # cites before says: identifying the evidence before
                            # composing the answer measurably beats the reverse.
                            "properties": {
                                "order": {"type": "integer"},
                                "cites": {"type": "array", "items": {"type": "string"}},
                                "says": {"type": "string"},
                                "system": {"type": "string"},
                                "parameters": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["order", "cites", "says"],
                        },
                    },
                    "parameters": {"type": "array", "items": {"type": "object"}},
                    "same_as": {"type": "string"},
                    "unproven": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "steps"],
            },
        }
    },
    "required": ["workflows"],
}


def build_prompt(
    window: Window,
    crossings: dict[str, list[str]],
    known: list[dict[str, Any]],
    kb: str,
) -> str:
    """The task first, the evidence, then the task again.

    Question-first ordering was strongest at long context, and restating the
    constraints after the evidence costs almost nothing. Nothing here marks
    which evidence matters most -- doing that was measured to reduce accuracy.
    """
    parts = [INSTRUCTIONS, "", "## The day", ""]
    parts.append(json.dumps([item.evidence for item in window.items], indent=1))
    if crossings:
        parts += [
            "",
            "## Values appearing in more than one system",
            json.dumps(crossings, indent=1),
        ]
    if known:
        parts += ["", "## Jobs already proven", json.dumps(known, indent=1)]
    if kb:
        parts += ["", "## What is known about these systems", kb]
    parts += ["", INSTRUCTIONS]
    return "\n".join(parts)


def _as_workflow(raw: object, tenant: str, answer: Answer) -> Workflow | None:
    if not isinstance(raw, dict):
        return None
    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list):
        return None

    steps: list[Step] = []
    for index, step in enumerate(steps_raw):
        if not isinstance(step, dict):
            continue
        cites = step.get("cites")
        steps.append(
            Step(
                order=step["order"] if isinstance(step.get("order"), int) else index,
                says=step["says"] if isinstance(step.get("says"), str) else "",
                system=step["system"] if isinstance(step.get("system"), str) else None,
                cites=[c for c in cites if isinstance(c, str)] if isinstance(cites, list) else [],
                parameters=[p for p in step.get("parameters", []) if isinstance(p, str)]
                if isinstance(step.get("parameters"), list)
                else [],
            )
        )

    return Workflow(
        id=new_workflow_id(),
        tenant=tenant,
        title=raw["title"] if isinstance(raw.get("title"), str) else "",
        narrative=raw["narrative"] if isinstance(raw.get("narrative"), str) else "",
        systems=[s for s in raw.get("systems", []) if isinstance(s, str)]
        if isinstance(raw.get("systems"), list)
        else [],
        steps=steps,
        parameters=[p for p in raw.get("parameters", []) if isinstance(p, dict)]
        if isinstance(raw.get("parameters"), list)
        else [],
        same_as=raw["same_as"] if isinstance(raw.get("same_as"), str) else None,
        unproven=[u for u in raw.get("unproven", []) if isinstance(u, str)]
        if isinstance(raw.get("unproven"), list)
        else [],
        cost_usd=answer.cost_usd,
        unpriced=answer.unpriced,
    )


async def propose(
    window: Window,
    crossings: dict[str, list[str]],
    known: list[dict[str, Any]],
    kb: str,
    *,
    asker: Asker,
    model: str,
    tenant: str,
) -> tuple[list[Workflow], Answer]:
    """One pass. Returns what it proposed and what the call cost."""
    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=build_prompt(window, crossings, known, kb),
        schema=WORKFLOW_SCHEMA,
    )
    if answer.data is None:
        return [], answer

    raw = answer.data.get("workflows")
    if not isinstance(raw, list):
        return [], answer

    proposed = [_as_workflow(item, tenant, answer) for item in raw]
    return [w for w in proposed if w is not None], answer
