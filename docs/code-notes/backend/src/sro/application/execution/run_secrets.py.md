# Notes for `backend/src/sro/application/execution/run_secrets.py`

Why the code in [`backend/src/sro/application/execution/run_secrets.py`](../../../../../../../backend/src/sro/application/execution/run_secrets.py) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## `RunSecrets`, [line 17](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L17): Class

> One run's view of the vault: the password a step types, and the evidence
> that the system refused it.
>
> This is where production signs in (2026-09-23: the deployed tenant has no
> connections and signs in by running the mined login job). A step typed the
> stored password, the sign-in form came back, and rescue or sight rungs
> planned the step again -- each one typing the refused password once more.
>
> "Refused" is decided by evidence, the rule the server-side driver uses: the
> password was typed, and the same host then shows its sign-in form again with
> the password box EMPTY (review round 3, 2026-09-23). Round 2 inferred it from
> the same value being asked for twice, which would have latched a correct
> password on an ordinary re-login after the session expired mid-run.

## `RunSecrets.__call__`, [line 27](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L27): Docstring

> A value held for this run comes first and is typed regardless of any
> refusal: the operator is answering for this run. Then a standing refusal
> means nothing is handed out -- the step stops on its needs_secret ask and the
> panel asks for a new password. Then the vault, except a value this run has
> already seen refused, which is never typed again in this run even if the
> operator re-stores the same one.

## `RunSecrets.typed`, [line 48](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L48): Docstring

> A value the browser reported typing. If it is a password this run handed
> out, the run now waits for the verdict, remembering the host the form was
> on.

## `RunSecrets.saw`, [line 53](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L53): Docstring

> What the page showed next. Same host, password box on screen and empty:
> refused. Any other host with no password box: the browser landed, and a
> sign-in form after that is a session ending, not a refusal -- the password
> is typed again. A form still holding what was typed is a submit in flight
> and decides nothing. Hosts, never page text.

## `RunSecrets._refuse`, [line 65](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L65): Docstring

> Only a vault value is latched on its key; a held value refused says nothing
> about what the vault keeps. Either way it is not typed again in this run.

## `WatchingChannel`, [line 83](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L83): Class

> The run's browser channel, read on the way through. Both facts the refusal
> rule needs are already in the conversation the run engine has: what a
> performed command typed, and what every `ui.url` answer says about the page
> (`signed_out`, and from the extension `credential_empty` -- whether a visible
> login box is empty, never its value). Watching here means the 2,000-line
> engine needed no new hook, and every command kind that types a password --
> `ui.perform`, `ui.perform_at`, the browser's own `sign_in` -- is covered in
> one place. Only replies the browser reported as done count.
