# Notes for `backend/src/sro/application/runtime/step.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/step.py`](../../../../../../../backend/src/sro/application/runtime/step.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `WaitingForAPerson`, [line 39](../../../../../../../backend/src/sro/application/runtime/step.py#L39): Note

> A sign-in asked for a one-time code and its page is kept open for a
> person: a `NeedsAPerson` of kind `code` that also carries the `Held`
> (the WAITING lease and the tab showing the prompt), so D5 can say the
> question and later call `SessionBroker.resume` on that tab. Unlike every
> other `NeedsAPerson`, its tab must not be closed while the run waits.
