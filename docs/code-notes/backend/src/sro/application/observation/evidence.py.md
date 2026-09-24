# Notes for `backend/src/sro/application/observation/evidence.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/evidence.py`](../../../../../../../backend/src/sro/application/observation/evidence.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/evidence.py#L1): Docstring

> What a batch holds, once the same call is counted once.
>
> Ingest stores what arrived, verbatim and unedited, and that is right: what was
> never stored cannot be recovered, and an operator's day is not repeatable the
> way a demonstration is. So normalisation belongs here, on the way out -- where
> every reader gets it, and where evidence already on disk is healed rather than
> left wrong for as long as it is kept.
>
> What is normalised is one browser defect. A relay injected into a frame a
> second time forwarded the page realm's *same* record again, so one call arrived
> as two adjacent, byte-identical lines carrying one `request_id`. The extension
> no longer does it -- `network.js` refuses to relay where a live copy already is
> -- but a day of recording was made while it did, and the miner whose whole job
> is counting how often something happened counted every one of those twice.
>
> The rule is narrow enough to be provable: a `request_id` is minted once per
> call, by a counter in the realm that made the call. Two lines bearing one are
> never two calls. Nothing else is touched -- a person really can click the same
> control twice, and two identical gestures are two things they did.

## `once_each`, [line 7](../../../../../../../backend/src/sro/application/observation/evidence.py#L7): Docstring

> One upload's NDJSON with a repeated call's later copies dropped.
>
> Per payload, never across them: batches are already idempotent on the id
> the extension minted, and an id repeated in two batches is that idempotency
> to answer, not this.

## `_request_id`, [line 22](../../../../../../../backend/src/sro/application/observation/evidence.py#L22): Docstring

> The call this line reports, or ``None`` for a line that reports none.
>
> A line that will not decode is not a call anybody can identify, so it is
> kept and left to the reader that follows -- each of which already skips
> what it cannot read, and none of which should learn about it from here.

## `once_each`, [line 19](../../../../../../../backend/src/sro/application/observation/evidence.py#L19): Comment

Code: `return b"\n".join(kept) if dropped else payload`

> The bytes themselves when there was nothing to do, which is every batch
> an extension carrying the fix ever sends.

## `numbered`, [line 36](../../../../../../../backend/src/sro/application/observation/evidence.py#L36): Docstring

> Every readable line of a stored batch, each gesture carrying its frame
> number and everything else carrying ``None``.
>
> The counter walks every gesture line, including the ones the caller then
> drops -- out of the episode, unreadable, a scroll -- because that is what
> the recorder counted when it numbered the pictures (`upload.js`,
> ``framesOf``). Counting only the surviving gestures slides every later
> picture onto the wrong one.
