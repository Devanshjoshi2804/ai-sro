# Notes for `backend/src/sro/domain/observation/window.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/window.py`](../../../../../../../backend/src/sro/domain/observation/window.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/window.py#L1): Docstring

> A4 — pack a window of evidence under a token budget.
>
> The window is built from trimmed evidence rather than full request bodies, and
> that is a measurement rather than a preference. Across 81 real gestures from the
> acme tenant, bodies inline ran a median of 72 tokens and a MEAN of 8,388 --
> three of the eighty-one held 71% of all request bytes and two individually
> exceeded the entire window. "Inline until the budget is spent" does not degrade
> gracefully; it lets one click starve the day, and which click wins is an
> accident of iteration order. Trimmed, the same evidence is a median of 88 and a
> mean of 204, and a whole day fits.
>
> Ported from `new_agent_arch/src/rig/window.py`. Pure -- it reads a `Gesture`, an
> `Intent` and `trim`, and nothing else -- so it lives in the domain beside them
> rather than in the application layer with the use case that calls it.

## module, [line 8](../../../../../../../backend/src/sro/domain/observation/window.py#L8): Note on the line above

Code: `K_WINDOW_TOKENS = 100_000`

> The prompt budget, in `tokens()`'s own units, whose whole purpose is to
> stay under the 200,000 boundary where Gemini 3.1 Pro's input price doubles.
>
> 150,000 did not do that, and the gap is `tokens()` itself. It counts four
> characters to a token, which is right for prose and wrong for what this budget
> actually measures: JSON of ids, URLs, CSS paths and punctuation, with almost no
> long words. Measured on the first real pass over a real store -- 507 gestures
> of Blue Yonder capture, 481,566 characters -- the estimate was 120,438 tokens
> and Gemini counted 204,333. A 1.697x under-count, 2.36 characters to the token
> in truth.
>
> So the budget is set where the ESTIMATE lands the real figure safely inside the
> boundary: 100,000 estimated is about 170,000 real at the measured ratio, leaving
> room for the instructions, the schema, the crossings and the known-workflow
> summary that ride on top of the evidence.
>
> Corrected here rather than in `tokens()` because this is the only cap that can
> be corrected on the evidence there is -- not because the estimator is sound.
> The estimator is wrong, `tokens()` now says so, and every other cap in this
> module inherits the error. They get away with it: `K_MAX_GESTURE_TOKENS`,
> `K_MAX_CROSSING_TOKENS` and the `kb` subtraction are bounds on each other,
> expressed in the estimator's own units and internally consistent as such, and
> `K_MAX_GESTURE_TOKENS` has no docstring to re-tune against anyway. Changing the
> divisor would silently re-tune all of them; four cap tests failed on exactly
> that when it was tried. This constant is the only one holding an EXTERNAL
> referent -- a real-token price boundary -- which is the only reason its error
> was ever visible.
>
> Pinned against that boundary rather than against itself by
> `test_the_budget_stays_under_the_price_boundary_in_real_tokens`. Every other
> assertion this constant has is derived from it and measured with the same
> under-counting `tokens()`, so 150,000 -- the value that shipped 204,747 tokens
> and cost $2.00 -- passed all of them.

## module, [line 9](../../../../../../../backend/src/sro/domain/observation/window.py#L9): Note on the line above

Code: `K_LEAD_UP_S = 180.0`

> How far back a chosen gesture reaches for the work that led to it, in seconds.
>
> Three minutes of one stream: long enough for somebody to open a screen, filter a
> grid, pick a row and press the button; short enough that the job before this one
> is not swept in with it.

## module, [line 14](../../../../../../../backend/src/sro/domain/observation/window.py#L14): Note on the line above

Code: `K_POOL_WAIT = 0.5`

