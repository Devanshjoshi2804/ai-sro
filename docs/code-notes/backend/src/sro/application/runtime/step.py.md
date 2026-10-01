# Notes for `backend/src/sro/application/runtime/step.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/step.py`](../../../../../../../backend/src/sro/application/runtime/step.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `WaitingForAPerson`, [line 47](../../../../../../../backend/src/sro/application/runtime/step.py#L47): Note

> A sign-in asked for a one-time code and its page is kept open for a
> person: a `NeedsAPerson` of kind `code` that also carries the `Held`
> (the WAITING lease and the tab showing the prompt), so D5 can say the
> question and later call `SessionBroker.resume` on that tab. Unlike every
> other `NeedsAPerson`, its tab must not be closed while the run waits.

## `LaneContext`, [line 79](../../../../../../../backend/src/sro/application/runtime/step.py#L79): Note

Code: `reauthed: bool = False`

> Set by the executor on the one retry after a lane answered `expired` and
> the broker signed in again. The API lane then asks the broker for fresh
> headers (a mark, a reload, then only requests after the mark): the page's
> request log still holds the token from before the sign-in, and replaying
> it would spend the only retry on a second refusal.

## `ReadsBack`, [line 121](../../../../../../../backend/src/sro/application/runtime/step.py#L121): Note

> The API lane as the executor needs it: a lane that can also say whether
> a read-back shows an `unknown` write's values, without sending the
> write again.

## `Superseded`, [line 57](../../../../../../../backend/src/sro/application/runtime/step.py#L57): Note

Code: `class Superseded(Stopped):`

> Another attempt holds the run (`progress` moved on since this one loaded
> it). A `Stopped` so every lane lets it through untouched, but never
> recorded as a stop and never barred from retry: the loser acts no further.

## `LaneContext`, [line 78](../../../../../../../backend/src/sro/application/runtime/step.py#L78): Note

Code: `about_to_write: Callable[[Lane], Awaitable[None]] = _nothing`

> Each lane names itself as it marks a write, so the mark says which lane
> sent it.

## `LaneContext`, [line 77](../../../../../../../backend/src/sro/application/runtime/step.py#L77): Note

Code: `request: tuple[str, ...] = ()`

> What the run's starter typed for it in their own panel thread
> (`the_operator_s_words`) and their answers to its `mail_body` question
> (`Progress.told`), read by `RunSteps` for a step that sends mail only: the
> tool lane hands it to the mail writer as the operator's trusted request (S4).
> Empty for a run the mail door started, and for every other step.
