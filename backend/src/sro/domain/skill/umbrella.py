import json

from sro.domain.observation.window import Packed, Window, arrange, tokens
from sro.domain.shared.prices import Effort
from sro.domain.skill.workflow import Step, Workflow, new_workflow_id

K_SAMPLES = 1
K_EFFORT: Effort = "medium"

K_MAX_CROSSING_TOKENS = 2_000

INSTRUCTIONS = """You are reading a stretch of one warehouse operator's working day.

Each entry below is one thing they did in a browser: the control they touched,
the calls it caused, and a short reading of it made earlier.

Find the jobs. A job is a run of doings that together accomplish one thing a
person would name -- creating a supplier, receiving a shipment, correcting a
count. A job may span more than one system: the operator may do half of it in a
warehouse system and half in an ERP, and those halves are still one job.

Some of what you are reading may be another doing of a job listed under
"Jobs already proven". That list is there so you can RECOGNISE work, not so
you can skip it: report a job you have seen before exactly like any other,
with its steps and its citations. A second doing is the only way anything here
learns which of a job's values vary, and a doing left out is a doing nobody
can learn from. Deciding which of your answers describe the same job is not
your work -- report what you see and it will be worked out.

An operator often does the same job several times in a row -- four customer
types, one after another, from four emails. That is ONE job done four times.
It is not four jobs, and it is not one job of four times the length: report it
once, with the steps of a SINGLE doing, and put what changed between the
doings in `parameters` -- the name of the field, and every value you saw in
it. The steps say what is always done; the parameters say what varies.

A job has something to show for it -- something the operator could point at
afterwards and say that is what I did. Looking something up is a STEP of a job
and not a job: somebody who searches for the record they just created is
finishing one, and somebody who types a query into their own mailbox and reads
what comes back has not started one. A stretch that only looked at things goes
under `unplaced`.

Name the job, not the one doing of it you are reading. The title is what every
doing of that job has in common, so keep the particular values this operator
typed -- codes, names, quantities -- out of it: "Create a Customer Type", never
"Create Customer Type DSS". Those values belong in the steps.

For every step of every job, cite the ids of the gestures that prove it. Cite
before you describe. A step you cannot cite is a step you should not report.

List anything you could not place under `unplaced`, once, at the top level
beside `workflows`. It is what is left of the WINDOW when every job in it has
been described -- not something belonging to any one job you found. Do not
force it into a job.

Say which values look like the same thing appearing in two systems.

Do not invent a system that the evidence you cited does not touch."""

WORKFLOW_SCHEMA: dict[str, object] = {
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
                    "parameters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "the field that varies"},
                                "seen_values": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "every value observed in it",
                                },
                            },
                            "required": ["name", "seen_values"],
                        },
                    },
                    "same_as": {"type": "string"},
                },
                "required": ["title", "steps"],
            },
        },
        "unplaced": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["workflows"],
}


def bounded_crossings(crossings: dict[str, list[str]]) -> dict[str, list[str]]:
    kept: dict[str, list[str]] = {}
    spent = 0
    for value, ids in sorted(crossings.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        cost = tokens(json.dumps({value: ids}, indent=1, ensure_ascii=False))
        if spent + cost > K_MAX_CROSSING_TOKENS:
            continue
        spent += cost
        kept[value] = ids
    return kept


def build_prompt(
    window: Window,
    crossings: dict[str, list[str]],
    known: list[dict[str, object]],
    kb: str,
) -> str:
    parts = [INSTRUCTIONS, "", "## The day", ""]
    parts.append(
        json.dumps([item.evidence for item in arrange(window.items)], indent=1, ensure_ascii=False)
    )
    in_window = {item.gesture_id for item in window.items}
    citable = {
        value: [gesture_id for gesture_id in ids if gesture_id in in_window]
        for value, ids in crossings.items()
    }
    bounded = bounded_crossings({v: ids for v, ids in citable.items() if len(ids) > 1})
    if bounded:
        parts += [
            "",
            "## Values appearing in more than one system",
            json.dumps(bounded, indent=1, ensure_ascii=False),
        ]
    if known:
        parts += ["", "## Jobs already proven", json.dumps(known, indent=1, ensure_ascii=False)]
    if kb:
        parts += ["", "## What is known about these systems", kb]
    parts += ["", INSTRUCTIONS]
    return "\n".join(parts)


_PROBE = [Packed(gesture_id=name, at=0.0, evidence={}, strength=0.0, tokens=0) for name in "yz"]
PROMPT_OVERHEAD_TOKENS = (
    tokens(build_prompt(Window(items=_PROBE), {"x": ["y", "z"]}, [{"x": "y"}], "x"))
    + tokens(json.dumps(WORKFLOW_SCHEMA))
    + K_MAX_CROSSING_TOKENS
)


def workflow_from(raw: object, tenant: str) -> Workflow | None:
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
                order=step["order"]
                if isinstance(step.get("order"), int) and not isinstance(step["order"], bool)
                else index,
                says=step["says"] if isinstance(step.get("says"), str) else "",
                system=step["system"] if isinstance(step.get("system"), str) else None,
                cites=[c for c in cites if isinstance(c, str)] if isinstance(cites, list) else [],
                parameters=[
                    p for p in step.get("parameters", []) if isinstance(p, str) and p.strip()
                ]
                if isinstance(step.get("parameters"), list)
                else [],
            )
        )

    steps.sort(key=lambda step: step.order)
    if len({step.order for step in steps}) != len(steps):
        for position, step_out in enumerate(steps):
            step_out.order = position

    return Workflow(
        id=new_workflow_id(),
        tenant=tenant,
        title=raw["title"] if isinstance(raw.get("title"), str) else "",
        narrative=raw["narrative"] if isinstance(raw.get("narrative"), str) else "",
        systems=[s for s in raw.get("systems", []) if isinstance(s, str)]
        if isinstance(raw.get("systems"), list)
        else [],
        steps=steps,
        parameters=[
            p
            for p in raw.get("parameters", [])
            if isinstance(p, dict) and isinstance(p.get("name"), str) and p["name"].strip()
        ]
        if isinstance(raw.get("parameters"), list)
        else [],
        same_as=raw["same_as"] if isinstance(raw.get("same_as"), str) else None,
    )
