# Notes for `backend/scripts/redact_stored_evidence.py`

Comments and docstrings moved out of [`backend/scripts/redact_stored_evidence.py`](../../../../backend/scripts/redact_stored_evidence.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/redact_stored_evidence.py#L1): Docstring

> Rewrite already-stored evidence through today's redaction rules.
>
> `ingest.py` redacts what arrives. It cannot redact what already arrived: the
> objects written before that boundary existed still hold whatever the browser
> sent, and on this deployment that was a live JWT and an OAuth authorization
> code in fourteen objects.
>
> A cleanup is a rewrite, not a delete. Each object is read, put through the same
> `redact_events` the ingest path uses, and written back at the same key so every
> `observation_batches.uri` still resolves. `byte_count` is corrected because it
> is the only column that stops being true.
>
> **Dry by default.** It reports what would change and touches nothing until
> `--apply`, because rewriting the evidence plane is not something to do by
> accident.
>
>     uv run python scripts/redact_stored_evidence.py                 # report
>     uv run python scripts/redact_stored_evidence.py --tenant acme   # narrower
>     uv run python scripts/redact_stored_evidence.py --apply         # do it
>
> Idempotent: a second run finds nothing to change, because the rules are the
> ones the first run already applied. Proven, not assumed: re-running the
> transform over all 396 live objects produced byte-identical output for 396 of
> 396, and every backup holds the same events in the same order as its live
> counterpart.
>
> **Putting one back.** `--backup` writes the original to `<key>.pre-redaction`
> in the same bucket -- not somewhere clever, because the point is that a person
> who finds this damaged can restore with one call:
>
>     aws s3 cp s3://BUCKET/KEY.pre-redaction s3://BUCKET/KEY
>
> That leaves `observation_batches.byte_count` describing the redacted object
> rather than the restored one. Recompute it from the object's own size:
>
>     UPDATE observation_batches SET byte_count = <ContentLength> WHERE uri = ...
>
> A restore is not a rollback of the rules: the next ingest redacts on arrival,
> and running this script again re-applies them.

## module, [line 26](../../../../backend/scripts/redact_stored_evidence.py#L26): Note on the line above

Code: `ADVISORY = {"long b64 run"}`

> Counters that report rather than judge. Everything else must reach zero.

## module, [line 18](../../../../backend/scripts/redact_stored_evidence.py#L18): Comment

Code: `LIVE = {`

> What a reader would grep the evidence plane for to decide whether this
> worked. Deliberately the same shapes the rig's own measurement used, so the
> before and after numbers here can be compared with the ones in
> docs/new-agent-doc-arc/findings.md.

## module, [line 22](../../../../backend/scripts/redact_stored_evidence.py#L22): Comment

Code: `"severed token": re.compile(r"\u00abredacted\u00bb[.\-_][A-Za-z0-9._~+/-]{16,}"),`

> The counter that does not share an assumption with the rule. Both rows
> above anchor on `eyJ`, which is the very prefix the JWT rule replaces --
> so a PARTIAL redaction removes the anchor, both counts read 0, and the
> script prints a clean bill over surviving ciphertext. That happened: a
> three-segment rule on a five-segment JWE left 1,059 characters behind a
> marker, and this run reported success. A marker with a base64 run still
> glued to it is the shape of that failure and nothing else.

## module, [line 23](../../../../backend/scripts/redact_stored_evidence.py#L23): Comment

Code: `"long b64 run": re.compile(r"[A-Za-z0-9_-]{60,}"),`

> Any long high-entropy run at all, priced as a warning rather than a
> failure: real evidence contains long ids, so this number is never
> expected to be zero. It is here to move when something changes.

## `main`, [line 105](../../../../backend/scripts/redact_stored_evidence.py#L105): Comment

Code: `payload = (`

> `separators` matches `ingest._ndjson` exactly. Default separators put
> a space after every `,` and `:`, which rewrote 322 objects that held
> no credential at all, grew the plane by 2.6 MB, and left these
> objects spaced while every future ingest writes compact -- one plane
> in two formats, for whitespace.

## `main`, [line 127](../../../../backend/scripts/redact_stored_evidence.py#L127): Comment

Code: `spare = f"{key}.pre-redaction"`

> Written to the same bucket rather than somewhere clever: the point
> is that a person who finds this damaged can put it back with one
> copy_object, and that is only true while the original is beside
> it. Skipped when one already exists, so a second run cannot
> overwrite the pristine copy with an already-redacted one.

## `main`, [line 136](../../../../backend/scripts/redact_stored_evidence.py#L136): Comment

Code: `store.put_object(  # type: ignore[attr-defined]`

> Same key, so every stored uri still resolves. byte_count is the one
> column that stops being true, and a row that disagrees with its own
> object is worse than either.
