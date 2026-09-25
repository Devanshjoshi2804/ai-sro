# Notes for `backend/src/sro/application/runtime/executor.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/executor.py`](../../../../../../../backend/src/sro/application/runtime/executor.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `StepExecutor.run`, [line 35](../../../../../../../backend/src/sro/application/runtime/executor.py#L35): Note

> One step, down the ladder (spec §3): the tool lane alone for a mail
> send; otherwise the API lane when a verified replay can be planned,
> then UI, then sight when the step has a gesture to aim at. Lanes known
> broken for this step are skipped (`lanes_for` never skips the last
> rung). The walk stops at the first result that is not `failed`: a
> `done`, a `read`, or an `unknown` the operator must settle. A step
> that only reads the mail this run came from answers `read` with no
> lane at all: the mail is already in hand.

## `StepExecutor.run`, [line 55](../../../../../../../backend/src/sro/application/runtime/executor.py#L55): Note

Code: `if result.verdict == "unknown":`

> An `expired` result signs the account back in through
> `SessionBroker.reauth` and then retries that lane once, with
> `reauthed=True` so the API lane asks for headers the page sent after
> the sign-in. An `unknown` write is never sent again, by this lane or
> any other: the call may have arrived. It is settled only by the API
> lane's `read_back` (also with `reauthed=True`); a read-back that shows
> the values makes it `done`, anything else leaves it `unknown` and the
> operator is asked.

## `StepExecutor.run`, [line 60](../../../../../../../backend/src/sro/application/runtime/executor.py#L60): Note

Code: `if result.verdict != "failed" or result.expired:`

> A lane still `expired` after signing back in stops the walk rather
> than falling to the next lane: the session, not the step, is what is
> wrong, and every lower lane drives the same session. Walking on would
> spend each lane on the same refusal and mark lanes broken that are not.
