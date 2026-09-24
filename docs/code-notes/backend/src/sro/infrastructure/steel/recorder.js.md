# Notes for `backend/src/sro/infrastructure/steel/recorder.js`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/recorder.js`](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js). Each note names the code it explains (the const it is bound to, then the line in the current file) and keeps the original text. The rest of this file still carries its explanations inline (`check_code_notes.py` gained JS support in X1, after most of this file was written); the symbols below are the ones added since, so they follow the same-file convention the Python side already uses.

## `settingOf`, [line 94](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L94): Docstring

> The value half of an after-state, and structurally never free text
> (E5 ruling, 2026-09-25). Only a control whose value IS a state records one:
> a checkbox, radio or switch as `checked` / `unchecked`, read off its checked
> state and never its `value` attribute (which is `on` for every checkbox, so
> a later "is it ticked" check would always pass); a select as the visible
> label of what is chosen. Everything else -- every text-type input, a
> textarea, a contenteditable, a `role=textbox|searchbox|combobox` entry, a
> file input, a button, a custom element's host -- is `null`.
>
> Decided by what the control is and not by whether it looks secret, because
> "looks secret" is judged at the moment the state is read: a password field a
> "show" toggle has switched to `type=text`, and a password input inside a
> custom element's shadow root whose host exposes `.value`, both passed that
> check and leaked what was typed. A text control has no value here at all,
> so neither shape can. `isSecretField` still gates a select named like a
> credential.

## `stateOf`, [line 108](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L108): Docstring

> What the target is in right now: its setting (`settingOf`), whether it is
> visible, whether it is enabled. `emit` calls it on whatever element the
> *previous* gesture touched, not the one triggering this call.

## `REALM`, [line 120](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L120): Docstring

> Makes `ref` unique across recorder installs. The counter restarts whenever
> the recorder is installed again (a navigation, a `document.open`), so a bare
> counter would let a new page's gesture 1 claim the identity of an old page's
> gesture 1 on the same tab and frame.

## `last`, [line 122](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L122): Docstring

> The element the previous gesture acted on, and `lastRef` that gesture's
> `ref`, so `emit` can read its state right before recording the next one and
> say whose state it is (`prior_of`). Both are `null` at the start, after a
> gesture with no element of its own (`scroll` -- which therefore consumes the
> previous target's state and resets it, it does not skip it), and after the
> worker says it did not keep the gesture that set them (`sro:dropped`).

## `emit`, [line 261](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L261): Docstring

> A control keeps changing after the gesture that touched it fires -- a
> spinner clears, a field disables, a box stays ticked -- so there is no
> instant during a gesture itself that is "the state it left". The next
> instant that can observe it is the next gesture: whatever `stateOf(last)`
> reads here, right before `last` is reassigned, is what the gesture before
> this one left its target in. It travels as `prior` on THIS record, with
> `prior_of` naming the `ref` of the gesture it belongs to; the backend
> attaches it to exactly that gesture and to nothing else
> (`correlate`, `redact._setting`).
>
> Ceiling: the last gesture of a batch has no later gesture in that batch, so
> its after-state arrives in the next batch and is not joined (see
> correlate.py's notes).

## module, [line 286](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L286): Comment

Code: `listen('sro:dropped', (e) => {`

> The worker drops a gesture while capture is paused, in a tab nobody is
> watching, or in a tab a run is driving, and this recorder cannot see that.
> Without being told, the next gesture it records reads that dropped
> target's state as its `prior` -- the state of something done while paused.
> `observe.js` dispatches `sro:dropped` with the dropped gesture's `ref`
> whenever the worker does not answer `ok: true`, and the previous target is
> forgotten if it is still that gesture's. When the next gesture was recorded
> before the answer came back, its `prior_of` names a gesture the server
> never received, and the server joins nothing.
