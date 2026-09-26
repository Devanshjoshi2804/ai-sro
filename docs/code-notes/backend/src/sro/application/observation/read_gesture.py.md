# Notes for `backend/src/sro/application/observation/read_gesture.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/read_gesture.py`](../../../../../../../backend/src/sro/application/observation/read_gesture.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L1): Docstring

> A3 — one model call per gesture, and never a batch of them.
>
> Batching stream items into a shared call degrades each item through semantic
> interference and diluted attention; measured accuracy decays roughly
> A(T) = A_max * e^(-b(T-1)) in batch size while throughput only saturates. The
> saving is small and the cost is per-item quality. So: one gesture, one call.
>
> Ported from `read_gesture` in `new_agent_arch/src/rig/intents.py` and
> `read_new_gestures` / `_read_unread` in `new_agent_arch/src/rig/api.py`. The
> words, the schema and the parsing are `sro.domain.observation.reading`; this is
> the half that asks and the half that stores.

## module, [line 36](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L36): Note on the line above

Code: `READING_LIMIT = 200`

> How many unread gestures one pass reads. A drain calls this repeatedly.
>
> Bounded because a pass that asks the model thousands of times before returning
> is a pass nothing can stop, and because every pass must reduce the unread set:
> a pass that returns 0 ends the drain.

## `read_gesture`, [line 39](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L39): Docstring

> One gesture, one call, one intent -- error, refusal and nonsense alike.
>
> The reading as it came back, and nothing folded into it. `with_recent_values`
> used to run here and now runs in the loop, because the two have different
> inputs: this is handed one gesture and the readings before it, and the fold
> needs the recorded GESTURES before it -- which only the loop holds. Keeping
> it here also made the cascade unsound, since the answer cached under a piece
> of evidence would carry the first gesture's fold into the second's reading.

## `read_new_gestures`, [line 60](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L60): Docstring (debt)

> Every stored gesture of THIS TENANT with no intent gets exactly one reading.
>
> Scoped, because the reading is what costs money: a second tenant in one
> database had this loop paying for gestures no pass of ours will ever mine,
> and filing intents under their tenant on our bill.
>
> One reading loop at a time. Two concurrent callers both select the same
> unread gestures before either writes an intent, so every gesture in the
> race window is asked -- and billed -- twice, while the replacing write
> leaves only one cost row. One of these fires per ingest, so two batches
> arriving together is enough to trigger it.
>
> Keyed by tenant, not by the bare word "reading". What the lock is for is two
> readers racing over the same unread rows, and those rows belong to a
> tenant: a single global name also made two DIFFERENT tenants take turns,
> which is nothing but a queue. The bake-off is the caller that showed it --
> five models, five copies of one day, and a lock that turned an hour of
> parallel work into five hours of serial work.
>
> ponytail: a process-local lock, because this runs in one process. Claim
> rows in the database if it ever becomes more than one.
>
> `uow` is already open: this commits per reading and never enters or leaves
> the block, so the caller owns the session.
>
> `blobs` is optional and, missing, changes nothing: every gesture is read
> exactly as before. Given, it is read from only for a `thin` gesture --
> see `sro.domain.observation.trim.thin` -- the one case a picture can tell
> the model something its markup could not. A deployment with no object
> store wired to this pass is not a broken one; it is one asking the same
> question this always asked, without the one extra source a picture is.

## `_not_our_own_driving`, [line 86](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L86): Docstring

> The ones an operator made, with this system's own replays taken out.
>
> The second check. The extension drops what it is driving before it is ever
> uploaded, and that was the only thing standing between a run and the
> evidence plane -- one check too few for a rule whose cost is a task mined
> from a robot imitating a person and then offered back as worth automating.
> Every other capture rule in this system is enforced twice, for the reason
> `ObservationPolicy.allows` gives: an extension that is wrong, old or lying
> does not get to write into the evidence plane.
>
> **Marked, not hidden.** Each one gets an intent saying what it is, which
> is what makes this safe to do here: `unread` is "has no intent row", so a
> gesture merely skipped would come back on every pass forever and the
> reading loop would stall on a window of them. An intent with no `act` is
> already what every later reader treats as nothing to learn from, the day's
> spend counts it at nothing because nothing was asked, and the record says
> which run it was -- so somebody reading the evidence can tell a replay
> from a gap.

