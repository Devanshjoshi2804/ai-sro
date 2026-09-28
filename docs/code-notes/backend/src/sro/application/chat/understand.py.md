# Notes for `backend/src/sro/application/chat/understand.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/understand.py`](../../../../../../../backend/src/sro/application/chat/understand.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/understand.py#L1): Docstring

> The chat door. Saying it offers the work; pressing start authorises it.
>
> The model reads the utterance against a few of this tenant's jobs, ranked in
> code, and answers which one, with which values, and what is still missing. Nothing
> performs from here: the answer is an offer the form renders, and starting a run
> is the press.
>
> Ported from `new_agent_arch/src/rig/entry.py`, plus the half of the rig's
> `/v1/chat` route that writes the bill down. The words and the response schema
> are `sro.domain.chat.reading`; this is the half that asks.
>
> The day's cap is the route's, not this module's: the rig answered 429 before it
> reached `understand`, and a cap checked after the call is a cap that has
> already paid for the call it stops.

## `Understood`, [line 28](../../../../../../../backend/src/sro/application/chat/understand.py#L28): Docstring

> What one sentence came to, and what reading it cost.
>
> `answer` has no default and is never None: every way out of `understand`
> -- named a job, named one nobody holds, or came back with nothing at all --
> went through the model and has to be billed for. A reading the caller
> cannot bill is a model call nobody can defend at the end of the month.

## `Understood`, [line 33](../../../../../../../backend/src/sro/application/chat/understand.py#L33): Note on the line above

Code: `sure: bool = True`

> Whether the sentence plainly named ONE of this tenant's jobs.
>
> `True` by default so a reading built by anything that predates this -- a
> test, an older row -- reads as it always did. What `False` means is the
> caller's: the panel asks a person which job was meant rather than pressing
> on, because a guess that creates one wrong record is a nuisance and the
> same guess against a list of twenty is twenty wrong records.

## `Understood`, [line 35](../../../../../../../backend/src/sro/application/chat/understand.py#L35): Note on the line above

Code: `also: list[str] = field(default_factory=list)`

> The other jobs it nearly said, ids only, for the question a person is
> asked. Filtered to jobs this tenant actually holds, like `workflow_id`.

## `Understood`, [line 37](../../../../../../../backend/src/sro/application/chat/understand.py#L37): Note on the line above

Code: `items: list[dict[str, str]] = field(default_factory=list)`

> The things this job is to be done for, where the operator named several.
>
> Empty for one thing, which is most sentences -- and a job run for one item
> performs exactly as a job run for none, so a caller that ignores this is
> not wrong, only limited to the first thing somebody asked for.

## `Understood`, [line 39](../../../../../../../backend/src/sro/application/chat/understand.py#L39): Note on the line above

Code: `aside: dict[str, str] = field(default_factory=dict)`

> What those fields were given, kept beside their names.
>
> A form posts far more fields than a job varies, so where the dictionary
> names the slot the write can fill it after all -- and it cannot fill a
> value this threw away. Set aside rather than in `values`, because `values`
> is what the job itself declares and this is not that.

## `Understood`, [line 41](../../../../../../../backend/src/sro/application/chat/understand.py#L41): Note on the line above

Code: `unasked: list[str] = field(default_factory=list)`

> What the request asked for that this job has no parameter for.
>
> Dropped from `values`, which is right -- a key the workflow never declared
> is a value nothing asked for. Named here because the silence was the fault:
> a job's parameters are what two doings proved VARY and the form has far
> more fields than that, so `code GV3, description X, Department Inbound` is
> a reasonable request answered by a record with no Department in it and
> nothing anywhere saying so.
>
> The run already says this after the press. Nobody can consent to a write
> they cannot see, and after the press is after the record.

## `read_utterance`, [line 144](../../../../../../../backend/src/sro/application/chat/understand.py#L144): Docstring

> One sentence, read against this tenant's jobs, with the bill written down.
>
> The bill, and not the sentence: there is no column for an operator's words
> about their own warehouse, and the row exists for the cap and the spend
> line, neither of which needs them.
>
> A row is written on every reading, a refusal included -- that is the case
> that matters, because it is then the only record left of a call that cost
> money and returned nothing. `now` is the caller's clock rather than one
> read here, so a test can move it.

## `read_utterance`, [line 152](../../../../../../../backend/src/sro/application/chat/understand.py#L152): Comment

Code: `facts = await job_facts(uow, tenant_id, await uow.workflows.known(tenant_id), now=now)`

