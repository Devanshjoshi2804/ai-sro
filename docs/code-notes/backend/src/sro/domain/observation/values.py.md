# Notes for `backend/src/sro/domain/observation/values.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/values.py`](../../../../../../../backend/src/sro/domain/observation/values.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/values.py#L1): Docstring

> A6 — a value that crossed a system boundary.
>
> Cross-organisational process mining reconstructs one process from logs with no
> shared case identifier -- our exact problem -- at over 98.4% precision and 94.2%
> recall, by linking on shared data items across the separate logs. No model
> anywhere in it. A supplier name typed into one system and appearing in a call to
> another is that signal, and it is arithmetic over evidence already stored.
>
> A hint, not a gate: this is handed to the umbrella pass as a labelled section
> and the model decides what it means. Nothing is joined on this score alone.
>
> This is arithmetic over what was typed and what a reading reported, and it
> never reads gesture.requests. A value that appears only inside another
> system's request body is therefore found only when the model echoed it into
> values_seen -- trim() does put body_keys in front of the model, so the path
> exists, but it runs through the model rather than around it.

## module, [line 12](../../../../../../../backend/src/sro/domain/observation/values.py#L12): Note on the line above

Code: `K_MIN_LONE_WORD = 6`

> A value that is one bare word has to be longer than one that is not.
>
> `test` is exactly K_MIN_VALUE_LEN and, on an all-tabs day, appeared in five
> hosts at a ubiquity of 0.025 -- under the furniture threshold, over the length
> floor, and so published as a cross-system link. A junk crossing is worse than
> noise: `strength` uses crossings to pull evidence INTO the window, so it
> displaces real signal.
>
> Blocklisting the word is what this looked like it needed, and the corpus says
> otherwise: `Test Drive LLC` is a real carrier in this tenant's capture and a
> genuine crossing, and it contains `Test` as a whole word. The same trap as
> `pin` in `shippingPhone`.
>
> What actually separates them is shape. A lone short word collides by accident
> across five applications; two words, or one long one, do not.
>
> What this costs, measured over all 109 distinct values in the real capture --
> and the earlier claim here that it "rejects `test`" was a claim about one
> value when the real number is fourteen. It rejects `test`, `test4`, `TEST!`,
> `TEST1`, `TEST2`, `TEST5`, `TESTI`, `ACZRD`, `LOCK`, `TDDS`, `TRLR` and the
> literals `True`/`False`/`None`. `TEST1` is the name of a workflow the rig
> itself mined and `TESTI` is a real work-area name; `TDDS`, `TRLR` and `ACZRD`
> read as carrier or dock codes, and a four-character SCAC is standard in this
> trade, so no lone-word floor above four can keep one.
>
> That cost is currently zero, for a reason worth stating rather than hiding
> behind the keeps. `trivial()` gates CROSSINGS only -- what may link evidence
> between systems -- and never a value, a parameter or a step, so a rejected
> value still reaches every workflow that typed it. And `shared_values` needs a
> value in two distinct systems: the real capture produces **no crossings at
> all**, at a floor of 4, 5 or 6 alike. The `test` collision that motivated this
> came from the synthetic all-tabs day. So the constant is honest about a hazard
> nobody has yet met on real evidence, it has never been exercised against a
> real crossing, and 6 rather than 5 is not a measured choice -- lowering it
> would keep seven of the fourteen and change nothing observable until a real
> two-system corpus exists to arbitrate.
>
> The keeps are real and were checked: `AITEST9`, `Enveyo`, `Test Drive LLC`,
> `005-BEST METHOD` and `ConnectShip (TanData)` all survive.

## module, [line 67](../../../../../../../backend/src/sro/domain/observation/values.py#L67): Note on the line above

Code: `K_RETURNED_TO = 2`

> How many separate stretches on a system count as somebody using it.
>
> One stretch is a visit. Two is going back, and going back is what says a tab
> was being USED rather than passed through: the browser bounces an operator
> through an identity provider exactly once, and somebody working a mail against
> a form returns to it again and again.

## `typed_values`, [line 15](../../../../../../../backend/src/sro/domain/observation/values.py#L15): Docstring

> What this gesture put into the world: what was typed, and what a reading
> saw entered. A credential is never here -- is_secret() is the one place
> that rule lives, and this asks it rather than restating it.
>
> The whole gesture is refused rather than only its typed value. values_seen
> comes back from the model, which is shown the field it was typed into, so
> guarding the typed value alone let a password return by the other route and
> become a cross-system link -- the same leak found in as_evidence, in a
> second place. The wire parser nulls the value at parse time and so hides
> this from a test built on the fixture; the model's echo is not nulled by
> anything.

## `trivial`, [line 27](../../../../../../../backend/src/sro/domain/observation/values.py#L27): Docstring

> Too short, too common, or a literal that means nothing on its own.

## `frequencies_over`, [line 35](../../../../../../../backend/src/sro/domain/observation/values.py#L35): Docstring