## `_ask_group`, [line 181](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L181): Docstring

> Every distinct question in this group, asked once and all at once.
>
> Nothing in here touches the unit of work, which is the whole reason the
> group may go out together: `read_gesture` takes a gesture, an image and a
> port, and the port is an HTTP client. The session work -- the pictures
> before, the saves after -- stays one at a time around it.
>
> Distinct is the operative word, and it is why this deduplicates WITHIN the
> group as well as against `already`. Two gestures carrying the same evidence
> that happened to land in the same batch would otherwise both be asked, and
> the cascade's rate would become a function of where the batch boundaries
> fell -- which is not a property of the evidence and not a number anybody
> could act on.
>
> Returns what came back and the first exception if there was one. Not
> raised here: the answers that did come back have been paid for, and a
> raise on the way out of this function would discard them unsaved.

## `_same_evidence`, [line 229](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L229): Docstring

> A name for exactly what the model would be shown about this gesture.
>
> `trim` is what `read_gesture` serialises, so hashing it is hashing the
> question rather than guessing at what makes two questions alike. A key
> built by hand out of the fields that "look like they matter" is the
> version of this that serves a stale answer: keyed on the control and the
> action alone, the same real day reports 65.9% reusable, and the extra
> forty points are gestures whose typed value or request body differed --
> every one of which would have been answered with somebody else's values.
>
> The picture counts too. A thin gesture asked about with its screenshot and
> the same gesture asked about without one are two different questions, and
> only the first is worth the token it costs.

## `_reread`, [line 236](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L236): Docstring

> The same answer, filed against this gesture, and billed to nobody.
>
> The tokens are zeroed rather than copied. The first reading paid for them
> and the row that says so is already stored; repeating the figure here
> would make a day of mining cost whatever the duplicates happened to
> total, which is the same arithmetic error `MineResult` fixed by putting
> the bill on the pass instead of on each workflow it found.

## `_thin_shot`, [line 249](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L249): Docstring

> The picture behind one thin gesture, or `None` when there is not one.
>
> A `thin` gesture is the one case `read_gesture` can use a picture for at
> all, and this is that picture -- the same join `ReadShots` reads back for
> a mined job's evidence tab: the recorder numbers every gesture in a batch,
> a screenshot is filed under that number, and the two sides are matched on
> the browser's clock because a gesture row carries an id the recording's
> own payload never saw.
>
> `cache` holds the listing and the frame numbering per batch, keyed once
> per reading pass rather than once per gesture: a pass over hundreds of
> gestures from a handful of batches would otherwise re-list the object
> store and re-parse the same NDJSON payload for every thin gesture in it.

## `_gestures_before`, [line 286](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L286): Docstring

> The recorded gestures of this stream that came before this one, oldest first.
>
> `_tail_for`'s twin, and deliberately not merged with it: that one answers
> what the MODEL should be shown about the doing so far, and this one answers
> what the OPERATOR demonstrably typed. The first is capped by
> `gemini_read_tail` because every line of it is paid for in prompt tokens;
> this one is not capped at all, because it costs nothing and a form filled
> across twenty gestures is a form whose first field still belongs in the
> save.
>
> Same stream, same reason: a value typed in the operator's other tab was
> never on this form.

## `_tail_for`, [line 292](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L292): Docstring

> The readings of this stream that came before this gesture, oldest first.
>
> Scoped to the stream rather than the tenant: `continues` asks whether this
> gesture carries on the last doing, and one operator's other tab is not it.
>
> Unbounded on purpose. `read_gesture` takes the last TAIL of whatever it is
> handed, and one function knowing that number is one place for it to be
> wrong.

