# Notes for `backend/src/sro/application/execution/run_secrets.py`

Why the code in [`backend/src/sro/application/execution/run_secrets.py`](../../../../../../../backend/src/sro/application/execution/run_secrets.py) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## `LATCH_AT`, [line 15](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L15): Constant

> Two failed attempts with no success between latch the password. One is
> forgiven because a single "form came back" can be a session that ended
> just after a good sign-in; a second in a row is not given that benefit, so
> a refused password is submitted at most twice -- under any IdP lockout
> threshold seen (fix round 5, 2026-09-23). Since task 10 (2026-09-24) the
> count for a vault password is kept in the vault (`FailedAttempts`), so the
> two are counted across runs, not per run.

## `RunSecrets`, [line 19](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L19): Class

> One run's view of the vault: the password a step types, and a count of the
> times the system refused it.
>
> This is where production signs in (2026-09-23: the deployed tenant has no
> connections and signs in by running the mined login job). A step typed the
> stored password, the sign-in form came back, and rescue or sight rungs
> planned the step again -- each one typing the refused password once more.
>
> Fix round 5 (2026-09-23) replaced page-signal inference with counting,
> because each inference rule was reproduced wrong (round 4 review): a click
> on a same-host error page ("Back to login") read as the run moving on and
> reset the bound -- five bad submits, nothing latched; and a stale doubt from
> an earlier landing latched a GOOD password when the form was merely seen at
> the next expiry. Now, per vault key:
>
> - an ATTEMPT is a submit (`pressed`) after this run typed that key;
> - it FAILED when a look on the host the password was typed on shows the
>   sign-in form with its password box empty -- counted once per attempt;
> - SUCCESS is a later step that is not part of signing in ending held
>   (`step_ended`), and resets the count; a page with no login box is never
>   success;
> - the count reaching `LATCH_AT` latches; a form seen with no attempt before
>   it counts for nothing.
>
> Task 10 (2026-09-24): for a vault password the count is the one in the
> vault (`<key>#failed`), so one bad submit in each of two runs latches. A
> held password is the operator answering for one run and is counted in the
> run only. If the vault will not answer, the run's own count decides.
>
> Task 10 fix round (2026-09-24), reviewer rulings:
>
> - **Success at run end.** A run of the sign-in job itself never holds a step
>   outside signing in, so held steps alone let a GOOD password latch across
>   two runs: the deployed Azure recording bounces once on Keycloak (first
>   Sign In stayed, retype and Enter landed), and each run added one. Now a key
>   whose last attempt LEFT the form's host (a look on another host, not
>   signed out -- the same leave-host evidence `sign_in_chain` trusts) and
>   did not see the form again before the run ended is a success, recorded by
>   `finished` when the run is over.
> - **The count is bound to the password it counted.** `#failed` holds the
>   count and a 12-hex fingerprint (`_mark`, keyed sha256, truncated); a
>   different fingerprint counts from zero. Before a vault refusal is written
>   the current vault value is read back, and a password changed since it
>   was handed out is not refused.
> - **Success is per system.** A key belongs to the hosts it was submitted on
>   and the first host its attempt landed on (`_homes`). A held step clears
>   only keys whose homes include the step's own origin (the engine passes
>   it; the last look's host when it does not).

## `RunSecrets.__call__`, [line 36](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L36): Docstring

> A value held for this run comes first and is typed regardless of any
> standing refusal: the operator is answering for this run. A fresh hold wins
> over the one kept earlier in the run (fix round 5): an operator who answers
> again mid-run is correcting the first answer. The value is kept for the run
> (`_kept`), so asking whether a password exists -- `_ask_for_the_password`
> does -- does not use up the operator's answer before the step types it. A
> held value this run saw refused is not handed out again. Then a standing
> refusal means nothing is handed out -- the step stops on its needs_secret
> ask and the panel asks for a new password. Then the vault, except a value
> this run latched, which is never typed again in this run even if the
> operator re-stores the same one.

## `RunSecrets.typed`, [line 60](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L60): Docstring

> A value the browser reported typing. If it is a password this run handed
> out, the key is armed on the host the form was on, and the current step is
> part of signing in.

## `RunSecrets.pressed`, [line 66](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L66): Docstring

> A submit. Every armed key becomes an attempt on its form's host and is
> disarmed; a vault key submitted this run is one a later success may clear
> in the vault, so later clicks -- an error page's "Back to login" -- are not new
> attempts and do not clear anything. Typing alone submits nothing.

## `RunSecrets.step_ended`, [line 77](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L77): Docstring

> The engine's verdict for a step. Held, outside a sign-in job, and this run
> neither typed nor submitted a password during it: the sign-in worked, so
> open attempts and failure counts are cleared. Anything else only closes the
> step.
>
> Task 10: the success clears, in the run and in the vault, only keys that
> sign into the held step's system (its origin, or the last look's host)
> and, in the vault, only keys this run submitted. A run that was handed the password but
> never submitted it proves nothing about it (its session was still alive),
> so its held steps leave another run's failed attempt standing. A key whose
> clear the vault refused is tried again at the next success.

## `RunSecrets.finished`, [line 88](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L88): Function

> Called by `StartWorkflowRun.perform` once the run is over (not when it
> crashed). Every key whose last attempt left its form and never saw the form
> again is a sign-in that worked; its vault count is cleared.

## `RunSecrets.saw`, [line 103](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L103): Docstring

> What the page showed. A page on another host that is not signed out marks
> each open attempt as having left its form (once; that host joins the key's
> homes). A signed-out page whose password box is empty, on the
> host an open attempt typed on, fails that attempt and undoes the leaving. Any other page decides
> nothing -- not a landing, not a refusal. A form still holding what was typed
> is a submit in flight. Hosts, never page text.

## `RunSecrets._refuse`, [line 132](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L132): Docstring

> Only a vault value is latched on its key; a held value refused says nothing
> about what the vault keeps. The vault value is read back first and must be
> the one this run submitted: a password stored in the meantime is not
> refused for the old one's attempts. A write landing between that read and
> the refusal can still be refused once; the operator's next write lifts it. Either way it is not typed again in this run.

## `WatchingChannel`, [line 154](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L154): Class

> The run's browser channel, read on the way through. What was typed, what
> was submitted and what every `ui.url` answer says about the page
> (`signed_out`, and from the extension `credential_empty` -- whether a visible
> login box is empty, never its value) are already in the conversation the run
> engine has, and every command kind that types a password -- `ui.perform`,
> `ui.perform_at`, the browser's own `sign_in` -- is covered in one place. Only
> replies the browser reported as done count. Step verdicts are not in the
> conversation, so the engine reports those itself (`step_ended`).
>
> A `ui.url` answer from a tab that is not the run's own (`elsewhere` with
> `elsewhere_is_ours` false: the operator's front tab) is ignored -- an
> unrelated page must not fail an attempt (review round 4).

## `_submits`, [line 195](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L195): Docstring

> A submit is a click, or Enter or NumpadEnter (task 10; a press with no key
> named defaults to Enter in the extension). Tab and other keys move focus or edit; counting them
> would turn filling a form into attempts (fix round 5).