> What each pass of waiting adds, on top of K_POOL_BONUS.
>
> Without it the carry-over is a flat bonus, which reorders nothing: every pooled
> entry gains the same 0.5, the ranking is what it was, and the window shows the
> same strongest items every pass. Measured on a synthetic all-tabs day of 3,240
> gestures across five hosts -- the scale watching every tab produces -- passes
> two through ten packed the identical 468 gestures, and ten passes had shown 19%
> of the day. Running more passes did not help and never would have.
>
> So waiting earns priority. An entry the budget has passed over six times
> outranks a stronger one that has been read six times, and the day rotates
> through the window instead of the same head of it repeating. This is ordinary
> anti-starvation scheduling, and the pool needed it the moment a day stopped
> fitting in one window.
>
> It compounds with K_POOL_AGE rather than fighting it: an entry rises for six
> passes, and if six readings still do not place it, it retires from privilege
> and competes on merit.

## module, [line 16](../../../../../../../backend/src/sro/domain/observation/window.py#L16): Note on the line above

Code: `K_POOL_BONUS = 0.5`

> What a carried-over gesture is worth over a fresh one of the same shape.
>
> The trade this buys, stated plainly because it is a choice and not an
> oversight: everything a pass did not cite is pooled, roughly a third of a real
> window is scrolls, mis-clicks and stray navigation, and so once the budget
> bites, yesterday's scroll (1.5) outranks today's GET-only click (1.0). That is
> intended, on three grounds.
>
> The pool cannot tell junk from a gesture the model failed to place, and neither
> can this file. That judgment is the model's, and the only signal it gives is
> "the pass did not cite it" -- which is exactly what pooling records. Filtering
> the pool by gesture shape would be a second, dumber classifier standing in
> front of the real one, refusing the evidence at 74% recall the pool exists for.
>
> The junk is cheap. A scroll trims to almost nothing -- the window's own
> measurement puts a median gesture at 88 tokens -- so a pooled scroll displacing
> a fresh click costs the window one small item, not a real one.
>
> And the bonus expires. pool.K_POOL_AGE retires an entry after six readings, and
> retirement here means precisely this bonus going away: the gesture goes on
> competing as ordinary evidence at its own strength. So the priority is
> temporary by construction, which is what makes over-inclusion recoverable and
> under-inclusion not.

## module, [line 18](../../../../../../../backend/src/sro/domain/observation/window.py#L18): Note on the line above

Code: `K_MAX_ITEMS = 40`

> One bound for `calls`, `page` and `values_seen`, on purpose.
>
> Not a token budget -- the token budget is the ladder in `as_evidence`, which
> re-measures the whole body after every step and drops to the skeleton if it is
> still over. This is a PLAUSIBILITY bound: no real gesture makes forty calls,
> fires forty page events or shows forty values, so a gesture that does is
> already pathological and is being cut back for that reason, not for its size.
>
> Forty is therefore right for all three even though they are not the same size.
> A `values_seen` entry can reach ~800 characters post-clip (field and value at
> K_MAX_TEXT_CHARS each) against ~17 for a stripped call, so it has by far the
> least headroom under this number -- but sizing each field to its own worst case
> would be a second, weaker token budget standing beside the real one, disagreeing
> with it, and needing its own re-measurement every time _clip changes. The
> ladder already covers the case those numbers would be guarding against.

## `tokens`, [line 22](../../../../../../../backend/src/sro/domain/observation/window.py#L22): Docstring (debt)

