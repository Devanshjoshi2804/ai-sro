# Notes for `backend/src/sro/application/execution/run_secrets.py`

Why the code in [`backend/src/sro/application/execution/run_secrets.py`](../../../../../../../backend/src/sro/application/execution/run_secrets.py) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## `RunSecrets`, [line 18](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L18): Class

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
>
> Review round 4 (2026-09-23) tightened both halves. A refusal now also needs
> an observed submit after the typing (`pressed`), and landing is any page with
> no login box, on any host -- a login form on the system's own host used to
> latch every later re-login. Accepted trade-off: a spinner with no login box
> between the submit and the refused form looks like a landing and buys one
> more try; the second is not given that benefit (`_unsure`), so a refused
> password is submitted at most twice in a run.

## `RunSecrets.__call__`, [line 31](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L31): Docstring

> A value held for this run comes first and is typed regardless of any
> standing refusal: the operator is answering for this run. It is taken from
> `OneTimeSecrets` once and kept for the run (`_kept`), so asking whether a
> password exists -- `_ask_for_the_password` does -- no longer uses up the
> operator's answer before the step types it (review round 4). A held value
> this run saw refused is not handed out again. Then a standing refusal
> means nothing is handed out -- the step stops on its needs_secret ask and the
> panel asks for a new password. Then the vault, except a value this run has
> already seen refused, which is never typed again in this run even if the
> operator re-stores the same one.

## `RunSecrets.typed`, [line 55](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L55): Docstring

> A value the browser reported typing. If it is a password this run handed
> out, the run now waits for the verdict, remembering the host the form was
> on, and that nothing has been submitted yet.

## `RunSecrets.pressed`, [line 60](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L60): Docstring

> A click or key press the browser performed: a submit of whatever was typed
> before it. Typing alone submits nothing, so an empty form after a value went
> into the wrong box is not a refusal (review round 4). Performed while the
> page had no login box, it is the run moving on in the system: that confirms
> the landing, and clears the waits and doubts a spinner could have caused.

## `RunSecrets.saw`, [line 66](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L66): Docstring

> What the page showed next. Submitted, same host, password box on screen and
> empty: refused. No password box, on any host: the browser landed, and a
> sign-in form after that is a session ending, not a refusal -- the password
> is typed again. A key whose last landing was never confirmed by the run
> moving on (`_unsure`) does not get a second landing from a page alone. A
> form still holding what was typed is a submit in flight and decides
> nothing. Hosts, never page text.

## `RunSecrets._refuse`, [line 81](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L81): Docstring

> Only a vault value is latched on its key; a held value refused says nothing
> about what the vault keeps. Either way it is not typed again in this run.

## `WatchingChannel`, [line 99](../../../../../../../backend/src/sro/application/execution/run_secrets.py#L99): Class

> The run's browser channel, read on the way through. Both facts the refusal
> rule needs are already in the conversation the run engine has: what a
> performed command typed, and what every `ui.url` answer says about the page
> (`signed_out`, and from the extension `credential_empty` -- whether a visible
> login box is empty, never its value). Watching here means the 2,000-line
> engine needed no new hook, and every command kind that types a password --
> `ui.perform`, `ui.perform_at`, the browser's own `sign_in` -- is covered in
> one place. Only replies the browser reported as done count.
>
> A `ui.url` answer from a tab that is not the run's own (`elsewhere` with
> `elsewhere_is_ours` false: the operator's front tab) is ignored -- an
> unrelated page must not clear a wait or latch a password (review round 4).
