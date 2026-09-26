import json

from sro.domain.observation.window import tokens
from sro.domain.prompts.mine import MINE
from sro.domain.skill.workflow import Step, Workflow, new_workflow_id

K_SAMPLES = 1

K_MAX_CROSSING_TOKENS = 2_000


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


def mining_blocks(
    day: list[dict[str, object]],
    crossings: dict[str, list[str]],
    known: list[dict[str, object]],
    kb: str,
) -> dict[str, str]:
    in_day = {str(one.get("id")) for one in day}
    citable = {
        value: [gesture_id for gesture_id in ids if gesture_id in in_day]
        for value, ids in crossings.items()
    }
    blocks = {"day": json.dumps(day, indent=1, ensure_ascii=False)}
    bounded = bounded_crossings({v: ids for v, ids in citable.items() if len(ids) > 1})
    if bounded:
        blocks["crossings"] = json.dumps(bounded, indent=1, ensure_ascii=False)
    if known:
        blocks["known"] = json.dumps(known, indent=1, ensure_ascii=False)
    if kb:
        blocks["knowledge"] = kb
    return blocks


_PROBE_DAY: list[dict[str, object]] = [{"id": "y"}, {"id": "z"}]
PROMPT_OVERHEAD_TOKENS = (
    tokens(MINE.instructions)
    + tokens(MINE.evidence({}, mining_blocks(_PROBE_DAY, {"x": ["y", "z"]}, [{"x": "y"}], "x")))
    + tokens(json.dumps(dict(MINE.output_schema)))
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
    )
