# Notes for `backend/src/sro/application/observation/correlate.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/correlate.py`](../../../../../../../backend/src/sro/application/observation/correlate.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/correlate.py#L1): Docstring

> A1 — a request belongs to the gesture that caused it, or to nobody.
>
> The existing pipeline learned this against a real browser: a request arriving
> after a drain belongs to the previous action, and only traffic with no owning
> gesture at all is an orphan. Orphans are stored, not discarded — a background
> poll is evidence that a background poll happened.

## `correlate`, [line 48](../../../../../../../backend/src/sro/application/observation/correlate.py#L48): Docstring

> Returns (gestures, orphan requests, orphan pages, snapshots ignored).
>
> Accessibility-tree snapshots are deliberately out of scope for this plan
> -- there is nowhere in the schema to put one -- but silently dropping
> them is not the same as never having received them. The count is the
> difference: it says a batch had snapshots even though nothing stores them.

## `correlate`, [line 86](../../../../../../../backend/src/sro/application/observation/correlate.py#L86): Comment

Code: `for key, after in priors:`

> A gesture's after-state is the state its target was in when the next
> gesture came (recorder.js, `emit`), so it arrives as that next gesture's
> `prior`. It is handed back by identity: `prior_of` names the `ref` of the
> gesture whose target it read, and it attaches to the gesture with that
> `ref` on the same tab AND the same `frame_path` -- two sibling iframes on
> one URL share a `frame_url` but never a frame path -- or to nothing. Never
> to "the previous gesture on this key": when the worker dropped the gesture
> in between (paused, an unwatched tab, a run's tab) the previous kept
> gesture is a different control, and joining by position gave it the
> dropped control's state.
>
> The value was already reduced to a state control's setting by
> `redact._setting` before this runs; this only joins.
>
> Ceiling: the last gesture of a batch is followed by the next batch's first,
> whose `prior_of` names a gesture this batch does not hold, so that gesture
> keeps no after-state. Batches flush every minute, so that is one gesture
> per tab and frame per minute. Recording it at flush instead is not
> possible from where a batch is flushed: the service worker holds no DOM,
> and the target's state only exists in the page realm of the frame it sits
> in. Upgrade: persist `ref` with the stored gesture and, at ingest, resolve
> an unmatched `prior_of` against the stored gestures of the same device, tab
> and frame -- `redact._setting` needs that stored gesture's target too, to
> judge the value.

## `_owner`, [line 114](../../../../../../../backend/src/sro/application/observation/correlate.py#L114): Docstring

> The last gesture in the same tab, within the attribution window.
>
> Tab matching is strict equality: a request whose tab we cannot establish
> (tab_id is None) is orphaned on purpose, never guessed at — missing
> evidence means "I cannot prove this belongs to that gesture", not
> "attach it to the nearest one".

## `_nearest_owner`, [line 127](../../../../../../../backend/src/sro/application/observation/correlate.py#L127): Docstring

> The closest gesture in time, in the same tab, within the window.
>
> Requests attach backwards only: a call is caused by the gesture before
> it. A page event is different in kind — a navigation typically lands
> *before* the gesture it gives context to (the operator arrives, then
> acts) — so it may attach to a gesture on either side, whichever is
> nearer in time.

## `as_action`, [line 142](../../../../../../../backend/src/sro/application/observation/correlate.py#L142): Docstring

> The wire gesture as the domain sees it: the fields the arithmetic
> reads, and nothing the recorder might add next week.

## `as_body`, [line 205](../../../../../../../backend/src/sro/application/observation/correlate.py#L205): Docstring

> A wire body as the domain sees it: no encoding field, nothing the
> belts don't read.

## `as_call`, [line 217](../../../../../../../backend/src/sro/application/observation/correlate.py#L217): Docstring

> A wire request as the domain sees it. The tab is not on the request:
> it is on the enclosing `RequestEvent`, so the caller passes it in — an
> orphan call's tab is a fact worth keeping.

## `as_mark`, [line 233](../../../../../../../backend/src/sro/application/observation/correlate.py#L233): Docstring

> A wire page event as the domain sees it.

## `as_action`, [line 162](../../../../../../../backend/src/sro/application/observation/correlate.py#L162): Comment

Code: `required=target.required,`

> What the page said about whether this field must be filled.
>
> Mapped here and not only in `decode`, which is the other ingest
> path: an extension's gestures arrive through this one, and a
> field this function does not name is a field that never reaches
> the store however faithfully the recorder captured it. Measured
> 2026-09-22 at 07:17 -- the recorder had been reading
> `aria-required` for an hour and every stored gesture had none.
