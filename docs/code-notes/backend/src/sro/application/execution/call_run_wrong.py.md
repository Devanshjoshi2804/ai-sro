# Notes for `backend/src/sro/application/execution/call_run_wrong.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/call_run_wrong.py`](../../../../../../../backend/src/sro/application/execution/call_run_wrong.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/call_run_wrong.py#L1): Docstring

> The person a run was performed for says its result was wrong.
>
> Not a survey. This is reached by an operator pressing "undo that" or "it's
> wrong, I'll fix it", both of which are things they wanted anyway -- which is why
> the answer can be trusted. A question they answer to help us is a question they
> stop answering.
>
> The skill hears about it the same way it hears about a crash, because the
> distinction it cares about is "did this still work", and a run that made the
> wrong record did not.

## `NotYours`, [line 11](../../../../../../../backend/src/sro/application/execution/call_run_wrong.py#L11): Docstring

> This caller is not the one person who may pass judgement on this run.

## `NotYours`, [line 12](../../../../../../../backend/src/sro/application/execution/call_run_wrong.py#L12): Note on the line above

Code: `code = "not_yours"`

> Shared, deliberately, with the same-named class in `revise_run`. Both
> are "that run is not yours" to the same person on two doors, and a console
> matching on `problem.type` should not have to learn two spellings of it.
> Without a `code` at all -- which is how both shipped -- `_problem` falls
> back to `error`, so the 403 `0302584` gave them was untellable from every
> other refusal in the system.

## `StillRunning`, [line 15](../../../../../../../backend/src/sro/application/execution/call_run_wrong.py#L15): Docstring

> This run has not finished; there is no result yet for anyone to judge.
>
> A `Conflict`, not a `NotYours`: the caller is exactly the right person and
> the request is well formed, the run just is not in a state anybody can
> call wrong yet -- 409, the same as `StopRun`'s `CannotStop`, so a console
> reads it as "try again once it's stopped" rather than "not allowed".

## `CallRunWrong.execute`, [line 28](../../../../../../../backend/src/sro/application/execution/call_run_wrong.py#L28): Comment

Code: `raise NotYours("only the person this ran for can say how it came out")`

> A run drives one operator's browser and they are the only
> person who saw what it produced.

## `CallRunWrong.execute`, [line 32](../../../../../../../backend/src/sro/application/execution/call_run_wrong.py#L32): Comment

Code: `already = judge(run)`

> Judged before the record is written, not after: this is the
> verdict `FinishRun` already counted for this run when it ended,
> and it is only recoverable while `wrong_because` is still unset
> -- `judge` reads that field before anything the steps say. Passed
> to `apply_verdict` below so the operator's answer replaces that
> entry instead of adding a second one for the same run, which had
> `total_runs` and `clean_runs` permanently overstating and let
> `earn` promote on a clean run the operator was in the middle of
> taking back.

## `CallRunWrong.execute`, [line 36](../../../../../../../backend/src/sro/application/execution/call_run_wrong.py#L36): Comment

Code: `skill = await uow.skills.get(ctx.tenant_id, run.skill_id)`

> The one place a verdict reaches a skill's track record and
> stage -- `FinishRun` reaches the same function when a run ends on
> its own. A skill's rung must not depend on which of them ran.
