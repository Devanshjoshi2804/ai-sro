# Notes for `backend/src/sro/domain/prompts/plan_step.py`

Notes on [`backend/src/sro/domain/prompts/plan_step.py`](../../../../../../../backend/src/sro/domain/prompts/plan_step.py). Each note names the code it explains (function or class, then the line in the current file).

## module, [line 26](../../../../../../../backend/src/sro/domain/prompts/plan_step.py#L26): Note on the line above

Code: `PLAN_STEP = Prompt(`

> What plans one step of a workflow run, from the step's evidence. Moved out of
> `sro.domain.execution.planning` (`PLAN_INSTRUCTIONS`, `PLAN_SCHEMA`) when the
> prompts became records; the text is the old instructions verbatim, split at
> their first blank line into role and task.
>
> `plan_step` asks it through `ask`, with the evidence it has always built as one
> untrusted block. So the answer is held to this schema before the planner reads
> it: a `kind` outside the enum or a `why` that is not a string is an unsure
> answer (`data` is `None`), never a plan. The nullable fields -- `action`,
> `value`, `url` -- are dropped alone when broken (`Prompt.kept`), so an invented
> action falls back to the operator's recorded gesture, as a null one does. The planner's
> own check for a kind the protocol does not have went with it: the schema is that
> check now.
>
> Version 1 is not the text the old constant sent. `ask` adds the input contract,
> the rules and the cases, fences the evidence and says the task again after it.
> The words the model is told are unchanged; the envelope is new, and the first
> `make eval` on the repair suite measures it.

## module, [line 43](../../../../../../../backend/src/sro/domain/prompts/plan_step.py#L43): Comment

Code: `"properties": {`

> kind first, why last: decide, then explain.

## module, [line 29](../../../../../../../backend/src/sro/domain/prompts/plan_step.py#L29): Note on the line above

Code: `model="gemini-3.8-flash",`

> What plans each step of a workflow run.
>
> The settings that were `gemini-3.7-flash` until 2026-09-15 -- the
> transcription, the vision rung and the chat door -- and `3.7-flash` is not
> in `prices.py`. So every call on those three recorded `cost_usd = 0.0` and
> the day's spend read lower than it was, which is the exact failure
> `prices.py` opens by describing. They are on the model the rest of the
> system already uses and the bakeoff already measured. The rig's `plan_model`
> (`config.py:41`). Deliberately the fast model: a run plans once per step and
> a slow plan is felt by an operator standing at a screen.
>
> It was the setting `gemini_plan_model` until the prompts became records.

## module, [line 92](../../../../../../../backend/src/sro/domain/prompts/plan_step.py#L92): Note on the line above

Code: `PLAN_STEP_ESCALATED = replace(`

> What re-plans a step the plan model got wrong. The rig's `rescue_model`
> (`config.py:45`). The expensive model earns its price here and not above:
> it is asked once per failure, not once per step.
>
> It was the setting `gemini_rescue_model`. A second record rather than a
> `model` argument, for the reason `SIGHT_ESCALATED` is one: the eval gate
> measures a record, and one record asked on two models is two things
> measured as one. The runner climbs `PLAN_STEP`, then this, then `SEE_STEP`.
>
> `fallback_model=None` because `replace` would otherwise carry the flash
> record's fallback onto a pro record: 3.7-flash is no stand-in for pro.
