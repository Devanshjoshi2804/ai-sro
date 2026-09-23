# Notes for `backend/src/sro/interface/http/v1/routers/ask.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/ask.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/ask.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `ask`, [line 38](../../../../../../../../../backend/src/sro/interface/http/v1/routers/ask.py#L38): Comment

Code: `await container.record_attempt().execute(`

> The door the panel's own box actually posts to.
>
> `/v1/chat` was instrumented first and the panel never calls it:
> measured on the deployment 2026-09-20, an operator typed two
> sentences into the panel and the attempts table stayed empty, because
> every one of them came through here. A record of what somebody asked
> for is worth nothing if it is kept at the door they did not use.
>
> The sentence itself is not recorded, here or anywhere: `ChatReading`
> has no column for an operator's words about their own warehouse.

## `ask`, [line 49](../../../../../../../../../backend/src/sro/interface/http/v1/routers/ask.py#L49): Comment

Code: `await container.record_attempt().execute(`

> A question this system cannot yet answer -- it has no plan it is
> ready to run -- which from the person asking is a question that got
> nothing back.
