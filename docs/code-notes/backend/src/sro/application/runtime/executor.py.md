# Notes for `backend/src/sro/application/runtime/executor.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/executor.py`](../../../../../../../backend/src/sro/application/runtime/executor.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `StepExecutor.run`, [line 43](../../../../../../../backend/src/sro/application/runtime/executor.py#L43): Note

> One step, down the ladder (spec §3): the tool lane alone for a mail
> send; otherwise the API lane when a verified replay can be planned,
> then UI, then sight when the step has a gesture to aim at. Lanes known
> broken for this step are skipped (`lanes_for` never skips the last
> rung). The walk stops at the first result that is not `failed`: a
> `done`, a `read`, or an `unknown` the operator must settle. A step
> that only reads the mail this run came from answers `read` with no
> lane at all: the mail is already in hand.

## `StepExecutor.run`, [line 79](../../../../../../../backend/src/sro/application/runtime/executor.py#L79): Note

Code: `if result.verdict == "unknown":`

> An `expired` result signs the account back in through
> `SessionBroker.reauth` and then retries that lane once, with
> `reauthed=True` so the API lane asks for headers the page sent after
> the sign-in. An `unknown` write is never sent again, by this lane or
> any other: the call may have arrived. It is settled only by the API
> lane's `read_back` (also with `reauthed=True`); a read-back that shows
> the values makes it `done`, anything else leaves it `unknown` and the
> operator is asked.

## `StepExecutor.run`, [line 84](../../../../../../../backend/src/sro/application/runtime/executor.py#L84): Note

Code: `if result.verdict != "failed" or result.expired:`

> A lane still `expired` after signing back in stops the walk rather
> than falling to the next lane: the session, not the step, is what is
> wrong, and every lower lane drives the same session. Walking on would
> spend each lane on the same refusal and mark lanes broken that are not.

## `StepExecutor.run`, [line 61](../../../../../../../backend/src/sro/application/runtime/executor.py#L61): Note

Code: `ladder = lanes_for(`

> A step with no mail send, no plannable replay and no gesture to aim at
> (it cites nothing, or only a scroll) has an empty ladder and answers
> `()`: the caller says no lane could act, rather than the activity dying.

## `StepExecutor.run`, [line 70](../../../../../../../backend/src/sro/application/runtime/executor.py#L70): Note

Code: `except (NeedsAPerson, AccountBusy, PageGone) as why:`

> Signing back in can need a person, find the account waiting for one
> (the run queues), or find the lease gone. The exception goes on to the
> caller as it is, since each has its own answer there, but it carries the
> lanes tried so far and this lane's own result, with why the sign-in
> stopped added to its reason: an `unknown` write stays `unknown` and a
> failure keeps its fingerprint for whoever learns from it.

## `StepExecutor.run`, [line 75](../../../../../../../backend/src/sro/application/runtime/executor.py#L75): Note

Code: `except Exception as why:`

> Any other failure while signing back in (the browser gone, a page that
> would not settle, a timeout) ends the walk with this lane's own result,
> still `expired` and with its verdict unchanged, so an `unknown` write is
> neither dropped nor sent again. Its reason names only the exception's
> class: the text may carry what the browser or the network said. An
> operator's stop and a cancellation still propagate.

## `StepExecutor.run`, [line 56](../../../../../../../backend/src/sro/application/runtime/executor.py#L56): Note

Code: `not tool and not ctx.adding.get(step.order) and replay_of(step, values, ctx) is not None`

> A write that follows a field this run filled (composed, or a learned field
> step) is never offered the API lane. The replay template is the recorded
> body, and it cannot carry the new key: replaying it would save the record
> without the field the operator asked for, and nothing would say so.
>
> **Ceiling.** Such a write always goes through the page. The upgrade is design
> 2's recipe compiler (K1): a learned key in the replay template, after which the
> API lane can carry it.
