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
> is handed to exactly the run it was given for and nothing else, and is gone
> after that or after `K_HELD_FOR`, whichever comes first. A restart forgets
> it; so does a second run that arrives too late. Both are the honest failure:
> the step refuses with the key it wanted, which is the same sentence an
> operator gets when they never gave one.
>
> **Bound to the run it was given for, and this is the whole of what the run
> id buys.** An operator watching a step refuse and typing a password into the
> card is answering about the run in front of them -- the run whose id the
> panel already carries, from the same card. Without the binding, any run of
> the tenant that asked next would be handed a password a different operator,
> for a different job, had lent to a different run: the retry an operator
> presses after a refusal is a NEW run with a new id, and a hold keyed only by
> system and field would answer it too, along with every other run racing to
> ask first.
>
> Not per key alone, and not per run alone: `hold` and `take` both take the
> key AND the run id, because a key names WHICH secret and the run id names
> WHO may read it back. `take` for the wrong run answers `None` without
> removing the hold -- a run that was never given a password does not get to
> spend the one chance the run that was given it still has.
>
> **Two runs holding for the same key at once do not collide.** Runs execute
> in parallel, so two runs needing the same system's password at the same
> moment is ordinary, not a race -- the store is keyed by `(key, run_id)`
> together, not by `key` alone with the run id checked afterwards, so the
> second run's `hold` cannot overwrite the first's before either has taken.
> Measured the wrong way once: a version keyed by `key` alone let the second
> of two concurrent `hold`s silently erase the first, so the run that asked
> first lost its password to the run that asked second.
>
> One store, constructed once and handed down from `Container`, in place of
> the module dict this used to be: a use case built once per process must not
> keep its own private copy of what every run shares, the same reason `Stops`
> and `Approvals` are built once and injected rather than imported.
>
> ponytail: process memory, because the deployment serves this from one uvicorn
> worker (`backend/Dockerfile`). The day the api runs more than one, this has to
> move to something the processes share -- with the same rules, once, briefly,
> and bound to the run that asked -- or an operator will type a password into
> one process and have the run ask again from another.

## module, [line 6](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L6): Note on the line above

Code: `K_HELD_FOR = 15 * 60.0`

> How long a one-time password waits for the run that will type it.
>
> Long enough for somebody to answer the card, press the retry and watch the
> sign-in happen; short enough that a password nobody used is not still in
> memory at the end of a shift. It is not a session: a run that has not asked
> for it in a quarter of an hour is a run nobody is watching.

## `OneTimeSecrets`, [line 15](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L15): Docstring (debt)

> The store itself, one per process and handed down from `Container` --
> `container.one_time_secrets`, built once beside `Stops` and `Approvals` and
> passed into `StartWorkflowRun` and the `/v1/secrets/once` route, rather than
> the module-level dict this used to be. A class, and not because anything
> here is polymorphic: it is state a container can construct once and inject,
> which a module-level dict cannot be handed down as, only imported -- and an
> imported dict is a dict every test and every future second worker shares
> whether it means to or not.

## `OneTimeSecrets.hold`, [line 19](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L19): Docstring

> Keep one value for the run it was given to, and the run it was given to
> alone.
>
> Answers when it will be forgotten, which is what the caller tells the
> operator. Holding the same key twice FOR THE SAME RUN replaces the first:
> somebody who typed it again meant the second one -- they mistyped, which is
> why they are typing it again, and the operator is still answering about the
> one run in front of them. Holding the same key for a DIFFERENT run does not
> replace anything: it is stored under its own `(key, run_id)` and sits
> beside the first run's hold rather than on top of it, which is what lets
> two runs racing for the same system's password each keep the one they were
> given.
>
> Sweeps expired entries first, on every hold and not only on every take: a
> key nobody ever came back to take must not sit in memory past its quarter
> of an hour just because nothing happened to read it.

## `OneTimeSecrets.take`, [line 26](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L26): Docstring

> The value, once, and only to the run it was held for. A read from any
> other run is a lookup on a `(key, run_id)` pair that was never held --
> nothing to find and nothing to disturb, so the run that was actually given
> the password may still ask, undisturbed by every other run that asked
> first. A second read from the right run gets nothing either, and neither
> does a read after it has aged out -- all three are `None`, which the
> runner already knows how to say out loud.
>
> Sweeps expired entries first, for `hold`'s reason: a stale key some other
> run's mistaken ask stumbles into must answer `None` for having aged out,
> not for merely naming the wrong run.

## `OneTimeSecrets.waiting`, [line 32](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L32): Docstring

> Whether a value is held for this key AND this run, without taking it. Runs
> the same `(key, run_id)` pair `take` does, for the same reason: two runs
> can each be waiting on their own hold of the same key, and asking without
> the run id would not say which one. For tests and for nothing that runs a
> step: reading a secret is `take`.

## `OneTimeSecrets.forget_everything`, [line 37](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L37): Docstring

> Drop every held value. For tests, and for a deployment that wants to
> clear them without a restart.

## `OneTimeSecrets._sweep`, [line 40](../../../../../../../backend/src/sro/application/execution/one_time_secrets.py#L40): Docstring

> Drop every hold that aged out, on every `hold` and every `take` rather than
> on a timer: nothing here runs a background loop, so the only moments this
> process is guaranteed to touch the store are the ones a caller already
> reached it on. A key that ages out between two of those moments sits in
> memory a little longer than `K_HELD_FOR` and no longer than the gap between
> them -- which is bounded by how often runs actually ask, the same bound an
> explicit sweep loop would be answering to.
