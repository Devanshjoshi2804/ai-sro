# Notes for `backend/src/sro/application/observation/ingest.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/ingest.py`](../../../../../../../backend/src/sro/application/observation/ingest.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/ingest.py#L1): Docstring

> Take an upload from a browser and put it in the evidence plane.
>
> Verbatim, in one object per batch. Whatever normalisation a miner wants can be
> re-run over what arrived; what was never stored cannot be recovered, and an
> operator's day is not repeatable the way a demonstration is.

## `_as_wire_batch`, [line 36](../../../../../../../backend/src/sro/application/observation/ingest.py#L36): Docstring

> The stored batch in the shape `correlate` reads, and how many events it
> could not.
>
> Parsed one at a time and never as a whole envelope, which is the rig's rule
> at `new_agent_arch/src/rig/api.py:482-487` and it holds harder here: these
> events have already been admitted, stored and answered for. An event kind
> the extension shipped last week must not take the batch beside it down --
> by the time this runs the upload is a fact, and raising would roll back a
> claim for events that are already in the blob store.
>
> The count comes back so the tally says a batch had events nothing could
> read, rather than a batch that quietly had fewer.

## `ObservationRefused`, [line 70](../../../../../../../backend/src/sro/application/observation/ingest.py#L70): Docstring

> This upload will not be stored, and the reason is not transient.
>
> A tenant who has not switched observation on, or a device an administrator
> has paused. The extension stops rather than retries -- a queue draining into
> a refusal is how a browser spends a day trying to send work nobody wants.

## `Ingested`, [line 79](../../../../../../../backend/src/sro/application/observation/ingest.py#L79): Note on the line above

Code: `stored_at: str | None`

> Where the evidence went. ``None`` when nothing in the batch survived
> screening, in which case no object was written and no row was made.

## `Ingested`, [line 82](../../../../../../../backend/src/sro/application/observation/ingest.py#L82): Note on the line above

Code: `snapshots_ignored: int = 0`

> Accessibility-tree snapshots admitted, stored, and read by nothing.
>
> There is nowhere in the schema to put one, and `correlate`'s docstring says
> why the count exists anyway: silently dropping them is not the same as
> never having received them. On the response for the same reason the
> rejections are -- a browser shipping snapshots nothing reads should be able
> to see that from the answer, not from a mining run three weeks later. The
> rig returns it in the same 202 body (`new_agent_arch/src/rig/api.py:534`).
>
> 0 on a batch we already had: nothing re-read it, and no column records what
> the first pass ignored.

## `IngestObservation`, [line 86](../../../../../../../backend/src/sro/application/observation/ingest.py#L86): Docstring

> Idempotent on the batch id the extension minted.
>
> An upload that reached us and whose response was lost is retried by every
> correct client. Storing it twice would double every count a miner reads, and
> the miner's whole job is counting how often something happened.

## `_key`, [line 236](../../../../../../../backend/src/sro/application/observation/ingest.py#L236): Docstring

> Tenant first, then who, then the day. A lifecycle rule for a retention
> window is a prefix match, and a purge for one operator is another.

## `_ndjson`, [line 240](../../../../../../../backend/src/sro/application/observation/ingest.py#L240): Docstring

> One event per line, as the extension streamed it.
>
> ``ensure_ascii=False`` because the default escapes the redaction marker to
> ``\u00abredacted\u00bb``: every batch already in the store carries the
> markers the extension wrote, and grepping those objects for the «redacted»
> that every redaction path in this codebase writes finds not one of them.
> The same round-trip argument as `_redact_query` -- a marker a reviewer
> cannot grep for is a hole nobody can count.

## `IngestObservation.execute`, [line 113](../../../../../../../backend/src/sro/application/observation/ingest.py#L113): Comment

Code: `refuse_unless_itself(device, secret, device_id)`

> The tenant credential says who is asking and can never say which
> browser. Without this, a colleague holding a valid token could
> file a day of their own browsing against somebody else's device,
> and every candidate mined from it would name the wrong operator.

## `IngestObservation.execute`, [line 133](../../../../../../../backend/src/sro/application/observation/ingest.py#L133): Comment

Code: `admission = admit(`

> What this operator said may be watched after all, on top of
> what the tenant agreed to by default. Read from the device
> already loaded above, and expired grants simply are not in it.

## `IngestObservation.execute`, [line 144](../../../../../../../backend/src/sro/application/observation/ingest.py#L144): Comment

Code: `check_times(started_at, ended_at, now)`

