# Notes for `backend/scripts/what_they_did.py`

Comments and docstrings moved out of [`backend/scripts/what_they_did.py`](../../../../backend/scripts/what_they_did.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/what_they_did.py#L1): Docstring

> What an operator actually did, in the order they did it.
>
>     uv run python scripts/what_they_did.py --tenant greyorange
>     uv run python scripts/what_they_did.py --since 90      # the last hour and a half
>     uv run python scripts/what_they_did.py --typed         # only what was typed
>
> The question this answers gets asked every time something on a screen looks
> wrong: *did a run do that, or did a person?* It was answered on 2026-09-16 by
> hand-written SQL against the `gestures` table, and the first three attempts
> answered nothing at all -- because the query asked for `gesture->'action'->>'kind'`
> and the stored JSON has no `action` key. Every column came back empty, which
> reads exactly like "nothing was captured", and the conclusion drawn from it was
> that capture was broken. It was not. The shape was wrong.
>
> **The shape, once, here.** A gesture row stores the action INLINE:
>
>     {"at": …, "url": …, "kind": "type", "value": "GDY", "secret": false,
>      "target": {"name": …, "component": {"field_label": "Customer Type", …}}}
>
> `sro.domain.observation.gesture.Gesture` puts those five under `.action`, which
> is what every reader inside the backend sees -- the repository unpacks the row
> on the way out. So `g.action.kind` is right in Python and `gesture->>'kind'` is
> right in SQL, and the two looking different is the whole trap.
>
> `value` is what was typed. Not `text`: a probe that asked for `action.text`
> printed `null` for every gesture it read and said nothing about it, which is
> the same mistake wearing the quieter face.
>
> **Reads, and nothing else.** Raw SQL for `measure.py`'s stated reason: this
> asks a question the product never asks -- "what happened, in order" -- and a
> repository method added for a probe is a method the product then carries. A
> secret's value is never stored (the recorder strikes it at the boundary), so
> `secret` is printed as a fact and there is nothing behind it to leak.

## module, [line 12](../../../../backend/scripts/what_they_did.py#L12): Note on the line above

Code: `K_WIDE = 34`

> How much of a field name or a typed value one line shows. A mail row's
> accessible name is the whole subject and first line, and a timeline where one
> entry wraps four times is one nobody reads.

## `_short`, [line 35](../../../../backend/scripts/what_they_did.py#L35): Docstring

> One line of it, however the page wrapped it.

## `main`, [line 76](../../../../backend/scripts/what_they_did.py#L76): Comment

Code: `print("\n  nothing was captured in this window.\n")`

> The absence is a measurement too, and it is the one that was misread:
> nothing here means nothing was CAPTURED, which is a different fact
> from nothing having happened.
