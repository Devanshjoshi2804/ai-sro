# Notes for `backend/src/sro/domain/observation/reading.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/reading.py`](../../../../../../../backend/src/sro/domain/observation/reading.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/reading.py#L1): Docstring

> A3 — the words one gesture is read in, and what a model's answer becomes.
>
> Everything here is arithmetic over an answer that has already come back: the
> confidence vocabulary, the one line an
> intent contributes to the next gesture's context, and the parsing that turns a
> model's JSON into an `Intent`. The call itself is
> `sro.application.observation.read_gesture`, which is the only half that needs a
> port. The words and the response schema are the `READ_GESTURE` record, in
> `sro.domain.prompts.read_gesture`.
>
> Ported from `new_agent_arch/src/rig/intents.py`. An answer that breaks the
> record's schema never reaches this file -- `ask` turns it into no answer --
> and every field is still read back defensively, so a field of the wrong type
> is treated as unusable rather than coerced into a plausible-looking one.

## module, [line 13](../../../../../../../backend/src/sro/domain/observation/reading.py#L13): Note on the line above

Code: `TAIL = 8`

> How many previous readings a gesture is read against.
>
> `continues` was decided from these lines until the schema stopped asking
> for it (2026-09-23), so this is the whole memory one reading has of the
> doing it belongs to. Eight is what the measured day's
> longest job fits inside; every reading pays for them in prompt tokens, once per
> gesture, thousands of times a day.

## `_string_field`, [line 25](../../../../../../../backend/src/sro/domain/observation/reading.py#L25): Docstring

> The schema is advisory, not enforced. A model can return `"act": [...]`
> and nothing here validates it before it reaches `Intent`. Treating a
> wrong-typed field as unusable is what stops that field poisoning `one_line`
> the next time this intent is pulled into somebody else's tail context.

## `intent_from`, [line 30](../../../../../../../backend/src/sro/domain/observation/reading.py#L30): Docstring

> One reading, as it will be stored -- whatever came back in it.
>
> An answer that carried no data still becomes an intent: the model was
> asked, it answered, and it was billed, so the row exists and says why it is
> empty. `model` is passed beside `answer` because `Answer` carries the bill
> but not the name it was run up against -- which is the one thing a reader of
> a $0.00 row needs.

## `_values_seen`, [line 57](../../../../../../../backend/src/sro/domain/observation/reading.py#L57): Docstring

> What the model reported the operator entering, with credentials blanked.
>
> The third place a guard covered the typed value and let values_seen
> through -- after `trim` and `typed_values`, and the only one of the three
> that reaches storage. `save_intent` writes this verbatim and the gestures
> route serves it back, so a password the model echoed into a field it had
> named was persisted and rendered. The field name is kept: that the operator
> typed a password is worth reading, what they typed is not. This is the
> single point every stored values_seen passes through.

## `is_write`, [line 72](../../../../../../../backend/src/sro/domain/observation/reading.py#L72): Docstring

> Whether this gesture's own calls actually wrote something.
>
> A save click is asked about like every other gesture -- what it touched,
> what it typed -- and it typed nothing: the click itself carries no value,
> only the calls it caused prove a write happened at all.

## `field_of`, [line 81](../../../../../../../backend/src/sro/domain/observation/reading.py#L81): Docstring

> What to call the box this value was typed into.
>
> In order of how much the name was actually chosen by somebody: the ExtJS
> component's own `field_label` is what the operator read on screen, its
> `name` is what the form posts under, and `target.name` is the plain-HTML
> fallback. `target.text` is deliberately not in the list -- on an input it
> is the typed value itself, so a fold built on it would name every field
> after its own contents.

## `_typed_before`, [line 93](../../../../../../../backend/src/sro/domain/observation/reading.py#L93): Docstring

> (field, value) for every value RECORDED as typed just before this one.
>
> The recorder's own bytes, not a model's account of them. Ordered oldest
> first and deduplicated by the caller, so a field typed twice keeps the
> last value -- the one that reached the write.
>
> A credential never reaches here: `is_secret` is the one place that rule
> lives, and a secret gesture contributes nothing rather than contributing a
> blanked value that would then be matched against a request body.

## `_carried_any`, [line 105](../../../../../../../backend/src/sro/domain/observation/reading.py#L105): Docstring

> Whether this gesture's writes actually sent something just typed.
>
> The test is the value, not the field name: a form posts `customerType`
> where the label said `Customer Type`, and it is the value that survives
> that translation intact.
>
> Short values are ignored, on the same reasoning and the same threshold as
> `values.K_MIN_VALUE_LEN`: `0` and `-1` appear in every payload ever sent,
> so matching on one would hand the fold back to the telemetry post this
> guard exists to refuse.