> Four characters to a token, and it UNDER-counts what this module ships.
>
> It used to say it "never lies in the expensive direction the way a
> model-specific tokeniser would". Measured on the first real pass over a
> real store -- 507 gestures of Blue Yonder capture, 481,566 characters --
> this returned 120,438 and Gemini counted 204,333. That is 2.36 characters
> to the token, a 1.697x under-count, and it lies in exactly the expensive
> direction: it crossed the 200,000 boundary where the input price doubles
> and spent $2.00 doing it. The estimate is fine to BUDGET with, because it
> is monotonic in length and stable across models; it is not fine to trust
> about a real-token threshold.
>
> The divisor stays 4 anyway, and `K_WINDOW_TOKENS` carries the correction
> instead. Changing it here would silently re-tune every other cap in this
> module, all of which were measured against this estimator and are
> internally consistent in its units.
>
> # ponytail: every other cap in this module -- K_MAX_GESTURE_TOKENS,
> # K_MAX_CROSSING_TOKENS, the kb subtraction -- is denominated in a unit
> # measured wrong by 1.697x. That costs nothing while they are only bounds
> # on each other. Re-tune them, or fix the divisor and re-tune them all at
> # once, the day a SECOND cap acquires an external referent the way
> # K_WINDOW_TOKENS has.

## `evidence_tokens`, [line 26](../../../../../../../backend/src/sro/domain/observation/window.py#L26): Docstring

> One item measured the way umbrella.mining_blocks will actually ship it.
>
> Inside a list, at indent=1 -- because that is what mining_blocks writes, and
> budgeting it compact was a 17.6% under-count on the real acme window (22,593
> counted against 26,566 shipped). K_WINDOW_TOKENS is a PROMPT budget whose
> whole purpose is the 200K boundary where Gemini 3.1 Pro's input price
> doubles, so a window filled to it under the compact count shipped ~177,000
> tokens -- over the line, at double the price, silently.
>
> One function rather than the expression, because pack() and the mining use
> case both build a Packed and the two counts must be the same count.

## `Packed`, [line 38](../../../../../../../backend/src/sro/domain/observation/window.py#L38): Note on the line above

Code: `stream_id: str = ""`

> Which browser this came from, so `pack` can tell a gesture's own lead-up
> from somebody else's work at the same moment. Defaulted because a hand-built
> item in a test is not about two streams.

## `_clip`, [line 48](../../../../../../../backend/src/sro/domain/observation/window.py#L48): Docstring

