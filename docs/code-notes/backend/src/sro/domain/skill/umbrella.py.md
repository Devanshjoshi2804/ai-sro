# Notes for `backend/src/sro/domain/skill/umbrella.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/umbrella.py`](../../../../../../../backend/src/sro/domain/skill/umbrella.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L1): Docstring

> A7, A8 — the pass that reads a window and proposes workflows.
>
> One sample by default. Plurality voting over repeated samples gained 0.4% at
> twenty times the cost in published work, and that paper's thesis is that voting
> helps LESS as models get stronger -- so a newer model argues for expecting less
> from repetition, not more. Reasoning effort is the first knob instead; it does
> show a significant positive relationship with accuracy.
>
> Ported from `new_agent_arch/src/rig/umbrella.py`, everything above `propose`.
> Pure -- it reads a `Window`, a `Workflow` and `tokens`, and nothing else -- so
> it lives in the domain beside them rather than in the application layer with the
> use case that calls it. `propose` itself asks a model and belongs to the mining
> use case.

## module, [line 10](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L10): Note on the line above

Code: `K_MAX_CROSSING_TOKENS = 2_000`

> What the crossings block may cost, and it is a cap rather than a count.
>
> Every other part of this prompt grows with the WINDOW, which the budget bounds.
> `crossings` is computed by values.shared_values over the tenant's whole store, so
> it grows with the store instead -- a second year of capture widens a block the
> window budget never sees, and the thing that gives way is the prompt.
>
> A cap and not a share of the budget, because this is a hint: the model is told
> which values appear in two systems and decides what that means. Two thousand
> tokens is ~1.3% of K_WINDOW_TOKENS and holds well over a hundred crossings,
> which is far past the point where a list of "these look like the same thing"
> stops being a hint and becomes furniture the K_UBIQUITY filter should have
> caught. It is subtracted from the budget whether or not any crossing fires, so
> the prompt fits in the case that matters -- the full one.

## `bounded_crossings`, [line 13](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L13): Docstring

> The crossings that fit K_MAX_CROSSING_TOKENS, best-evidenced first.
>
> Ordered by how many gestures carry the value: values.trivial already drops
> anything above K_UBIQUITY, so nothing left here is furniture, and among what
> remains a value seen on eight gestures across two systems is a firmer link
> than one seen on two. Ties break on the value so the same store always
> produces the same prompt.

## `_has_control`, [line 56](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L56): Comment

Code: `def _has_control(value: object) -> bool:`

> Control characters other than tab, newline and carriage return. A NUL
> reached the store from a model answer and Postgres refused the insert,
> killing the pass's save. None of them is text anybody reads, so a job
> carrying one anywhere -- title, a step, a parameter's values -- is
> refused whole (M1 round 3); `propose` drops only that job and keeps the
> rest of the answer.

## `workflow_from`, [line 66](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L66): Docstring

> One workflow out of one model answer, or None if it is not one.
>
> Public, unlike the rig's `_as_workflow`: the mining use case in the
> application layer calls it, and a leading underscore on something that
> crosses a layer boundary is a lie about who may use it.

## `bounded_crossings`, [line 17](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L17): Comment

Code: `cost = tokens(json.dumps({value: ids}, indent=1, ensure_ascii=False))`

> Each entry measured on its own, so the count never depends on how many
> came before it. Slightly over -- it pays for a pair of braces per entry
> -- which is the direction a budget should err in.

## `bounded_crossings`, [line 18](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L18): Comment

Code: `if spent + cost > K_MAX_CROSSING_TOKENS:`

> Skipped, not stopped at. These are sorted by how many gestures carry
> the value, so the expensive ones come FIRST -- and a single value on
> 200 in-window gestures costs 2,100 tokens against a 2,000 cap, while
> `values.trivial` only discards a value above a quarter of the store.
> Breaking there emptied the whole block: the section that exists so the
> model can see a job crossing two systems, gone, because one link was
> too well evidenced to print. Nothing says so downstream, and the
> architecture's central claim quietly loses its input.

