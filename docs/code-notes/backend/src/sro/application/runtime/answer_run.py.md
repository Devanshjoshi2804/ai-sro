# Notes for `backend/src/sro/application/runtime/answer_run.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/answer_run.py`](../../../../../../../backend/src/sro/application/runtime/answer_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_ANSWER`, [line 11](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L11): Constant

> The longest answer a run is handed, in characters. An answer is a choice,
> a value or a short "done it"; a mail reply carries its whole quoted thread,
> which is cut here rather than stored in the workflow's history.

## `AnswerRun.execute`, [line 38](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L38): Note

Code: `if not asking:`

> Nothing standing means the question was withdrawn (the step turned out
> done): the answer is passed on bare, with no value, so a workflow waiting
> on it carries on, and `RunSteps.answered` changes nothing. A secret never
> rides a signal: the workflow's history is not a vault (Global Constraint
> 10). A password is stored with `PUT /v1/secrets` and a one-time code is
> typed on the page; either answer is empty.
>
> A question about a write that was sent and never confirmed needs the
> operator's verdict. Without one nothing is signalled: the question stands
> and the write stays in doubt, never sent again.

## `WriteVerdict`, [line 13](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L13): Constant

> The operator's word on a step the run asked about: `done` settles it,
> `not_done` says the write never happened so the lanes may try it again,
> and empty says nothing about it.
