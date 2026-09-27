# Notes for `backend/src/sro/application/runtime/executor.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/executor.py`](../../../../../../../backend/src/sro/application/runtime/executor.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `StepExecutor.run`, [line 44](../../../../../../../backend/src/sro/application/runtime/executor.py#L44): Note

> One step, down the ladder (spec §3): the tool lane alone for a mail
> send; otherwise the API lane when a verified replay can be planned,
> then UI, then sight when the step has a gesture to aim at. Lanes known
> broken for this step are skipped (`lanes_for` never skips the last
> rung). The walk stops at the first result that is not `failed`: a
> `done`, a `read`, or an `unknown` the operator must settle. A step
> that only reads the mail this run came from answers `read` with no
> lane at all: the mail is already in hand.

## `StepExecutor.run`, [line 83](../../../../../../../backend/src/sro/application/runtime/executor.py#L83): Note

Code: `if result.verdict == "unknown":`

> An `expired` result signs the account back in through
> `SessionBroker.reauth` and then retries that lane once, with
> `reauthed=True` so the API lane asks for headers the page sent after
> the sign-in. An `unknown` write is never sent again, by this lane or
> any other: the call may have arrived. It is settled only by the API
> lane's `read_back` (also with `reauthed=True`); a read-back that shows
> the values makes it `done`, anything else leaves it `unknown` and the
> operator is asked.

## `StepExecutor.run`, [line 88](../../../../../../../backend/src/sro/application/runtime/executor.py#L88): Note

Code: `if result.verdict != "failed" or result.expired:`

> A lane still `expired` after signing back in stops the walk rather
> than falling to the next lane: the session, not the step, is what is
> wrong, and every lower lane drives the same session. Walking on would
> spend each lane on the same refusal and mark lanes broken that are not.

## `StepExecutor.run`, [line 65](../../../../../../../backend/src/sro/application/runtime/executor.py#L65): Note

Code: `ladder = lanes_for(`

> A step with no mail send, no plannable replay and no gesture to aim at
> (it cites nothing, or only a scroll) has an empty ladder and answers
> `()`: the caller says no lane could act, rather than the activity dying.

## `StepExecutor.run`, [line 74](../../../../../../../backend/src/sro/application/runtime/executor.py#L74): Note

Code: `except (NeedsAPerson, AccountBusy, PageGone) as why:`

> Signing back in can need a person, find the account waiting for one
> (the run queues), or find the lease gone. The exception goes on to the
> caller as it is, since each has its own answer there, but it carries the
> lanes tried so far and this lane's own result, with why the sign-in
> stopped added to its reason: an `unknown` write stays `unknown` and a
> failure keeps its fingerprint for whoever learns from it.

## `StepExecutor.run`, [line 79](../../../../../../../backend/src/sro/application/runtime/executor.py#L79): Note

Code: `except Exception as why:`

> Any other failure while signing back in (the browser gone, a page that
> would not settle, a timeout) ends the walk with this lane's own result,
> still `expired` and with its verdict unchanged, so an `unknown` write is
> neither dropped nor sent again. Its reason names only the exception's
> class: the text may carry what the browser or the network said. An
> operator's stop and a cancellation still propagate.

## `StepExecutor.run`, [line 59](../../../../../../../backend/src/sro/application/runtime/executor.py#L59): Note

Code: `set(adding.fresh) <= known <= set(learned_slots(ctx.workflow, step))`

> A write that follows a field this run filled is offered the API lane only
> when every added field was learned with a slot (`learned_slots`, K1): the
> replay template then carries the learned key, and the read-back checks it.
> `adding.fresh` is not "composed this run": `_fill_for` puts every filled
> field's held value there, learned ones included, and names a learned field
> in `adding.known` too. A field is composed this run when it is in `fresh`
> and not in `known`. A field composed this run has no learned key, and a learned
> field whose slot was taken out after an API break has none the template may
> use; either way the recorded body cannot carry it, and replaying it would
> save the record without the field the operator asked for, and nothing would
> say so -- so that write goes through the page.

## `StepExecutor._settled`, [line 108](../../../../../../../backend/src/sro/application/runtime/executor.py#L108): Note

Code: `keyed=confirmed_keys(step, values, ctx),`

> An in-doubt write the API lane's read-back settled as done keys its learned
> fields the same way the API lane's own write does (`confirmed_keys`): the
> read-back checked every value the plan confirms, the learned slots' values
> among them.
