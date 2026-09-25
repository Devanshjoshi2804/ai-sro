# Notes for `backend/src/sro/domain/observation/outline.py`

Explanations for [`backend/src/sro/domain/observation/outline.py`](../../../../../../../backend/src/sro/domain/observation/outline.py), which carries none (Global Constraint 2).

## `K_OUTLINE_OPTIONS`, [line 11](../../../../../../../backend/src/sro/domain/observation/outline.py#L11): Constant

> The page's caps, repeated where the server enforces them
> (page-code.js `OUTLINE_OPTIONS`, `OUTLINE_FIELDS`, `OUTLINE_TEXT`,
> `OUTLINE_MESSAGES`; recorder.js `OUTLINES_PER_GESTURE`). An option list over
> 25 is data, not vocabulary, and is dropped whole (`options: None`).

## `K_OUTLINE_CHARS`, [line 16](../../../../../../../backend/src/sro/domain/observation/outline.py#L16): Constant

> The page's `OUTLINE_CHARS` (16 KiB), enforced again here on whatever a
> client sends: one outline, serialized compactly, is trimmed to fit by
> `_fitted`. Three of them stay well under the extension's 128 KiB record
> limit, and a hostile client cannot make one gesture's outlines the bulk of
> a batch.

## `FIELD_ROLES`, [line 18](../../../../../../../backend/src/sro/domain/observation/outline.py#L18): Constant

> With `MESSAGE_ROLES` and `LANDMARK_ROLES`, the only roles an outline field,
> message or landmark may carry. Anything
> else a client sends (a `gridcell` whose "label" is a row's data, a
> `banner` of free page text, a `region`) is dropped. So is a role that is
> not a string (`_role`): a forged `[]` or `{}` is unhashable, and testing it
> for membership raised inside ingest (E6 review, M1).

## `_said`, [line 41](../../../../../../../backend/src/sro/domain/observation/outline.py#L41): Function

> One outline string, kept only if it is vocabulary: no URL, `name=value`
> pair or token-like run (page-code.js `NOT_VOCABULARY`), and unchanged by `redact_url` and
> `redact_shapes`. A string redaction would change is dropped whole, not kept
> with a marker: an outline string exists to name a control, and a redacted
> token names nothing.

## `outline_kept`, [line 86](../../../../../../../backend/src/sro/domain/observation/outline.py#L86): Function

> The one server rule for an outline, applied in `redact_events` before the
> blob is written and before the batch is parsed, so it holds for both
> stores. The backend does not trust the page's own rule: it rebuilds the
> outline from the keys it knows and copies nothing else, so a `value`, a
> `text` or any key a client adds is never written and no rule has to name
> it.
>
> A message is rebuilt as its role alone: any `text` a client sends is never
> copied (see page-code.js `outlineOf` for why messages keep no text). There
> is no echo rule: a heading, label or option equal to a typed word is kept.

## `_fitted`, [line 70](../../../../../../../backend/src/sro/domain/observation/outline.py#L70): Function

> The page's `fitted`, in the same order: option lists from the last field
> back, then headings, landmarks, messages and buttons from the end, and
> fields last, until the outline fits `K_OUTLINE_CHARS`. Fields go last
> because a field is what a run fills by label (X10): a field missing from
> the outline reads as a field that does not exist.

## `last_outline`, [line 134](../../../../../../../backend/src/sro/domain/observation/outline.py#L134): Function

> The screen a gesture was made on: its own last outline, else the latest
> outline sent earlier from the same tab and frame. A gesture made on a screen
> equal to the previous one carries none (the recorder does not resend it).
>
> "Same frame" also means the same document: the gesture's `url` (the
> frame's own location) must match in scheme, host and path. A top frame's
> `frame_path` is `[]` on every page of the tab, so without it a gesture
> whose own outline was lost fell back to another page's screen (E6 review,
> M5). The query is ignored: an SPA that rewrites `?id=` stays on one
> screen.