## `workflow_from`, [line 80](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L80): Comment

Code: `order=step["order"]`

> True is an int in Python, and would sort as step 1.

## `workflow_from`, [line 86](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L86): Comment

Code: `parameters=[`

> Same rule as the workflow-level parameters below, which is
> the point: these two arrive from one model answer and were
> checked differently -- an empty string survived here while an
> empty `name` was dropped there. The SHAPES stay different
> because the schema declares them different (a step names a
> parameter, a workflow declares one), but "a parameter with no
> usable name is not a parameter" is one rule now, applied at
> both. A blank name is no name.

## `workflow_from`, [line 94](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L94): Comment

Code: `steps.sort(key=lambda step: step.order)`

> The model's order is only a sort key: every step is renumbered to its
> position, 0..n-1 (M1 round 2). The workflow-step table declares PRIMARY
> KEY (workflow_id, ord) on an integer, and "order": 1 twice or an order
> past int32 are both schema-valid answers. The second failed in the
> driver, before the server, so the transaction lived on and the pass
> committed a job row with no steps. The rule was once to renumber only
> on a repeat; nothing reads a model's own numbering.

## `workflow_from`, [line 107](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L107): Comment

Code: `parameters=[`

> A parameter with no usable name is not a parameter, the way a step
> with no `says` is not a step. The step-level check above is the same
> rule against the same-named field one level down; `.strip()` is here
> too so that `{"name": "  "}` and `"  "` are refused alike.

## `workflow_from`, [line 114](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L114): Comment

Code: `)`

> No cost here. The call that proposed this workflow proposed all of
> them, so its price belongs to the pass -- the mining pass stamps
> `pass_id` on what it keeps. Copying `answer.cost_usd` onto each
> workflow made SUM(cost_usd) overstate the bill by the number of
> workflows found.

## `mining_blocks`, [line 31](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L31): Comment

Code: `in_day = {str(one.get("id")) for one in day}`

> Only the crossings the model is allowed to cite. checks.validate refuses
> any workflow naming an id outside the window, so a crossing whose partner
> the budget left out is not a hint but a trap: the prompt says those ids
> carry the same value, the model cites them, and the whole workflow --
> the cross-system one this rig exists to find -- is discarded. Measured at
> a 25-item window over 60 genuine pairs: 95 of the ids named were outside
> it, every one of them a rejection waiting to happen.
>
> Filtered HERE, at the render, and not where the mining pass builds them:
> `crossings` is computed over the whole tenant on purpose, because
> window.strength gives every id in one a `linked` bonus and that bonus is
> what pulls a crossing's partner INTO the window. Narrowing upstream would
> spend that. What the model may be TOLD and what earns a place are two
> questions, and only the first one is about the window.
>
> A value left with one id in the window is dropped rather than shown: one
> id is not a crossing, and "this value appears in more than one system"
> over a single gesture is a claim the prompt cannot support.

## module, [line 47](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L47): Comment

Code: `_PROBE_DAY: list[dict[str, object]] = [{"id": "y"}, {"id": "z"}]`

> What window.pack has to subtract from K_WINDOW_TOKENS before it fills anything,
> because none of it is evidence and all of it is billed as input: the task
> stated at both ends (the measured decision, and 446 tokens), every section
> heading, the response schema, and the crossings cap above.
>
> Probed rather than added up by hand -- one truthy value for each optional
> section, so the headings are counted -- and the probe's own few tokens of
> content are left in as slack. The one thing it cannot see is the evidence, and
> that is exactly what the budget is for.
>
> The probe's day holds the two ids its crossing names, because mining_blocks
> renders only crossings whose gestures are IN the day: probed with an empty
> one the block disappears, and the probe would stop counting a heading the real
> prompt still pays for.