> Bound every string anywhere in the evidence.
>
> Strings only, and deliberately. A cap that shrank only request bodies was
> passed by four routes -- a huge typed value, a URL with nothing to split
> on, two thousand calls on one gesture, and model output returned at a
> million characters -- by 15x to 1000x. Nothing upstream bounds the length
> of what a model returns (see the intent reader's string handling), so this
> is where a string is bounded.
>
> Lists are left alone here. Truncating them at this point dropped five of a
> busy gesture's forty-five calls and returned a body that claimed to be
> whole -- and it did so in a case the ladder below would have handled
> better, by keeping all forty-five and dropping only their detail. Nothing
> loses an item except on a path that has already said `truncated`.

## `_map`, [line 58](../../../../../../../backend/src/sro/domain/observation/window.py#L58): Docstring

> `_clip` returns `object` because it takes one. Every use of these two
> reads back a shape this module built a line earlier; the empty fallback is
> what a `cast` would have written as a lie.

## `as_evidence`, [line 66](../../../../../../../backend/src/sro/domain/observation/window.py#L66): Docstring

> One gesture as the umbrella pass sees it: what it was, and what a model
> already made of it. Capped -- and the cap is a guarantee rather than an
> attempt: nothing over K_MAX_GESTURE_TOKENS leaves here by any route.

## `_wrote`, [line 132](../../../../../../../backend/src/sro/domain/observation/window.py#L132): Docstring

> Whether a packed item's trimmed evidence still shows a write.
>
> A pooled gesture arrives as evidence rather than as a `Gesture`, and the
> trim keeps each call's method -- so the same question is answerable, just
> from the other side.

## `strength`, [line 145](../../../../../../../backend/src/sro/domain/observation/window.py#L145): Docstring

> What earns a place at the ends of the window. Never stated in the prompt:
> telling a model which evidence is most relevant was measured to reduce
> accuracy in all five languages tested.

## `arrange`, [line 158](../../../../../../../backend/src/sro/domain/observation/window.py#L158): Docstring

> Strongest at both ends, weakest in the middle.
>
> MEASURED, and it changes nothing at this scale: six real passes on the 81
> captured acme gestures, three with this applied and three without, gave
> identical coverage (0.80), identical skew (+0.367) and identical proposals.
> The control holds -- 74 of 81 items move and the prompts differ. That window
> is 16% of budget, while the attention findings this argues from concern
> prompts near their limit, so it is unproven at this scale rather than
> disproved. Kept because it costs one sort; claimed for nothing until a
> window near the 555-gesture ceiling has been mined. See
> docs/new-agent-doc-arc/findings.md.
>
> The middle stays in temporal order. Order-invariant representations were
> measured to degrade cross-application reconstruction specifically, and a
> workflow is a sequence -- scrambling it to chase a position effect would
> trade the thing we are reading for points on somebody else's benchmark.

## `pack`, [line 171](../../../../../../../backend/src/sro/domain/observation/window.py#L171): Docstring

> Fill the window strongest-first, then put it back in time order.

## `as_evidence`, [line 67](../../../../../../../backend/src/sro/domain/observation/window.py#L67): Comment

Code: `hide = is_secret(gesture)`

> values_seen is model output, and the model is shown what the operator
> typed. trim() nulls a credential; nothing nulled it on the way back, so a
> password the model echoed into a field it had named went into the window
> intact. Same rule, same gesture, applied on both paths.

## `as_evidence`, [line 80](../../../../../../../backend/src/sro/domain/observation/window.py#L80): Note on the line above

Code: `"tab": gesture.tab_id,`

> The tab the gesture acted in, and (`opened`) each popup it opened with the
> tab that opened it, so the miner sees that a gesture in tab 9 was opened from
> tab 7 and reads a two-tab doing as one job. `opened` is left out when the
> gesture opened nothing, so the ordinary gesture costs one key, not two. This
> changes the miner's input, so `MINE` is version 3 and its input contract says
> what both keys mean; the mining eval compares v3 with v2.

## `as_evidence`, [line 101](../../../../../../../backend/src/sro/domain/observation/window.py#L101): Comment

Code: `body["truncated"] = True`

> Over the cap: keep what names the gesture, drop what merely bulks it out.
> Every call survives here, stripped to what identifies it; the count is
> bounded only if that is still not enough. The full evidence stays in the
> store, reachable by this id.

## `as_evidence`, [line 110](../../../../../../../backend/src/sro/domain/observation/window.py#L110): Comment

Code: `trimmed["calls"] = _seq(trimmed["calls"])[:K_MAX_ITEMS]`

> Still over, so the counts themselves are the bulk. Bounded here rather
> than on the way in, so that a gesture only ever loses an item on a path
> that has already said so.

## `as_evidence`, [line 118](../../../../../../../backend/src/sro/domain/observation/window.py#L118): Comment

Code: `return {`

> Still over, which means something pathological is in here. Keep what
> identifies the gesture and nothing else: one unreadable item in a window
> is worth more than a window that could not be built.

## `pack`, [line 185](../../../../../../../backend/src/sro/domain/observation/window.py#L185): Comment

Code: `writing = {gesture.id for gesture in gestures if _mutates(gesture)}`

> Which candidates carry a write, by id, so the loop below can ask without
> reaching back for the Gesture -- a pooled item arrives already packed and
> has none to reach for.

## `pack`, [line 201](../../../../../../../backend/src/sro/domain/observation/window.py#L201): Comment

Code: `from sro.domain.skill.umbrella import PROMPT_OVERHEAD_TOKENS`

> Deferred, and not at module scope: umbrella imports Window, so the pair
> at import time is a cycle. The subtraction belongs HERE, with `known` and
> `kb`, rather than at a call site -- a budget that leaves out the fixed
> cost of the prompt it is budgeting is not a prompt budget, and
> the task twice plus the response schema plus the crossings block came
> to ~2,600 tokens nothing subtracted.

## `pack`, [line 210](../../../../../../../backend/src/sro/domain/observation/window.py#L210): Comment (debt)

Code: `by_stream: dict[str, list[Packed]] = {}`

> A write is not admitted without the work that led to it.
>
> **A demonstration is several quiet gestures and then a write, and the
> ranking was built to split exactly that shape.** The gesture carrying a
> mutation scores 2.0 and the clicks that made it possible score 1.0, so the
> packer took the write and left the job behind -- and a model shown one
> orphan click cannot propose the job it belongs to. `validate` would refuse
> a one-step proposal even if it did.
>
> Measured on the deployment 2026-09-19. The operator deleted customer type
> GZ4 by hand in a watched tab; `DELETE /wm/customerTypes/GZ4` answered 200
> and all twelve gestures of it were captured. With the tie-break above
> fixed the window reached that evening and admitted exactly one of the
> twelve: the confirm click carrying the DELETE. The eleven that show HOW to
> cause it were still out. With this it admits all twelve, and the window
> grows from 114 items to 161 -- a lead-up is clicks, and clicks are cheap.
>
> Only a write anchors a group, and that is the narrow reading on purpose.
> Every gesture dragging three minutes of history in with it would let one
> scroll spend the window, and the failure this repairs is specifically that
> an EFFECT was shown without its cause. A write is evidence that something
> is possible; the gestures before it are evidence of how to do it, and the
> second is what a job is made of.
>
> ponytail: greedy per-write, not sitting-level packing. Two writes three
> minutes apart still merge their lead-ups, and a lead-up wider than the
> room left is dropped while its write is kept. The upgrade is ranking whole
> sittings; this is the smallest thing that stops the splitting, and it is
> measurable against the same store that found it.

## `pack`, [line 219](../../../../../../../backend/src/sro/domain/observation/window.py#L219): Comment

Code: `for item in sorted(unread, key=lambda i: (-i.strength, -i.at)):`

> Only unread evidence fills the window. `read` is the pooled evidence a
> pass has already read. Once it sorted after the unread and still filled
> whatever budget they left, so one new gesture bought a window of up to
> ~190 leftovers already read, the same leftovers that minted wfl_88bc on
> the QA box. A strong read entry must not take an unread one's place
> either: a pool bigger than a window would then leave the unread out for
> good.

## `pack`, [line 252](../../../../../../../backend/src/sro/domain/observation/window.py#L252): Comment

Code: `for item in sorted(context, key=lambda i: (distance(i), -i.strength))[:K_READ_CONTEXT]:`

> What was read joins only as context for what is unread: the same tab
> (stream) within K_LEAD_UP_S of an unread gesture in the window, nearest
> first, at most K_READ_CONTEXT, and only in the room the unread left. That
> is where the other half of a job that reached two passes would be. A read
> entry with no unread neighbour is not sent.
>
> ponytail: K_READ_CONTEXT = 20 is a guess, not a measurement. It bounds
> what one new gesture can re-send. Tune it with the mining eval if jobs
> spanning two passes stop being put together.

## `pack`, [line 233](../../../../../../../backend/src/sro/domain/observation/window.py#L233): Comment

Code: `if len(chosen) >= K_MIN_GESTURES:`

> The floor is a floor on ITEMS, so a group that will not fit falls
> back to the write alone rather than spending the allowance a whole
> demonstration at a time. Below the floor the budget yields, which
> is what it has always done: a window of nothing is worse than a
> window over its estimate.

## `pack`, [line 258](../../../../../../../backend/src/sro/domain/observation/window.py#L258): Comment

Code: `left_out = [one.gesture_id for one in candidates if one.gesture_id not in taken]`

> Everything the window could not take, named once. Built at the end rather
> than as the loop goes: an item passed over on its own turn can still be
> admitted afterwards as a write's lead-up.
