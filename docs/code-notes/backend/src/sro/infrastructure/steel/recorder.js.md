# Notes for `backend/src/sro/infrastructure/steel/recorder.js`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/recorder.js`](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js). Each note names the code it explains (the const it is bound to, then the line in the current file) and keeps the original text. The rest of this file still carries its explanations inline (`check_code_notes.py` gained JS support in X1, after most of this file was written); the symbols below are the ones added since, so they follow the same-file convention the Python side already uses.

## `stateOf`, [line 53](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L53): Docstring

> What the target is in right now: its setting (`settingOf`), whether it is
> visible, whether it is enabled. `emit` calls it on whatever element the
> *previous* gesture touched, not the one triggering this call. `settingOf`
> comes from page-code.js's `readers` (see its note there), so what is
> recorded here and what `sroPage.holds` later compares are one text
> (X4 review I8). What stays here is the recorder's own guard:
> `isSecretField` blanks a select named like a credential, and a label is cut
> to `MAX_VALUE`.

## `REALM`, [line 66](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L66): Docstring

> Makes `ref` unique across recorder installs. The counter restarts whenever
> the recorder is installed again (a navigation, a `document.open`), so a bare
> counter would let a new page's gesture 1 claim the identity of an old page's
> gesture 1 on the same tab and frame.

## `last`, [line 68](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L68): Docstring

> The element the previous gesture acted on, and `lastRef` that gesture's
> `ref`, so `emit` can read its state right before recording the next one and
> say whose state it is (`prior_of`). Both are `null` at the start, after a
> gesture with no element of its own (`scroll` -- which therefore consumes the
> previous target's state and resets it, it does not skip it), and after the
> worker says it did not keep the gesture that set them (`sro:dropped`).

## `emit`, [line 258](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L258): Docstring

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

## module, [line 296](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L296): Comment

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
>
> `seenOutline` is forgotten on every drop, whichever gesture it was: the
> dropped record carried outlines, and without the reset the next gesture
> would not resend a screen the server never received, so the server's last
> outline for this frame would be stale.
> `observe.js` also dispatches `sro:dropped` (with no `ref`) when it refuses a
> record over its 128 KiB limit, so a refusal for size is never silent here
> either. Outlines are capped well under that limit (page-code.js
> `OUTLINE_CHARS`), so it should not happen.

## `OUTLINES_PER_GESTURE`, [line 79](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L79): Constant

> At most three screens ride on one gesture record: the ones seen since this
> frame's previous gesture, oldest dropped first. A screen equal to the last
> one taken (`seenOutline`, compared as JSON) is not taken again, so an
> unchanged page is not resent. A message keeps only its role, so a status
> whose text ticks does not produce a new screen per tick.

## `takeOutline`, [line 83](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L83): Function

> Reads `outlineOf(document)` and keeps it when the screen changed. A throw is
> swallowed: an outline the page cannot give must not cost the gesture it
> would have ridden on.

## `appeared`, [line 94](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L94): Function

> When a screen is outlined between gestures. `emit` always reads one; this
> adds the screens that come and go before anyone acts: a dialog or form
> added to the page, and any change inside an `alert` or `status` region. A
> dialog that appears and is dismissed by a key the recorder does not record
> would otherwise leave no trace.
>
> **Ceiling:** nothing is read after a demonstration's last gesture, so the
> screen that gesture produced (a confirmation, an error) is not sent until
> the operator acts again.

## `WATCHING`, [line 101](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L101): Constant

> The observer is kept on the window and disconnected before a new one is made,
> for the same reason the listeners are (`__sroHandlers`): installing the
> recorder again must not leave two observers outlining one page.

## `placeNow`, [line 234](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L234): Function

> Also `choiceNow`, and the `describe` keys labelText, fullName, siblingIndex, siblingCount. These keys are additions for later checks and locators. None of them is read by `targetIdentity` or `screenOf`, so a recording's identity does not move when they are present. A credential field records no label and no name. `placeNow`, `choiceNow` and each of those describe keys never throw: a page that breaks a reader loses that key, not the gesture.

## `sendEffect`, [line 71](../../../../../../../backend/src/sro/infrastructure/steel/recorder.js#L71): Function

> Sends one effect keyed to its gesture (`of` is the gesture's ref, `of_at` its `at`), through `window.__sroEffect`. `emit` first finishes the open watcher with `"next"`, so an effect never outlives the gesture after it. A shortcut (ctrl/meta/alt plus a character) is added to the open watcher and is not a gesture: a new gesture kind would change shape keys.
