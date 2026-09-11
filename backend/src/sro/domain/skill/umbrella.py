"""A7, A8 — the pass that reads a window and proposes workflows.

One sample by default. Plurality voting over repeated samples gained 0.4% at
twenty times the cost in published work, and that paper's thesis is that voting
helps LESS as models get stronger -- so a newer model argues for expecting less
from repetition, not more. Reasoning effort is the first knob instead; it does
show a significant positive relationship with accuracy.

Ported from `new_agent_arch/src/rig/umbrella.py`, everything above `propose`.
Pure -- it reads a `Window`, a `Workflow` and `tokens`, and nothing else -- so
it lives in the domain beside them rather than in the application layer with the
use case that calls it. `propose` itself asks a model and belongs to the mining
use case.
"""

import json

from sro.domain.observation.window import Packed, Window, arrange, tokens
from sro.domain.shared.prices import Effort
from sro.domain.skill.workflow import Step, Workflow, new_workflow_id

K_SAMPLES = 1
K_EFFORT: Effort = "medium"
"""How hard the model is told to think before it answers.

`"high"` is what the rig shipped, and it is not the harmless default it looks
like. On Gemini, thinking is billed INSIDE `max_output_tokens`: over one day of
evidence at `high`, Gemini 3.8 Flash spent 62,913 of 65,536 tokens thinking and
was truncated with 2,609 left to answer in -- three runs out of three, $0.38
each, nothing kept. At `medium` the same model mined the same day successfully
and kept 7 of 17 proposed jobs.

`"medium"`, then, and measured on this backend rather than inherited: the first
real pass over a real store -- 507 gestures from a day of Blue Yonder capture,
`gemini-3.1-pro-preview` -- did the same thing at `high`. 204,747 in, 65,522
out, truncated after 2,610 tokens of answer, $2.00 for nothing kept. The same
evidence at `medium` answered in 6,041 output tokens with 3,362 of thinking,
cost $0.93, and kept 2 of 3 proposed jobs, which then replayed 2 of 2 as
themselves. Twice the result at half the price, and the difference is this
word.

So this constant is a budget decision as much as a quality one, and it belongs
to whoever configures a model: a model with a small output ceiling wants
`"medium"`. Both numbers are written down here because the choice cannot be
made without them -- and because the first was recorded for one model and not
applied to the one actually configured, which is how the $2.00 was spent.
"""

K_MAX_CROSSING_TOKENS = 2_000
"""What the crossings block may cost, and it is a cap rather than a count.

Every other part of this prompt grows with the WINDOW, which the budget bounds.
`crossings` is computed by values.shared_values over the tenant's whole store, so
it grows with the store instead -- a second year of capture widens a block the
window budget never sees, and the thing that gives way is the prompt.

A cap and not a share of the budget, because this is a hint: the model is told
which values appear in two systems and decides what that means. Two thousand
tokens is ~1.3% of K_WINDOW_TOKENS and holds well over a hundred crossings,
which is far past the point where a list of "these look like the same thing"
stops being a hint and becomes furniture the K_UBIQUITY filter should have
caught. It is subtracted from the budget whether or not any crossing fires, so
the prompt fits in the case that matters -- the full one.
"""