> The facts are loaded once, for every job, runnable or not: a request for a
> job that cannot run is still that job (C1's ruling), and is answered with
> its reasons (`Understood.cannot_run`) rather than read as asking for
> nothing. The ranking and the `asked_by` mails are read off these same
> facts, before the model call. The sign-in names come from `logins_of`,
> which reads the sign-in jobs' landing evidence the facts do not carry.

## `read_utterance`, [line 171](../../../../../../../backend/src/sro/application/chat/understand.py#L171): Comment

Code: `workflow_id=got.workflow_id,`

> What the offer came to, which is None when the model named a job
> nobody holds. The sentence it read is not here and has nowhere to
> go: `ChatReading` has no field for it.

## `understand`, [line 66](../../../../../../../backend/src/sro/application/chat/understand.py#L66): Docstring

> R1's reader: one model call over the whole request (a mail thread or a
> chat sentence), a few candidate jobs ranked in code, and the standing
> question when one is open (trusted JSON; the request and the candidates
> are untrusted fences). What it answers is not trusted either: every value
> passes `domain.chat.request.read_of` before it becomes a value (GC 10).
> No candidates is a reading of nothing: no model is asked, and the answer
> carries empty data rather than None, so the mail door does not take it
> for a model failure and release the mail to be read again forever.

## `understand`, [line 78](../../../../../../../backend/src/sro/application/chat/understand.py#L78): Comment

Code: `[shown(one) for one in candidates], indent=2, ensure_ascii=False`

> The redaction marker is «redacted», and the default ensure_ascii
> writes it into the prompt as \u00abredacted\u00bb -- a form
> nothing else in this system uses. Every json.dumps on a path to a
> prompt or to the store says so.

## `shown`, [line 48](../../../../../../../backend/src/sro/application/chat/understand.py#L48): Docstring

> What the reader sees of a candidate: each field's name, the labels the
> screen shows, the operator's aliases for it, the values seen in it, and
> whether the job ever filled it. `asked_by` is left out, never sent empty,
> when no mail asked for the job: an empty list reads as "nobody mails for
> this", a claim about history rather than about the job. The eval suite
> builds its cases from this same form.

## `read_request`, [line 99](../../../../../../../backend/src/sro/application/chat/understand.py#L99): Docstring

> The one way a request is read, for the chat door and the mail door alike.
> A request that names a sign-in chore more than any work job is answered
> with `K_A_CHORE` as a note, and no model is asked: sign-in is the session
> broker's work (amendment 2, item 5). Otherwise the ranked, de-duplicated
> candidates carry the tenant's recorded logins (`logins_of`), which are
> never a job value. The caller passes them: the mail door reads them once
> per look.

## `held_runs`, [line 118](../../../../../../../backend/src/sro/application/chat/understand.py#L118): Docstring

> Held runs per job, from the run tallies: the second key of the canonical
> copy among duplicate titles, after the number of parameters.

## `offer_check`, [line 122](../../../../../../../backend/src/sro/application/chat/understand.py#L122): Docstring

> C1's follow-up (amendment 2, item 6): the request's values reach the
> compile check, so a value for a field gone from its form (`field_gone`)
> is said when the job is offered, not when it starts. Each item is checked
> with its own values over the shared ones, as `read_of` supplies them
> (R1 review, M11): merged into one dict, the last item's values hid the
> others'. The first item that cannot run answers for the offer. With no values the
> facts already loaded are the answer, so a valueless reading costs no
> second compile. It runs in its own unit of work in the mail door: no
> session is held across the model call.

## `read_request`, [line 99](../../../../../../backend/src/sro/application/chat/understand.py#L99): Note

> `also` are candidates beside the ranked jobs, never ranked or cut by
> `K_CANDIDATES`. The chat door passes the built-in mail actions (M4); the mail
> door passes none, so a mail is never offered a reply of its own.
>
> A request that is exactly a ranked job's title (`normal`) is that job, sure,
> and no model is asked (J1): typing a title back to "Did you mean X or Y?"
> used to be read again and asked again. Only ranked learned jobs are picked
> this way; a built-in has no fields to say what it still needs.

## `read_utterance`, [line 144](../../../../../../backend/src/sro/application/chat/understand.py#L144): Note

> The chat door: the built-in mail actions are always candidates, so "send an
> email to ..." reaches one even for a tenant with no mined job -- and such a
> tenant is now read, not answered "nothing holds this" without a model.
