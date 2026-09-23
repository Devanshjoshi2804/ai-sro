# Notes for `backend/src/sro/application/execution/one_time_secrets.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/one_time_secrets.py`](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L1): Docstring (debt)

> A password the operator gave for one run and nothing after it.
>
> The vault is for a credential somebody means to keep: stored once, reused by
> every run that signs into that system, rotated when it changes. What this
> holds is the other answer to the same question -- "here is my password, use it
> now, do not keep it" -- which an operator gives when they are signing into a
> system they do not own, or when policy says a credential does not live in a
> deployment's vault at all.
>
> So nothing here is written down. The value sits in this process's memory,
> is handed out exactly once, and is gone after that or after `K_HELD_FOR`,
> whichever comes first. A restart forgets it; so does a second run that arrives
> too late. Both are the honest failure: the step refuses with the key it
> wanted, which is the same sentence an operator gets when they never gave one.
>
> Not per run, deliberately. The step that asks for a password has already
> failed, and the retry the operator presses is a NEW run with a new id -- a
> hold keyed by the run that asked would be a hold nothing could ever read.
>
> ponytail: process memory, because the deployment serves this from one uvicorn
> worker (`backend/Dockerfile`). The day the api runs more than one, this has to
> move to something the processes share -- with the same two rules, once and
> briefly -- or an operator will type a password into one process and have the
> run ask again from another.

## module, [line 6](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L6): Note on the line above

Code: `K_HELD_FOR = 15 * 60.0`

> How long a one-time password waits for the run that will type it.
>
> Long enough for somebody to answer the card, press the retry and watch the
> sign-in happen; short enough that a password nobody used is not still in
> memory at the end of a shift. It is not a session: a run that has not asked
> for it in a quarter of an hour is a run nobody is watching.

## `hold`, [line 18](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L18): Docstring

> Keep one value for the next run that asks for this key.
>
> Answers when it will be forgotten, which is what the caller tells the
> operator. Holding the same key twice replaces the first: somebody who
> typed it again meant the second one.

## `take`, [line 25](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L25): Docstring

> The value, once. A second read gets nothing, and neither does a read
> after it has aged out -- both are `None`, which the runner already knows
> how to say out loud.

## `waiting`, [line 35](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L35): Docstring

> Whether a value is held for this key, without taking it. For tests and
> for nothing that runs a step: reading a secret is `take`.

## `forget_everything`, [line 41](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L41): Docstring

> Drop every held value. For tests, and for a deployment that wants to
> clear them without a restart.