## `ReadGestures`, [line 302](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L302): Docstring

> Read this tenant's unread gestures, once, and bill it.
>
> The same shape as `sro.application.observation.mine_pass.MinePass`, and for
> the same reasons: both refusals happen here, before `read_new_gestures`
> itself. That function's own cap check returns a bare `int` -- no reason a
> reader can tell apart from "nothing was unread" -- which is right for a
> loop that fires on every ingest and wrong for a request that asked to be
> told. Raised here, the door answers 503 and 429, which is what those two
> facts are.

## `read_gesture`, [line 46](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L46): Comment

Code: `recent = [one_line(intent) for intent in tail]`

> Already bounded by the caller, which is the one that knows how long a
> tail this deployment asked for. Re-trimming to the constant here made
> `tail_size` unenforceable from above: a caller asking for none still
> got eight if it handed eight over.

## `read_gesture`, [line 55](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L55): Comment

Code: `image=image if thin(gesture.action.target) else None,`

> A picture only where the markup could not name the control. A
> screenshot on every gesture is the largest avoidable line on the
> bill, and on a named control it tells the model nothing the
> field label already did.

## `_read_unread`, [line 123](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L123): Comment

Code: `rows = await uow.gestures.unread(tenant_id, limit=limit)`

> An intent row means a reading happened, whatever came back in it -- an
> error, or an answer whose `act` was the wrong type and got nulled. None
> of those is retried: `unread` is "has no intent row", the model was
> asked, it answered, and it was billed. Re-asking the same evidence with
> the same prompt bills again for the same likely answer. What a row with
> no usable `act` gets instead is to be visible: the day's spend counts it
> as unusable and the gestures route returns an intent rather than null.
> Not both billed and hidden -- pick one, and this picks visible.

## `_read_unread`, [line 128](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L128): Comment

Code: `logger.warning("%s for %s, %d gesture(s) unread", why, tenant_id.value, len(rows))`

> Reading stops; capture does not. The evidence is still stored, so
> raising the cap tomorrow reads what today declined -- which is why
> this stops the asking rather than the mirroring. Read before the
> loop asks anything: a cap checked per gesture is a cap that has
> already paid for the gesture it stops on.

## `_read_unread`, [line 131](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L131): Comment (debt)

Code: `ordered = await uow.gestures.gestures_for(tenant_id)`

> The tail comes out of one read of the tenant's evidence rather than a
> query per gesture, and the scan of it is linear per gesture.
> ponytail: this reads the tenant's WHOLE HISTORY, not a day. Neither
> `gestures_for` nor `intents_for` takes a time bound, so every pass
> deserialises every gesture ever captured -- request and response bodies
> included -- and that set only grows. Defensible while a pass is dominated
> by up to `limit` model calls, and no longer once it is not. The upgrade is
> `GestureRepository.tail_for(stream_id, before)`: the rig had that query in
> SQL, and a port is exactly the seam it belongs on.

## `_read_unread`, [line 136](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L136): Comment

Code: `already: dict[str, Intent] = {}`

> One reading per distinct piece of evidence. Two gestures the model would
> be shown the same bytes for get the same answer, so the second one is
> arithmetic rather than a call -- 17.1% of a real 164-gesture day.
>
> Only reachable with no tail, and that is not a tuning choice but the
> whole of it: measured on that same day, keyed on the evidence alone the
> rate is 17.1%, and keyed on the evidence the model is ACTUALLY shown --
> which ends with the last eight readings -- it is 0.0%. Every gesture has
> a tail nothing else has, so with one, nothing is ever reusable.

## `_read_unread`, [line 139](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L139): Comment

Code: `asked: list[tuple[Gesture, bytes | None, str | None]] = []`

> The pictures first, and one at a time, because they come off the
> unit of work: `_thin_shot` reads the batch row and the object store
> through the same session every other query here uses, and a session
> is not a thing two coroutines may hold at once.

## `_read_unread`, [line 162](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L162): Comment

Code: `continue`