> Between screening and serialisation, on the whole batch, and
> nowhere else. `admit()` filters by host policy and says nothing
> about values; without this the browser's own redaction was the
> only one there was, and a browser can be made not to run it --
> measured, on this tenant's real traffic: a live JWT and the
> `&code=` carrying it reached the blob store with no marker on
> them at all.
> Before the object is written, not after. `ObservationBatch`
> asks the same two questions and it is built below, once the blob
> has an address -- so an envelope carrying an offset-less time
> answered 422 with the NDJSON already in the store, the
> transaction rolled back, and no row left pointing at it. Neither
> a purge nor the retention sweep can reach an object nothing
> names.

## `IngestObservation.execute`, [line 147](../../../../../../../backend/src/sro/application/observation/ingest.py#L147): Comment (debt)

Code: `uri = await self._blobs.put(`

> ponytail: the daily byte budget is enforced in the extension only.
> Server-side would mean summing today's batches on every upload;
> add it here when a device is seen to ignore the policy.

## `IngestObservation.execute`, [line 166](../../../../../../../backend/src/sro/application/observation/ingest.py#L166): Comment

Code: `wire, unreadable = _as_wire_batch(batch, redacted)`

> The same upload again, as the miner reads it. Two tables, neither
> derived from the other: `observations` keeps the events verbatim
> in the blob store, and this keeps what was read out of them.
>
> In this block on purpose, so the batch claim and its gestures
> commit together. A claim written without them is an id that can
> never be retried -- the events it named are gone, and the row says
> they were handled. The rig makes the same argument for the same
> reason at `new_agent_arch/src/rig/api.py:63-72`.
>
> Correlated from the REDACTED events, not the accepted ones: the
> redacted payload is what was stored, and a gesture carrying a
> value the blob store does not have is a citation pointing at
> nothing.
>
> Measured, because the argument is right and the margin is not:
> `rig_wire`'s validators redact on their own, so a url, a typed
> value, a prose label, a header and a body TEXT come out the same
> either way. The one field that does not is `redacted_fields` --
> the wire's `redact_body` reports shapes and this one reports
> names -- so `admission.accepted` here would store bodies that no
> longer say a password was ever in them. Pinned by
> `test_the_gesture_stored_says_which_field_the_blob_store_lost`.
> Defence in depth, then, rather than the only belt; keep it that
> way, and do not let the wire's copy become the argument for
> deleting this one.

## `IngestObservation.execute`, [line 180](../../../../../../../backend/src/sro/application/observation/ingest.py#L180): Comment

Code: `rejected=len(admission.rejected) + unreadable,`

> Two kinds of loss, deliberately one number. An event
> `admit()` turned away never reached the blob store; one
> `_as_wire_batch` could not parse did, was paid for, and
> is read by nobody. Neither became a gesture, and this
> column's question is "what did this batch not yield" --
> so `accepted + rejected` is not the event count and was
> never meant to be. Split them the day something acts on
> the difference rather than reports it.

## `IngestObservation.execute`, [line 208](../../../../../../../backend/src/sro/application/observation/ingest.py#L208): Comment

Code: `for orphan in orphans:`

> A call or a page event no gesture in THIS batch claimed. In the
> same block for the same reason the gestures are: an orphan
> written outside the batch claim is a row nothing can retry.
>
> The whole point is the batch boundary. The extension uploads on
> a timer, so a click at the end of batch N routinely has its XHR
> arrive in batch N+1, and `correlate` -- which only ever sees one
> batch -- cannot own it. Dropped here, that call is gone for good
> and the gesture reads as a click that asked the server nothing.
> Kept, it is a row a later pass can join on. The rig stores both
> (`new_agent_arch/src/rig/api.py:118-136`); this discarded both as
> `_calls` and `_marks` until now, which made cross-batch
> correlation dead on this side and alive on that one.

## `IngestObservation.execute`, [line 219](../../../../../../../backend/src/sro/application/observation/ingest.py#L219): Comment

Code: `at=datetime.fromtimestamp(mark.at, UTC).isoformat(),`

> The column is a string and the domain keeps epoch
> seconds, so it is spelled here the way the rig spells it
> and the way the contract test writes it: ISO, UTC.

## `IngestObservation.execute`, [line 185](../../../../../../../backend/src/sro/application/observation/ingest.py#L185): Comment

Code: `for one in left:`

> An effect whose gesture is in an earlier batch is attached to the stored row by `attach_effect`. The ceiling: an effect that arrives before its gesture's batch (an upload retried out of order) matches nothing and is dropped and logged; one matching several stored gestures, one naming a ref that is not the stored gesture's (or a stored gesture with no ref), or a gesture that already has an effect, is dropped the same way. Every drop, in the batch or on the stored rows, is counted in `Ingested.effects_dropped` and in the 202 body.
