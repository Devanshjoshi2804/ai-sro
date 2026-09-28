# Notes for `backend/src/sro/domain/prompts/interpret.py`

Notes on [`backend/src/sro/domain/prompts/interpret.py`](../../../../../../../backend/src/sro/domain/prompts/interpret.py). Each note names the code it explains (function or class, then the line in the current file).

## module, [line 24](../../../../../../../backend/src/sro/domain/prompts/interpret.py#L24): Note on the line above

Code: `INTERPRET = Prompt(`

> Reading one demonstration into a workflow. It was `_INSTRUCTIONS` and
> `_SCHEMA` in `sro.infrastructure.gemini.interpreter`, text verbatim.
>
> On the pro model, which was `gemini_interpreter_model`; `NAME_SKILL`,
> `JUDGE_VARIANT` and `JUDGE_WORKFLOW` were asked on the same setting and keep
> the same model.
>
> Reading a demonstration into a workflow, once per induction. Nobody is
> watching the clock, being wrong is expensive and lasting, and the reading is
> what an operator will see for the life of the skill -- so this is the
> reasoning model. It cannot enable computer use, and does not need to.
