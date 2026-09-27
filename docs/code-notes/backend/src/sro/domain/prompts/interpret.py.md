# Notes for `backend/src/sro/domain/prompts/interpret.py`

Notes on [`backend/src/sro/domain/prompts/interpret.py`](../../../../../../../backend/src/sro/domain/prompts/interpret.py). Each note names the code it explains (function or class, then the line in the current file).

## module, [line 24](../../../../../../../backend/src/sro/domain/prompts/interpret.py#L24): Note on the line above

Code: `INTERPRET = Prompt(`

> Reading one demonstration into a workflow. It was `_INSTRUCTIONS` and
> `_SCHEMA` in `sro.infrastructure.gemini.interpreter`, text verbatim.
>
> On the pro model, which was `gemini_interpreter_model`; `NAME_SKILL` and
> `JUDGE_SKILL` were asked on the same setting and keep the same model.
>
> Reading a demonstration into a workflow, once per induction. Nobody is
> watching the clock, being wrong is expensive and lasting, and the reading is
> what an operator will see for the life of the skill -- so this is the
> reasoning model. It cannot enable computer use, and does not need to.

## module, [line 97](../../../../../../../backend/src/sro/domain/prompts/interpret.py#L97): Note on the line above

Code: `NAME_SKILL = Prompt(`

> It was `_NAMING` and `_NAME_SCHEMA`. Its cases are the ones its own text
> gives: the LPN example, the list of what a name leaves out, and the empty
> title.

## module, [line 150](../../../../../../../backend/src/sro/domain/prompts/interpret.py#L150): Note on the line above

Code: `JUDGE_SKILL = Prompt(`

> It was `_JUDGING`, a dict of two texts keyed by kind, and `_JUDGEMENT_SCHEMA`.
> One record holds both, each text verbatim under the `kind` it answers, and the
> kind is given as trusted JSON. A kind outside `JUDGED` is never asked, as a
> kind outside the dict never was. The role sentence is new: the two texts had
> none in common.
