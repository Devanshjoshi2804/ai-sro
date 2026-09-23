# Notes for `backend/src/sro/application/capture/events.py`

Comments and docstrings moved out of [`backend/src/sro/application/capture/events.py`](../../../../../../../backend/src/sro/application/capture/events.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/capture/events.py#L1): Docstring

> Protocol-neutral events the capture adapter emits.

## `InputEvent`, [line 15](../../../../../../../backend/src/sro/application/capture/events.py#L15): Note on the line above

Code: `page_url: str | None = None`

> The page the gesture happened on.
>
> The recorder has always sent it. It only ever reached the accessibility
> snapshot, so a demonstration made of pure gestures -- no snapshot, no call --
> recorded nothing at all about which screen it was on, and the resulting skill
> could only be replayed by an operator who had already navigated there.