## `with_recent_values`, [line 120](../../../../../../../backend/src/sro/domain/observation/reading.py#L120): Docstring

> A write's reading folds in what was typed just before it.
>
> Measured against a real save: the write's own POST body carried five
> submitted fields, and the model's reading of the click itself named one of
> them -- the rest were typed in the gestures just before it. Folded in, the
> save says what it saved. `window.py` serialises `values_seen` into the
> evidence the mining pass reads, and a save whose reading names one field of
> five is a save whose evidence does not say what was submitted.
>
> **The RECORDED typed value, not a previous reading of it**, and this is the
> second version of this function. The first folded in the tail of `Intent`s
> -- the model's account of what it had seen entered -- which made the fold
> an accident of `gemini_read_tail`: set that to 0 and the fold silently
> stopped, and a real 164-gesture pass dropped from naming 16 of 16
> operator-typed fields to 12. That regression is what sent this looking for
> the better source, and the better source was already in the store. The
> recorder captured `action.value` at the keystroke; a reading is a model
> paraphrasing it afterwards. The bytes beat the paraphrase, they cost no
> tokens, and they do not care what order anything was read in.
>
> What this is NOT for, stated because the first version of this docstring
> claimed it and the claim was wrong: it does not rescue a cross-system value
> crossing. `values.shared_values` needs one value under two distinct
> systems; `recent` is the same stream only, so every value folded here
> already belongs to a gesture on the same system.
>
> Scoped to a write on purpose: folding history into every gesture would make
> an ordinary click on an empty form report values from three screens ago. A
> later entry wins a field name over an earlier one -- typed twice, the last
> value is the one that reached the write -- and the write's own reading wins
> over both, being the more direct evidence for whatever it actually named.
>
> And scoped a second time, to a write that carried something just typed.
> `is_write` asks only whether a 2xx POST, PUT or PATCH left the gesture, and
> measured against one real capture that is far too generous: of 15 gestures
> it called writes, **6 were saves**. The other nine were the browser talking
> to itself -- five `sessionKeepAlive` calls and four posts to
> `webPerformanceEntries/batch`, which is the WMS uploading its own
> performance telemetry. So the fold has to be earned: at least one recorded
> typed value must actually appear in what the write sent. A keepalive sends
> no body and a telemetry post sends timings, so neither earns it, while a
> real save sends the form -- and no endpoint anywhere is named to tell those
> apart, which matters because the next customer's housekeeping endpoints
> will be called something else entirely.
>
> Returns a new `Intent` rather than editing the one handed over: the caller
> holds the reading it just built, and a `with_` that quietly rewrites its
> argument is the kind of surprise that costs an afternoon.

## `intent_from`, [line 50](../../../../../../../backend/src/sro/domain/observation/reading.py#L50): Comment

Code: `intent.continues = _string_field(data, "continues") or None`

> No longer asked for (2026-09-23): nothing read it, and every reading paid
> for the model to write it. Still read here, tolerantly, from an answer that
> carries it anyway, and the column stays.
>
> `or None`: the old schema said "empty unless it continues the last doing",
> so "" is what a model returned for most gestures. Stored verbatim it is
> neither a link nor an absence.
>
> This comment used to end "and `continues` is what the mining pass walks
> to join gestures into one doing", which is not true and was worth
> checking rather than repeating: `mining_pass` does not contain the word,
> and `window.as_evidence` -- the function that builds what the miner is
> shown -- lists `act`, `object`, `page`, `why`, `confidence` and
> `values_seen`, and not this. Nothing in the backend reads it. It is
> stored because it is cheap to store and because the day something does
> join a doing it will want it; it is not load-bearing today, and `TAIL`
> above should not be defended on its account.

## module, [line 15](../../../../../../../backend/src/sro/domain/observation/reading.py#L15): Note on the line above

Code: `CONFIDENCE = ["high", "medium", "low"]`

> The one declaration of the confidence vocabulary; `READ_GESTURE`'s schema
> enum is this list. `ask` refuses a word outside the enum, so a second copy
> that drifted would refuse every answer carrying a word the schema offers.

## `_values_seen`, [line 58](../../../../../../../backend/src/sro/domain/observation/reading.py#L58): Comment

Code: `seen = cast(list[dict[str, str]], data.get("values_seen", []))`

> A cast and not a check: the only caller reads an answer `ask` has already
> held to `READ_GESTURE`'s schema, where `values_seen` is a list of objects
> whose `field` and `value` are both required strings. The per-entry type
> guards that stood here could no longer be reached. An empty `field` is
> still allowed by the schema, so that one test stays.
