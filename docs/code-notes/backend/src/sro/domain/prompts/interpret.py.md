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

## module, [line 115](../../../../../../../backend/src/sro/domain/prompts/interpret.py#L115): Note on the line above

Code: `NAME_SKILL = Prompt(`

> It was `_NAMING` and `_NAME_SCHEMA`. Its cases are the ones its own text
> gives: the LPN example, the list of what a name leaves out, and the empty
> title.

## module, [line 180](../../../../../../../backend/src/sro/domain/prompts/interpret.py#L180): Note on the line above

Code: `JUDGE_VARIANT = Prompt(`

> It was `_JUDGING["variant"]` and `_JUDGEMENT_SCHEMA`, text verbatim: its first
> paragraph is the role and its second the task. One record per kind, because
> the two are different questions with different words, and the eval gate
> measures a record: one record holding both would score two questions as one.

## module, [line 223](../../../../../../../backend/src/sro/domain/prompts/interpret.py#L223): Note on the line above

Code: `JUDGE_WORKFLOW = Prompt(`

> It was `_JUDGING["workflow"]`, text verbatim, split the same way.

## module, [line 254](../../../../../../../backend/src/sro/domain/prompts/interpret.py#L254): Note on the line above

Code: `JUDGES = {"variant": JUDGE_VARIANT, "workflow": JUDGE_WORKFLOW}`

> Which record answers which kind. A kind not here is never asked, as a kind
> outside `_JUDGING` never was.
