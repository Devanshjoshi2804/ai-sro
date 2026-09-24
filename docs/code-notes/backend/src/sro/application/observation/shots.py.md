# Notes for `backend/src/sro/application/observation/shots.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/shots.py`](../../../../../../../backend/src/sro/application/observation/shots.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/shots.py#L1): Docstring

> The pictures an observed episode left behind, joined back to its gestures.
>
> A screenshot taken during passive capture has no row of its own.
> `StoreObservationArtifact` keys one by
> ``tenant/principal/day/batch/screenshot/NNNNN.png``, where ``NNNNN`` is the
> gesture's position within its batch as the recorder counted it
> (`new-chrome-extension/src/background/upload.js`, ``framesOf``). Nothing writes
> that join down anywhere, so this reads it back: count a batch's gestures the
> same way the recorder did, then ask the store which of them were photographed.
>
> Without this, a skill learned from watching has an empty Artifacts tab and a
> timeline of prose, while the pictures of the very gestures it describes sit in
> the object store unreferenced.
>
> Two callers, one counter. `teach` numbers the events it is assembling into a
> recording; `read_shots` numbers a batch to answer which stored gesture each
> picture belongs to. Both go through `numbered` below, because the recorder's
> rule is one rule and a second spelling of it is a second answer to which
> gesture a picture is of.

## `ShotRef`, [line 19](../../../../../../../backend/src/sro/application/observation/shots.py#L19): Docstring

> Where a gesture's picture would be, if one was taken.

## `ShotRef`, [line 21](../../../../../../../backend/src/sro/application/observation/shots.py#L21): Note on the line above

Code: `ordinal: int`

> The gesture's position among its batch's gestures, counting from zero.
>
> Every gesture, not only the photographed ones -- that is the recorder's
> rule, and counting any other way slides every later picture onto the wrong
> gesture.

## `Shot`, [line 25](../../../../../../../backend/src/sro/application/observation/shots.py#L25): Docstring

> One picture the store actually holds.

## `frames_by_instant`, [line 31](../../../../../../../backend/src/sro/application/observation/shots.py#L31): Docstring

> Each gesture's frame number in this batch, keyed by the instant it
> happened.
>
> For the reader that has `Gesture` rows rather than the payload's own
> lines. The two share no id -- `correlate` mints a gesture id this payload
> never saw -- so the browser's clock is the only thing both sides carry.
>
> An instant two gestures share is dropped rather than guessed at, which is
> this module's rule everywhere: a picture hung on the wrong gesture is
> worse evidence than no picture, because nothing about it looks wrong.

## `stored_shots`, [line 51](../../../../../../../backend/src/sro/application/observation/shots.py#L51): Docstring

> Every screenshot the store holds for one batch, by URI, with its size.
>
> Nothing at all for a batch the server filtered: the recorder counted the
> gestures it sent, `admit` then dropped some of them, so the gestures
> stored here are not the gestures the pictures were numbered against. Which
> ones went is not recoverable from a `RejectedEvent`, so this batch's
> pictures are left behind rather than hung on whichever gesture the shifted
> count lands on.

## `frame_of`, [line 60](../../../../../../../backend/src/sro/application/observation/shots.py#L60): Docstring

> The picture numbered for this gesture, or ``None`` when none was taken.
>
> Absent is the ordinary answer: the per-minute cap, a background tab, a
> trim for the byte budget.

## `pictures`, [line 72](../../../../../../../backend/src/sro/application/observation/shots.py#L72): Docstring

> The screenshots for an assembled recording, in frame order.
>
> ``sources`` is `AssemblyResult.sources` -- the gesture each frame was
> opened by -- and ``refs`` is keyed by ``id()`` of those same objects.
> Identity rather than timestamp: two gestures can share an instant, and a
> picture attached to the wrong one is worse evidence than no picture, since
> nothing about it looks wrong.
