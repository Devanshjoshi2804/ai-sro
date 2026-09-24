# Notes for `backend/src/sro/infrastructure/steel/recorder.js`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/recorder.js`](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js). Each note names the code it explains (the const it is bound to, then the line in the current file) and keeps the original text. The rest of this file still carries its explanations inline (`check_code_notes.py` gained JS support in X1, after most of this file was written); the symbols below are the ones added since, so they follow the same-file convention the Python side already uses.

## `stateOf`, [line 94](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L94): Docstring

> What the target is in right now: the value it holds, whether it is visible,
> whether it is enabled. Read the same way for every control kind rather than
> per-listener, because `emit` calls it on whatever element the *previous*
> gesture touched, not the one triggering this call -- see `emit`.
>
> Never a credential's value: `isSecretField` is the same check `describe`
> uses to withhold a typed password from the gesture it belongs to, applied
> here so the state one gesture *left behind* cannot leak a credential either.

## `last`, [line 110](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L110): Docstring

> The element the previous gesture acted on, so `emit` can read its state
> right before recording the next one. `null` at the start of a session and
> after a gesture with no element of its own (`scroll`), which is why `emit`
> guards the read with `last ? stateOf(last) : null` rather than calling
> `stateOf(null)` and trusting it to return something neutral.

## module, [line 248](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L248): Docstring

Code: `const emit = (record, el = null) => {`

> A control keeps changing after the gesture that touched it fires -- a typed
> value settles, a spinner clears, a field disables -- so there is no instant
> during a gesture itself that is "the state it left". The next instant that
> can observe it is the next gesture: whatever `stateOf(last)` reads here,
> right before `last` is reassigned to this call's own element, is what the
> gesture before this one left its target in. It travels as `prior` on THIS
> record; `correlate` (backend/src/sro/application/observation/correlate.py)
> joins it back onto the previous gesture's `action.after`, because at capture
> time nothing here knows that previous gesture's server-side id yet.
>
> Ceiling: the last gesture of a batch is never followed by another `emit`
> call in that batch, so it never gets an after-state from this path. Upgrade
> path and the batch-boundary case are in correlate.py's code notes
> (`_join_after_states`).
