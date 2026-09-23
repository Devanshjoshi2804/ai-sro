# Notes for `backend/src/sro/application/execution/revise_run.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/revise_run.py`](../../../../../../../backend/src/sro/application/execution/revise_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/revise_run.py#L1): Docstring

> The operator changes a value while the run is still going.
>
> The panel draws a run as it happens, a row per step, and a step that has not
> been sent can still be argued with: the address was wrong, or the mail that
> started this never said which one. What has already gone to the warehouse has
> gone -- steps record what they sent and nothing here rewrites them -- and what
> is still to come renders from the new value.
>
> That works because a step is a fresh read: `PerformStep` loads the run before
> each one, so a value saved between two steps is the value the second uses. It
> is the same property durability rests on, used for a different purpose.
>
> Only the person the run is being performed for. A run drives their browser and
> they are the one watching it; `CallRunWrong` refuses on the same grounds, and
> for the same reason.

## `NotYours`, [line 11](../../../../../../../backend/src/sro/application/execution/revise_run.py#L11): Docstring

> This caller is not the person this run is being performed for.
>
> A separate class from `call_run_wrong.NotYours` with the same name and the
> same `code`: two doors, one refusal to the same person, and a console that
> matches on `problem.type` should not have to learn two spellings of it.
> Without a `code` -- which is how both shipped -- `_problem` falls back to
> `error`, so the 403 `0302584` finally gave them was untellable from every
> other refusal in the system.

## `ReviseRun.execute`, [line 27](../../../../../../../backend/src/sro/application/execution/revise_run.py#L27): Comment

Code: `run.revise(values, at=self._clock.now())`

> Every refusal below this line is the domain's: a finished run, a
> name the skill never declared, a change that names nothing. They
> are invariants of the run rather than rules about the request, so
> they live where anything else that touches a run will meet them.