INSTRUCTIONS = """You are reading a stretch of one warehouse operator's working day.

Each entry below is one thing they did in a browser: the control they touched,
the calls it caused, and a short reading of it made earlier.

Find the jobs. A job is a run of doings that together accomplish one thing a
person would name -- creating a supplier, receiving a shipment, correcting a
count. A job may span more than one system: the operator may do half of it in a
warehouse system and half in an ERP, and those halves are still one job.

Name the job, not the one doing of it you are reading. The title is what every
doing of that job has in common, so keep the particular values this operator
typed -- codes, names, quantities -- out of it: "Create a Customer Type", never
"Create Customer Type DSS". Those values belong in the steps.

For every step of every job, cite the ids of the gestures that prove it. Cite
before you describe. A step you cannot cite is a step you should not report.

List anything you could not place under `unproven` rather than forcing it into a
job. Say which values look like the same thing appearing in two systems.

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


def bounded_crossings(crossings: dict[str, list[str]]) -> dict[str, list[str]]:
    """The crossings that fit K_MAX_CROSSING_TOKENS, best-evidenced first.

    Ordered by how many gestures carry the value: values.trivial already drops
    anything above K_UBIQUITY, so nothing left here is furniture, and among what
    remains a value seen on eight gestures across two systems is a firmer link
    than one seen on two. Ties break on the value so the same store always
    produces the same prompt.
    """
    kept: dict[str, list[str]] = {}
    spent = 0
    for value, ids in sorted(crossings.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        # Each entry measured on its own, so the count never depends on how many
        # came before it. Slightly over -- it pays for a pair of braces per entry
        # -- which is the direction a budget should err in.
        cost = tokens(json.dumps({value: ids}, indent=1, ensure_ascii=False))
        # Skipped, not stopped at. These are sorted by how many gestures carry
        # the value, so the expensive ones come FIRST -- and a single value on
        # 200 in-window gestures costs 2,100 tokens against a 2,000 cap, while
        # `values.trivial` only discards a value above a quarter of the store.
        # Breaking there emptied the whole block: the section that exists so the
        # model can see a job crossing two systems, gone, because one link was
        # too well evidenced to print. Nothing says so downstream, and the
        # architecture's central claim quietly loses its input.
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
    """The task first, the evidence, then the task again.

    Question-first ordering was strongest at long context, and restating the
    constraints after the evidence costs almost nothing. Nothing here marks
    which evidence matters most -- doing that was measured to reduce accuracy.
    """
    # arrange() and not window.items directly. `pack` sorts the window into time
    # order and every reader downstream depends on that -- checks.coverage
    # slices it into TIME deciles, and its skew figure is only comparable across
    # passes while those deciles mean the same thing. So the reordering happens
    # here, at the one place the evidence becomes a prompt, exactly as
    # algorithms.md's pseudocode has it: `chosen.sort(key=at)` upstream,
    # `arrange(chosen)` at assembly.
    parts = [INSTRUCTIONS, "", "## The day", ""]
    parts.append(
        json.dumps([item.evidence for item in arrange(window.items)], indent=1, ensure_ascii=False)
    )
    # Only the crossings the model is allowed to cite. checks.validate refuses
    # any workflow naming an id outside the window, so a crossing whose partner
    # the budget left out is not a hint but a trap: the prompt says those ids
    # carry the same value, the model cites them, and the whole workflow --
    # the cross-system one this rig exists to find -- is discarded. Measured at
    # a 25-item window over 60 genuine pairs: 95 of the ids named were outside
    # it, every one of them a rejection waiting to happen.
    #
    # Filtered HERE, at the render, and not where the mining pass builds them:
    # `crossings` is computed over the whole tenant on purpose, because
    # window.strength gives every id in one a `linked` bonus and that bonus is
    # what pulls a crossing's partner INTO the window. Narrowing upstream would
    # spend that. What the model may be TOLD and what earns a place are two
    # questions, and only the first one is about the window.
    #
    # A value left with one id in the window is dropped rather than shown: one
    # id is not a crossing, and "this value appears in more than one system"
    # over a single gesture is a claim the prompt cannot support.
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


# What window.pack has to subtract from K_WINDOW_TOKENS before it fills anything,
# because none of it is evidence and all of it is billed as input: the task
# stated at both ends (the measured decision, and 446 tokens), every section
# heading, the response schema, and the crossings cap above.
#
# Probed rather than added up by hand -- one truthy value for each optional
# section, so the headings are counted -- and the probe's own few tokens of
# content are left in as slack. The one thing it cannot see is the evidence, and
# that is exactly what the budget is for.
#
# The probe's window holds the two ids its crossing names, because build_prompt
# renders only crossings whose gestures are IN the window: probed with an empty
# one the block disappears, and the probe would stop counting a heading the real
# prompt still pays for.
_PROBE = [Packed(gesture_id=name, at=0.0, evidence={}, strength=0.0, tokens=0) for name in "yz"]
PROMPT_OVERHEAD_TOKENS = (
    tokens(build_prompt(Window(items=_PROBE), {"x": ["y", "z"]}, [{"x": "y"}], "x"))
    + tokens(json.dumps(WORKFLOW_SCHEMA))
    + K_MAX_CROSSING_TOKENS
)


def workflow_from(raw: object, tenant: str) -> Workflow | None:
    """One workflow out of one model answer, or None if it is not one.

    Public, unlike the rig's `_as_workflow`: the mining use case in the
    application layer calls it, and a leading underscore on something that
    crosses a layer boundary is a lie about who may use it.
    """
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
                # True is an int in Python, and would sort as step 1.
                order=step["order"]
                if isinstance(step.get("order"), int) and not isinstance(step["order"], bool)
                else index,
                says=step["says"] if isinstance(step.get("says"), str) else "",
                system=step["system"] if isinstance(step.get("system"), str) else None,
                cites=[c for c in cites if isinstance(c, str)] if isinstance(cites, list) else [],
                # Same rule as the workflow-level parameters below, which is
                # the point: these two arrive from one model answer and were
                # checked differently -- an empty string survived here while an
                # empty `name` was dropped there. The SHAPES stay different
                # because the schema declares them different (a step names a
                # parameter, a workflow declares one), but "a parameter with no
                # usable name is not a parameter" is one rule now, applied at
                # both. A blank name is no name.
                parameters=[
                    p for p in step.get("parameters", []) if isinstance(p, str) and p.strip()
                ]
                if isinstance(step.get("parameters"), list)
                else [],
            )
        )

    # Renumbered only when the model repeated itself. The workflow-step table
    # declares PRIMARY KEY (workflow_id, ord), so two steps at order 1 is a
    # workflow that cannot be saved -- and "order": 1 twice is schema-valid, so
    # it is an ordinary model slip rather than a broken answer. An answer that
    # numbered its steps correctly keeps its own numbering.
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
        # A parameter with no usable name is not a parameter, the way a step
        # with no `says` is not a step. The step-level check above is the same
        # rule against the same-named field one level down; `.strip()` is here
        # too so that `{"name": "  "}` and `"  "` are refused alike.
        parameters=[
            p
            for p in raw.get("parameters", [])
            if isinstance(p, dict) and isinstance(p.get("name"), str) and p["name"].strip()
        ]
        if isinstance(raw.get("parameters"), list)
        else [],
        same_as=raw["same_as"] if isinstance(raw.get("same_as"), str) else None,
        unproven=[u for u in raw.get("unproven", []) if isinstance(u, str)]
        if isinstance(raw.get("unproven"), list)
        else [],
        # No cost here. The call that proposed this workflow proposed all of
        # them, so its price belongs to the pass -- the mining pass stamps
        # `pass_id` on what it keeps. Copying `answer.cost_usd` onto each
        # workflow made SUM(cost_usd) overstate the bill by the number of
        # workflows found.
    )
