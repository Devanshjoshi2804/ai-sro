# Notes for `backend/src/sro/domain/observation/outline.py`

Explanations for [`backend/src/sro/domain/observation/outline.py`](../../../../../../../backend/src/sro/domain/observation/outline.py), which carries none (Global Constraint 2).

## `K_OUTLINE_OPTIONS`, [line 9](../../../../../../../backend/src/sro/domain/observation/outline.py#L9): Constant

> The page's caps, repeated where the server enforces them
> (page-code.js `OUTLINE_OPTIONS`, `OUTLINE_FIELDS`, `OUTLINE_TEXT`,
> `OUTLINE_MESSAGES`; recorder.js `OUTLINES_PER_GESTURE`). An option list over
> 25 is data, not vocabulary, and is dropped whole (`options: None`).

## `K_ECHO_MIN`, [line 14](../../../../../../../backend/src/sro/domain/observation/outline.py#L14): Constant

> The echo rule, the same as the page's (`ECHO_MIN`, `ECHO_SPAN` in
> page-code.js): a typed value of 3 characters or more drops any string that
> contains it; a shorter one drops a string where it is a whole word; any
> shared run of 8 characters drops the string. The server's typed values are
> the `type` gestures of the same batch, including one a client marked secret
> and sent anyway (its value is used for the comparison and never written).
>
> **Ceiling:** a value typed in an earlier batch is not known here; the page
> is the guard for that case. A contenteditable fires no `change`, so its text
> is never a `type` gesture: the page is its only echo guard too.

## `FIELD_ROLES`, [line 17](../../../../../../../backend/src/sro/domain/observation/outline.py#L17): Constant

> With `MESSAGE_ROLES` and `LANDMARK_ROLES`, the only roles an outline field,
> message or landmark may carry. Anything
> else a client sends (a `gridcell` whose "label" is a row's data, a
> `banner` of free page text, a `region`) is dropped.

## `_said`, [line 58](../../../../../../../backend/src/sro/domain/observation/outline.py#L58): Function

> One outline string, kept only if it is vocabulary: not an echo of a typed
> value, no URL or `name=value` pair, and unchanged by `redact_url` and
> `redact_shapes`. A string redaction would change is dropped whole, not kept
> with a marker: an outline string exists to name a control, and a redacted
> token names nothing.

## `outline_kept`, [line 78](../../../../../../../backend/src/sro/domain/observation/outline.py#L78): Function

> The one server rule for an outline, applied in `redact_events` before the
> blob is written and before the batch is parsed, so it holds for both
> stores. The backend does not trust the page's own rule: it rebuilds the
> outline from the keys it knows and copies nothing else, so a `value`, a
> `text` or any key a client adds is never written and no rule has to name
> it.

## `last_outline`, [line 118](../../../../../../../backend/src/sro/domain/observation/outline.py#L118): Function

> The screen a gesture was made on: its own last outline, else the latest
> outline sent earlier from the same tab and frame. A gesture made on a screen
> equal to the previous one carries none (the recorder does not resend it).