> How often each value appears across the tenant's gestures.
>
> Arithmetic, not a pattern, and the only thing here that needs history: a
> value carried by a quarter of everything is furniture rather than a link.
>
> Counted through typed_values, which is the same function shared_values
> below counts through. It used to read `values_seen` out of the intents
> table alone -- model output only -- so a value the operator actually TYPED
> on every gesture and that no reading ever echoed looked up at 0.0 and could
> never be classified as furniture, however ubiquitous it was. The two halves
> of one signal were being weighed on different scales.
>
> The ruling that still holds: the numerator is the number of GESTURES
> carrying a value, never the number of mentions, because K_UBIQUITY is a
> coverage fraction. typed_values returns a set, so a value named five times
> on one gesture is one gesture. The unit moved from "reading" to "gesture"
> with the source -- they are the same unit whenever a gesture has been read,
> and the gesture is the unit shared_values already divides the world into.

## `shared_values`, [line 46](../../../../../../../backend/src/sro/domain/observation/values.py#L46): Docstring

> Values appearing in more than one system, and the gestures carrying them.

## `worked_in_both`, [line 70](../../../../../../../backend/src/sro/domain/observation/values.py#L70): Docstring

> Gestures from a sitting where somebody used two systems for one job.
>
> `shared_values` above is the other half of this question and it answers a
> narrower one: it links two systems when the same TYPED VALUE appears in
> both. That misses the commonest shape there is -- read a mail, create the
> thing it asks for -- because a mail somebody read and never typed into
> carries no value across.
>
> Measured on the real stores, 2026-09-14: the value rule links 23 of acme's
> 555 gestures. Its browser's own timeline holds 219 inside a sitting that
> went to another system and came back, 211 of them linked by no value at
> all. One of those sittings is an operator reading a mail whose subject is
> "create a customer type :" and typing the value into the warehouse six
> seconds later; the job mined from it has no mail step, and so no record of
> where the value came from.
>
> Three things keep this from linking the whole browser:
>
> **A sitting, not a day.** `gap` is the caller's, and the caller passes
> `checks.K_SITTING_GAP_S` -- itself tied to the extension's `K_TAIL_TTL_S`,
> because two gestures further apart than the browser's own tail can never
> be matched in one shape however related they are.
>
> **Returned to, not merely visited.** A system has to hold `K_RETURNED_TO`
> separate stretches. A login redirect is entered once and left; a tab
> somebody is working in is come back to.
>
> **Not transit, and not ours.** A system every one of whose gestures ended
> somewhere else is a doorway -- the same rule `checks.work_only` uses to
> strike a sign-in hop out of a job -- and this deployment's own console is
> not a system anybody works in.
>
> **One browser, not one tenant.** A sitting is somebody working, and each
> `stream_id` is one browser -- this tenant's whole evidence sorted by time
> is two operators interleaved, so two people working at once would be read
> as one person moving between systems and the miner would propose a job
> stitching one person's mailbox to the other's warehouse form. Every
> sibling that does this arithmetic partitions the same way
> (`skill.checks.around`, `read_gesture`), and a tenant here really does
> hold more than one stream: acme's 555 gestures are two browsers. Nothing
> changes today -- across this whole store no two streams of one tenant hold
> gestures within `K_SITTING_GAP_S` of each other, because nobody has yet
> run two browsers at once -- so this is the mechanism, and it matters the
> first day a tenant has two operators working.

## `_sittings`, [line 94](../../../../../../../backend/src/sro/domain/observation/values.py#L94): Docstring

> Stretches of work with no more than `gap` seconds of silence in them.

## `_used_for_work`, [line 109](../../../../../../../backend/src/sro/domain/observation/values.py#L109): Docstring

> The systems in this sitting somebody was actually working in.

## `typed_values`, [line 18](../../../../../../../backend/src/sro/domain/observation/values.py#L18): Comment

Code: `found: set[str] = set()`

> Stripped here, which is the only place it happens: this is a set, so a
> gesture whose typed value is "Supplier-X" and whose reading reported
> " Supplier-X" collapses to one value rather than appending the same
> gesture id twice under one key -- two pieces of evidence, downstream,
> where there is one. Stripping in the caller instead deduplicated
> nothing, because the set had already been built from the raw pair.

## `trivial`, [line 31](../../../../../../../backend/src/sro/domain/observation/values.py#L31): Comment

Code: `lone = not any(character in text for character in " -_/.:@")`

> One bare word, and a short one: `test` in five applications is a
> coincidence, `Test Drive LLC` in three is a carrier.

## `shared_values`, [line 53](../../../../../../../backend/src/sro/domain/observation/values.py#L53): Comment

Code: `if not gesture.system:`

> A gesture whose system could not be established contributes nothing.
> An unknown system is not a second system, and `system or ""` made it
> one -- so one unattributable gesture beside one real system reported
> a crossing. Same rule correlate._owner already applies to requests.

## `shared_values`, [line 56](../../../../../../../backend/src/sro/domain/observation/values.py#L56): Comment

Code: `if trivial(value, frequencies.get(value, 0.0)):`

> Already stripped by typed_values, so the frequency lookup and
> the key agree with trivial() and frequencies_over(). They did not
> before: the lookup missed, and furniture at frequency 1.0 was
> published as a link, while one real crossing split four ways
> across "Supplier-X", " Supplier-X" and "Supplier-X\n" became no
> crossing at all. Not case-folded: the fixture has a `D3`, and
> welding codes that differ only in case is the worse error.

## `_used_for_work`, [line 117](../../../../../../../backend/src/sro/domain/observation/values.py#L117): Comment

Code: `doorways = {`

> Every gesture on it moved the operator somewhere else: a doorway, not a
> tab. `any` rather than `all` would strike the warehouse host, which
> bounced elsewhere on 4 of its 495 gestures in the real store.
