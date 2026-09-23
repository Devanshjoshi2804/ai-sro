# Notes for `backend/src/sro/application/execution/run_secrets.py`

Why the code in [`backend/src/sro/application/execution/run_secrets.py`](../../../../../../../backend/src/sro/application/execution/run_secrets.py) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## `RunSecrets`, [line 11](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L11): Class

> One run's view of the vault: the password a step types, and the rule that
> the same stored password is never typed twice in one run.
>
> This is where production signs in (2026-09-23: the deployed tenant has no
> connections and signs in by running the mined login job). A step typed the
> stored password, the sign-in form came back, and rescue or sight rungs
> planned the step again -- each one typing the refused password once more.
> Now the second ask for a value this run already typed is answered with
> nothing, which stops the step on its existing needs_secret ask so the panel
> asks the operator, and the key is latched for every later run and for the
> keeper until somebody writes it again.

## `RunSecrets.__call__`, [line 19](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L19): Docstring

> The order is the rule. A value held for this run comes first and is typed
> regardless of any refusal: the operator is answering for this run. Then a
> standing refusal means nothing is handed out. Then the vault -- and a stored
> value this run already typed is refused and latched instead of handed out.
>
> "Already typed" compares the value, by a keyed hash kept only in memory, not
> the key: an operator who stores a new password while the run waits on its
> ask gets that one typed, because a different password is not a retry.
> Values are handed out several times without being typed -- a rung whose
> command missed the field typed nothing -- so handing out alone never counts.

## `RunSecrets.typed`, [line 49](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L49): Docstring

> Told by the run engine, after the browser reported a command done, what
> value it typed. Only a value this run handed out from the vault counts; a
> held value refused says nothing about what the vault keeps, so it is never
> latched.
