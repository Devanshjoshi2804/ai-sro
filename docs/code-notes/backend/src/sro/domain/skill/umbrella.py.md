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

## module, [line 8](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L8): Note on the line above

Code: `K_EFFORT: Effort = "medium"`

> How hard the model is told to think before it answers.
>
> `"high"` is what the rig shipped, and it is not the harmless default it looks
> like. On Gemini, thinking is billed INSIDE `max_output_tokens`: over one day of
> evidence at `high`, Gemini 3.8 Flash spent 62,913 of 65,536 tokens thinking and
> was truncated with 2,609 left to answer in -- three runs out of three, $0.38
> each, nothing kept. At `medium` the same model mined the same day successfully
> and kept 7 of 17 proposed jobs.
>
> `"medium"`, then, and measured on this backend rather than inherited: the first
> real pass over a real store -- 507 gestures from a day of Blue Yonder capture,
> `gemini-3.1-pro-preview` -- did the same thing at `high`. 204,747 in, 65,522
> out, truncated after 2,610 tokens of answer, $2.00 for nothing kept. The same
> evidence at `medium` answered in 6,041 output tokens with 3,362 of thinking,
> cost $0.93, and kept 2 of 3 proposed jobs, which then replayed 2 of 2 as
> themselves. Twice the result at half the price, and the difference is this
> word.
>
> So this constant is a budget decision as much as a quality one, and it belongs
> to whoever configures a model: a model with a small output ceiling wants
> `"medium"`. Both numbers are written down here because the choice cannot be
> made without them -- and because the first was recorded for one model and not
> applied to the one actually configured, which is how the $2.00 was spent.

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

## `bounded_crossings`, [line 111](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L111): Docstring

> The crossings that fit K_MAX_CROSSING_TOKENS, best-evidenced first.
>
> Ordered by how many gestures carry the value: values.trivial already drops
> anything above K_UBIQUITY, so nothing left here is furniture, and among what
> remains a value seen on eight gestures across two systems is a firmer link
> than one seen on two. Ties break on the value so the same store always
> produces the same prompt.

## `build_prompt`, [line 123](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L123): Docstring

> The task first, the evidence, then the task again.
>
> Question-first ordering was strongest at long context, and restating the
> constraints after the evidence costs almost nothing. Nothing here marks
> which evidence matters most -- doing that was measured to reduce accuracy.

## `workflow_from`, [line 161](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L161): Docstring

> One workflow out of one model answer, or None if it is not one.
>
> Public, unlike the rig's `_as_workflow`: the mining use case in the
> application layer calls it, and a leading underscore on something that
> crosses a layer boundary is a lie about who may use it.

## module, [line 63](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L63): Comment

Code: `"properties": {`

> cites before says: identifying the evidence before
> composing the answer measurably beats the reverse.

## module, [line 86](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L86): Comment

Code: `"parameters": {`

> The shape is declared, which it was not. `object` with
> no properties told the model nothing, while
> `chat.understand` and `skill.shape` both read
> `seen_values` off whatever came back -- so a
> model-supplied parameter arrived in whatever shape the
> model guessed and was dropped by `workflow_from`'s name
> check or carried no values anybody reads. Measured across
> three clean mines of a real day: `parameters` came back
> empty every time, on jobs whose evidence plainly showed
> four different customer types being typed.

## module, [line 105](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L105): Comment

Code: `"unplaced": {"type": "array", "items": {"type": "string"}},`

> Beside `workflows`, not inside one. It is a fact about the WINDOW --
> what was left over when every job in it had been described -- and it
> was asked for per workflow, so the model attached the window's
> leftovers to whichever job it happened to emit. Four readers then
> took it for a property of that job and refused to serve, schedule or
> fire it: on the first real cross-tab evidence this system ever mined,
> a correct six-step job carried thirty-six unplaced ids, a third of
> which were gestures supporting its own steps, and was never offered.

## `bounded_crossings`, [line 115](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L115): Comment

Code: `cost = tokens(json.dumps({value: ids}, indent=1, ensure_ascii=False))`

> Each entry measured on its own, so the count never depends on how many
> came before it. Slightly over -- it pays for a pair of braces per entry
> -- which is the direction a budget should err in.

## `bounded_crossings`, [line 116](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L116): Comment

Code: `if spent + cost > K_MAX_CROSSING_TOKENS:`

> Skipped, not stopped at. These are sorted by how many gestures carry
> the value, so the expensive ones come FIRST -- and a single value on
> 200 in-window gestures costs 2,100 tokens against a 2,000 cap, while
> `values.trivial` only discards a value above a quarter of the store.
> Breaking there emptied the whole block: the section that exists so the
> model can see a job crossing two systems, gone, because one link was
> too well evidenced to print. Nothing says so downstream, and the
> architecture's central claim quietly loses its input.

## `build_prompt`, [line 129](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L129): Comment

Code: `parts = [INSTRUCTIONS, "", "## The day", ""]`

> arrange() and not window.items directly. `pack` sorts the window into time
> order and every reader downstream depends on that -- checks.coverage
> slices it into TIME deciles, and its skew figure is only comparable across
> passes while those deciles mean the same thing. So the reordering happens
> here, at the one place the evidence becomes a prompt, exactly as
> algorithms.md's pseudocode has it: `chosen.sort(key=at)` upstream,
> `arrange(chosen)` at assembly.

## `build_prompt`, [line 133](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L133): Comment

Code: `in_window = {item.gesture_id for item in window.items}`

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

## module, [line 153](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L153): Comment

Code: `_PROBE = [Packed(gesture_id=name, at=0.0, evidence={}, strength=0.0, tokens=0) for name in`

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
> The probe's window holds the two ids its crossing names, because build_prompt
> renders only crossings whose gestures are IN the window: probed with an empty
> one the block disappears, and the probe would stop counting a heading the real
> prompt still pays for.

## `workflow_from`, [line 175](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L175): Comment

Code: `order=step["order"]`

> True is an int in Python, and would sort as step 1.

## `workflow_from`, [line 181](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L181): Comment

Code: `parameters=[`

> Same rule as the workflow-level parameters below, which is
> the point: these two arrive from one model answer and were
> checked differently -- an empty string survived here while an
> empty `name` was dropped there. The SHAPES stay different
> because the schema declares them different (a step names a
> parameter, a workflow declares one), but "a parameter with no
> usable name is not a parameter" is one rule now, applied at
> both. A blank name is no name.

## `workflow_from`, [line 189](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L189): Comment

Code: `steps.sort(key=lambda step: step.order)`

> Renumbered only when the model repeated itself. The workflow-step table
> declares PRIMARY KEY (workflow_id, ord), so two steps at order 1 is a
> workflow that cannot be saved -- and "order": 1 twice is schema-valid, so
> it is an ordinary model slip rather than a broken answer. An answer that
> numbered its steps correctly keeps its own numbering.

## `workflow_from`, [line 203](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L203): Comment

Code: `parameters=[`

> A parameter with no usable name is not a parameter, the way a step
> with no `says` is not a step. The step-level check above is the same
> rule against the same-named field one level down; `.strip()` is here
> too so that `{"name": "  "}` and `"  "` are refused alike.

## `workflow_from`, [line 186](../../../../../../../backend/src/sro/domain/skill/umbrella.py#L186): Comment

Code: `)`

> No cost here. The call that proposed this workflow proposed all of
> them, so its price belongs to the pass -- the mining pass stamps
> `pass_id` on what it keeps. Copying `answer.cost_usd` onto each
> workflow made SUM(cost_usd) overstate the bill by the number of
> workflows found.
