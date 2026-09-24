# Notes for `backend/src/sro/application/observation/correlate.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/correlate.py`](../../../../../../../backend/src/sro/application/observation/correlate.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/correlate.py#L1): Docstring

> A1 — a request belongs to the gesture that caused it, or to nobody.
>
> The existing pipeline learned this against a real browser: a request arriving
> after a drain belongs to the previous action, and only traffic with no owning
> gesture at all is an orphan. Orphans are stored, not discarded — a background
> poll is evidence that a background poll happened.

## `correlate`, [line 39](../../../../../../../backend/src/sro/application/observation/correlate.py#L39): Docstring

> Returns (gestures, orphan requests, orphan pages, snapshots ignored).
>
> Accessibility-tree snapshots are deliberately out of scope for this plan
> -- there is nowhere in the schema to put one -- but silently dropping
> them is not the same as never having received them. The count is the
> difference: it says a batch had snapshots even though nothing stores them.

## `_owner`, [line 93](../../../../../../../backend/src/sro/application/observation/correlate.py#L93): Docstring

> The last gesture in the same tab, within the attribution window.
>
> Tab matching is strict equality: a request whose tab we cannot establish
> (tab_id is None) is orphaned on purpose, never guessed at — missing
> evidence means "I cannot prove this belongs to that gesture", not
> "attach it to the nearest one".

## `_nearest_owner`, [line 106](../../../../../../../backend/src/sro/application/observation/correlate.py#L106): Docstring

> The closest gesture in time, in the same tab, within the window.
>
> Requests attach backwards only: a call is caused by the gesture before
> it. A page event is different in kind — a navigation typically lands
> *before* the gesture it gives context to (the operator arrives, then
> acts) — so it may attach to a gesture on either side, whichever is
> nearer in time.

## `as_action`, [line 121](../../../../../../../backend/src/sro/application/observation/correlate.py#L121): Docstring

> The wire gesture as the domain sees it: the fields the arithmetic
> reads, and nothing the recorder might add next week.

## `as_body`, [line 160](../../../../../../../backend/src/sro/application/observation/correlate.py#L160): Docstring

> A wire body as the domain sees it: no encoding field, nothing the
> belts don't read.

## `as_call`, [line 172](../../../../../../../backend/src/sro/application/observation/correlate.py#L172): Docstring

> A wire request as the domain sees it. The tab is not on the request:
> it is on the enclosing `RequestEvent`, so the caller passes it in — an
> orphan call's tab is a fact worth keeping.

## `as_mark`, [line 188](../../../../../../../backend/src/sro/application/observation/correlate.py#L188): Docstring

> A wire page event as the domain sees it.

## `as_action`, [line 141](../../../../../../../backend/src/sro/application/observation/correlate.py#L141): Comment

Code: `required=target.required,`

> What the page said about whether this field must be filled.
>
> Mapped here and not only in `decode`, which is the other ingest
> path: an extension's gestures arrive through this one, and a
> field this function does not name is a field that never reaches
> the store however faithfully the recorder captured it. Measured
> 2026-09-22 at 07:17 -- the recorder had been reading
> `aria-required` for an hour and every stored gesture had none.
