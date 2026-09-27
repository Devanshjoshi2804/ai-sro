# Notes for `backend/src/sro/domain/prompts/see_step.py`

Notes on [`backend/src/sro/domain/prompts/see_step.py`](../../../../../../../backend/src/sro/domain/prompts/see_step.py). Each note names the code it explains (function or class, then the line in the current file).

## module, [line 44](../../../../../../../backend/src/sro/domain/prompts/see_step.py#L44): Note on the line above

Code: `SEE_STEP = Prompt(`

> What finds a control by looking, once every recorded identity missed. Moved
> out of `sro.domain.execution.planning` (`SIGHT_INSTRUCTIONS`, `SIGHT_SCHEMA`),
> text verbatim, split at its first blank line into role and task.
>
> `plan_by_sight` asks it through `ask`, so an answer is held to this schema: an
> action a point cannot take, or an answer with no `points_at`, is unsure. The
> `SIGHT_ACTIONS` check in the planner and its `found`-only fallback went with
> it, because the schema already refuses what they refused.

## module, [line 47](../../../../../../../backend/src/sro/domain/prompts/see_step.py#L47): Note on the line above

Code: `model="gemini-3.1-pro-preview",`

> The rescue model, as it was: the runner asked this rung and its looks on
> `gemini_rescue_model`. The brief for P2 listed this record on `3.8-flash`, but
> said its models are the defaults of the settings they replace, and the setting
> this one replaces is the rescue model's. Moving the model is a prompt change
> that needs its own `make eval`, so this record keeps the model the code ran.

## module, [line 62](../../../../../../../backend/src/sro/domain/prompts/see_step.py#L62): Comment

Code: `"action": {"type": "string", "enum": ["click", "type", "press"]},`

> No select: `sroPage.performAt` has no way to choose an option at a
> point, and an action the browser cannot take is a step that stops.

## module, [line 64](../../../../../../../backend/src/sro/domain/prompts/see_step.py#L64): Comment

Code: `"points_at": {`

> WHAT the point is, which is required and so cannot be skipped.
>
> This was an optional `open_first` object, and it was skipped every
> time: the model wrote "it is likely under the 'Partners' menu" in
> `why` and left the field null, twice in a row, with the Partners tab
> plainly on the screen it was looking at. A model fills what a schema
> demands and passes over what it offers.
>
> So there is one point and one question about it. `the_control` is
> the step itself; `what_reveals_it` is a menu to open first, clicked
> instead of the step, after which this rung is asked again with a new
> picture; `nothing` is nowhere to point, which is the honest refusal
> this rung must always be able to give.
