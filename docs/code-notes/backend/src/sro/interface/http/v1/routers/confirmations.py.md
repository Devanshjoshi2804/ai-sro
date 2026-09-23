# Notes for `backend/src/sro/interface/http/v1/routers/confirmations.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/confirmations.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/confirmations.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `list_confirmations`, [line 38](../../../../../../../../../backend/src/sro/interface/http/v1/routers/confirmations.py#L38): Comment

Code: `if titles is None:`

> The tenant's jobs, once, rather than a read per card: there is no
> single-workflow use case and a card list is short. `titles` is
> built lazily so a queue with no job cards makes no extra read.

## `list_confirmations`, [line 46](../../../../../../../../../backend/src/sro/interface/http/v1/routers/confirmations.py#L46): Comment

Code: `skill_name=titles.get(confirmation.workflow_id, confirmation.workflow_id),`

> A job that has since been re-mined away still has a card
> somebody has to answer, and an id is better on it than a
> blank.

## `approve`, [line 66](../../../../../../../../../backend/src/sro/interface/http/v1/routers/confirmations.py#L66): Comment

Code: `await container.record_attempt().execute(`

> An approval that starts nothing is the shape this records. The card is
> answered either way -- the row for it exists -- and whether a run came
> out of the yes is the thing nobody could see afterwards.

## `decline`, [line 92](../../../../../../../../../backend/src/sro/interface/http/v1/routers/confirmations.py#L92): Comment

Code: `await container.record_attempt().execute(`

> A person saying no is not a refusal BY this system, so it is `done`: they
> asked to decline and they declined. What `refused` would mean here is
> that the decline itself was turned down, which is a different sentence.
