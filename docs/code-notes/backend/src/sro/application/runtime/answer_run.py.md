# Notes for `backend/src/sro/application/runtime/answer_run.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/answer_run.py`](../../../../../../../backend/src/sro/application/runtime/answer_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_ANSWER`, [line 14](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L14): Constant

> The longest answer a run is handed, in characters. An answer is a choice,
> a value or a short "done it"; a mail reply carries its whole quoted thread,
> which is cut here rather than kept whole.

## `AnswerRun.execute`, [line 50](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L50): Note

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

## `AnswerRun.execute`, [line 79](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L79): Note

Code: `progress.asking = {**asking, **answer}`

> That the question was answered, and the verdict, are kept on the run's
> own question in one compare-and-set, so the first answer wins: a different
> second one is refused, the same one again is only signalled again (a retry
> after the signal failed). No answer text is kept anywhere: nothing reads a
> value yet, and a reply could carry a secret. The signal carries the
> question id and nothing else; the workflow's history is not a vault
> (Global Constraint 10), and `RunSteps.answered` reads the answer back
> from the run.

## `WriteVerdict`, [line 16](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L16): Constant

> The operator's word on a step the run asked about: `done` settles it,
> `not_done` says the write never happened so the lanes may try it again,
> and empty says nothing about it.

## `AnswerRun.execute`, [line 61](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L61): Note

Code: `if kind == "field" and chosen and chosen not in json.loads(asking.get("choices") or "[]"):`

> A field question takes one of the choices it offered (the form's labels, or
> the dropdown's options), or "" to leave the value out -- never free text. The
> choice is kept on the question, because it is one the page offered and so no
> secret; the signal still carries only the question id.

## `AnswerRun.execute`, [line 52](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L52): Comment

Code: `if kind == "recipient" and run.started_by and run.started_by != ctx.principal_id.value:`

> Who a mail goes to is the one answer that names somebody outside the evidence,
> so only the operator who started the run gives it (invariant 5), and only as
> addresses that read cleanly (`mailboxes`) -- the same parser the draft's own
> recipients go through. The answer keeps the addresses and who gave them; the
> first answer wins, as for every question.

## `AnswerRun.execute`, [line 47](../../../../../../../backend/src/sro/application/runtime/answer_run.py#L47): Comment

Code: `drafted = run.executor != "steel" and kind == "recipient"`

> A drafted (non-Steel) mail job asks who its mail goes to from a stopped run --
> it holds no browser while it waits -- so that one question is answered on a
> stopped run, and carried out by `resume` (the job redrafted) instead of a
> Temporal signal, which no workflow would receive.
