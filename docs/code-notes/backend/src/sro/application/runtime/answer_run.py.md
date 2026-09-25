# Notes for `backend/src/sro/application/runtime/answer_run.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/answer_run.py`](../../../../../../../backend/src/sro/application/runtime/answer_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_ANSWER`, [line 9](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L9): Constant

> The longest answer a run is handed, in characters. An answer is a choice,
> a value or a short "done it"; a mail reply carries its whole quoted thread,
> which is cut here rather than stored in the workflow's history.

## `AnswerRun.execute`, [line 27](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L27): Note

Code: `if not asking:`

> Nothing standing means the question was withdrawn (the step turned out
> done): the answer is passed on bare, with no value, so a workflow waiting
> on it carries on, and `RunSteps.answered` changes nothing. A password never
> rides a signal: the workflow's history is not a vault (Global Constraint
> 10); it is stored with `PUT /v1/secrets` and the answer is empty.
