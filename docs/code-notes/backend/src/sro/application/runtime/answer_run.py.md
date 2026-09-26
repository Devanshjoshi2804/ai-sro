# Notes for `backend/src/sro/application/runtime/answer_run.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/answer_run.py`](../../../../../../../backend/src/sro/application/runtime/answer_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_ANSWER`, [line 12](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L12): Constant

> The longest answer a run is handed, in characters. An answer is a choice,
> a value or a short "done it"; a mail reply carries its whole quoted thread,
> which is cut here rather than kept whole.

## `AnswerRun.execute`, [line 39](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L39): Note

Code: `if not asking or asking.get("id") != question_id:`

> Only the question standing now is answered. A question withdrawn under a
> waiting workflow (the step turned out done) is refused like any other; it
> is never run again, because the step has already moved on.
>
> Only a question for a value takes a value. A password is stored with
> `PUT /v1/secrets`, a one-time code is typed on the page, a step is answered
> by its verdict: no secret or free text is ever kept with the answer.
>
> A question about a write that was sent and never confirmed needs the
> operator's verdict. Without one the question stands and the write stays in
> doubt, never sent again.

## `AnswerRun.execute`, [line 62](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L62): Note

Code: `progress.asking = {**asking, **answer}`

> That the question was answered, and the verdict, are kept on the run's
> own question in one compare-and-set, so the first answer wins: a different
> second one is refused, the same one again is only signalled again (a retry
> after the signal failed). No answer text is kept anywhere: nothing reads a
> value yet, and a reply could carry a secret. The signal carries the
> question id and nothing else; the workflow's history is not a vault
> (Global Constraint 10), and `RunSteps.answered` reads the answer back
> from the run.

## `WriteVerdict`, [line 14](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L14): Constant

> The operator's word on a step the run asked about: `done` settles it,
> `not_done` says the write never happened so the lanes may try it again,
> and empty says nothing about it.

## `AnswerRun.execute`, [line 49](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L49): Note

Code: `if kind == "field" and chosen and chosen not in json.loads(asking.get("choices") or "[]"):`

> A field question takes one of the choices it offered (the form's labels, or
> the dropdown's options), or "" to leave the value out -- never free text. The
> choice is kept on the question, because it is one the page offered and so no
> secret; the signal still carries only the question id.
