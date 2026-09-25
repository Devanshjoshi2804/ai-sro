# Notes for `backend/src/sro/application/runtime/step.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/step.py`](../../../../../../../backend/src/sro/application/runtime/step.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `WaitingForAPerson`, [line 38](../../../../../../../backend/src/sro/application/runtime/step.py#L38): Note

> A sign-in asked for a one-time code and its page is kept open for a
> person: a `NeedsAPerson` of kind `code` that also carries the `Held`
> (the WAITING lease and the tab showing the prompt), so D5 can say the
> question and later call `SessionBroker.resume` on that tab. Unlike every
> other `NeedsAPerson`, its tab must not be closed while the run waits.

## `LaneContext`, [line 65](../../../../../../../backend/src/sro/application/runtime/step.py#L65): Note

Code: `reauthed: bool = False`

> Set by the executor on the one retry after a lane answered `expired` and
> the broker signed in again. The API lane then asks the broker for fresh
> headers (a mark, a reload, then only requests after the mark): the page's
> request log still holds the token from before the sign-in, and replaying
> it would spend the only retry on a second refusal.