> Its own call raised. The rest of the group answered and was
> paid for, so they are saved below and this one stays unread
> -- which is what `unread` means and what the next pass will
> pick up.

## `_read_unread`, [line 163](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L163): Comment

Code: `intent = with_recent_values(intent, gesture, _gestures_before(ordered, gesture))`

> Folded here and not inside `read_gesture`, and after the cascade
> and not before it. The fold reads the recorded gestures of this
> stream, which is a thing only this loop holds; and `already`
> therefore caches the unfolded answer, so a reading reused under a
> piece of evidence gets THIS gesture's fold rather than inheriting
> the first one's.

## `_read_unread`, [line 165](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L165): Comment

Code: `intents[gesture.id] = intent`

> Committed a group at a time, not once at the end: a pass that
> dies later has already been billed for these, and a rollback
> would leave them unread and ask -- and pay -- for them again.
> So the next gesture of this stream is read against what this one
> said, exactly as the rig's per-gesture query was.

## `_read_unread`, [line 169](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L169): Comment

Code: `await uow.commit()`

> Only when there is something to make durable. A group whose every
> call raised has staged nothing, and committing it anyway is a
> round trip to Postgres that says nothing -- visible, because
> `FakeUnitOfWork.commits` is a number a test can read and the
> per-reading commit rule is worth keeping legible.

## `_read_unread`, [line 172](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L172): Comment

Code: `raise failure`

> Loudly, and only after the group's paid-for readings are durable.
> Swallowing it would turn a broken deployment into a pass that
> quietly reads nothing every night.

## `_ask_group`, [line 191](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L191): Comment

Code: `questions[gesture.id] = (gesture, image)`

> With a tail there is no shared question -- every gesture trails
> a different one -- so it is keyed by itself and the group is one.

## `_ask_group`, [line 193](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L193): Comment

Code: `questions[key] = (gesture, image)`

> Keyed by the evidence, so two gestures carrying the same bytes
> collapse to one entry here and are asked once. WHICH of them is
> the one asked does not matter -- the key covers the image too, so
> it is the same question either way -- but the reading that comes
> back is stamped with that gesture's id, and every other sharer
> needs it re-stamped with its own. See below.

## `_ask_group`, [line 210](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L210): Comment

Code: `continue`

> This one's own call raised. Every other member of the group is
> unaffected, and this gesture stays unread.

## `_ask_group`, [line 223](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L223): Comment

Code: `if answered.gesture_id != gesture.id:`

> Re-stamped unless this IS the gesture that was asked, and the test is
> the id rather than the order it was met in. Ordering was what stood
> in for this, and it held only while the asked gesture happened to be
> the first sharer the loop reached; it stopped holding the moment the
> dict kept the last. What went wrong was not subtle and was invisible
> in every unit test: the answer carried the asked gesture's id, so it
> was SAVED under that id for all of them -- one gesture written twice,
> the other never written, and the never-written one read and billed
> again on the next pass. A real 164-gesture pass reported 169 readings
> for 164 rows, which is how it was found.

## `_thin_shot`, [line 261](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L261): Comment

Code: `cache[gesture.batch_id] = None`

> The evidence aged out from under the gesture that cites it.

## `ReadGestures.execute`, [line 323](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L323): Comment

Code: `asker = asker_or_refuse(self._asker)`

> Before the session is opened: neither refusal needs a database, and
> a 503 that first took a connection is a 503 that made the outage
> slightly worse.

## `read_gesture`, [line 52](../../../../../../../backend/src/sro/application/observation/read_gesture.py#L52): Comment

Code: `"gesture": json.dumps(trim(gesture), indent=2, sort_keys=True, ensure_ascii=False),`

> The redaction marker is «redacted», and the default ensure_ascii
> writes it into the prompt as \u00abredacted\u00bb -- a form
> nothing else in this system uses. The model was being asked to understand a
> marker written one way here and another way everywhere else, and a
> reviewer grepping stored prompts for it found nothing. Every
> json.dumps on a path to a prompt or to the store says so.
