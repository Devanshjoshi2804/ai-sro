# Notes for `backend/scripts/mirror_backfill.py`

Comments and docstrings moved out of [`backend/scripts/mirror_backfill.py`](../../../../backend/scripts/mirror_backfill.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/mirror_backfill.py#L1): Docstring

> Replay captured batches into the rig.
>
> The extension mirrors an upload to the rig only while the rig's URL and token
> are set in its options, so everything captured before that went to the backend
> alone. This posts the backend's own stored batches to the rig's /v1/observations
> so the rig starts from the evidence that already exists rather than from zero.
>
> Reads only. It never writes to the backend, and the rig refuses a batch id it
> already holds, so running it twice costs two rejected requests and nothing else.
>
>     uv run python scripts/mirror_backfill.py --rig http://127.0.0.1:8100         --token "$RIG_TOKEN" --tenant acme [--since 2026-09-01] [--dry-run]

## `main`, [line 52](../../../../backend/scripts/mirror_backfill.py#L52): Comment

Code: `excluded: tuple[str, ...] = ()`

> The batches were captured under whatever policy was in force then, and
> replaying them into a rig governed by today's policy would ingest exactly
> what the tenant has since decided not to watch. The policy is the one
> source of truth for that, so it is read rather than restated here.

## `main`, [line 68](../../../../backend/scripts/mirror_backfill.py#L68): Comment

Code: `ours = settings.our_own_hosts()`

> Plus this deployment's own API and console, which `admit` now refuses at
> ingest -- but these batches were stored before it did. Without this, a
> re-run faithfully re-imports the console asking the API for its own
> recordings, which is how twelve such requests reached the rig and one of
> them became the write a mined workflow reports as its job.

## `main.watched._at`, [line 72](../../../../backend/scripts/mirror_backfill.py#L72): Comment

Code: `def _at(key: str) -> object:`

> `.get(k, {})` returns the JSON null, not the default, when the key
> is present and null -- and then `.get("url")` on it raises. Every
> other reader of this shape uses isinstance for exactly that reason.

## `main.watched`, [line 83](../../../../backend/scripts/mirror_backfill.py#L83): Comment

Code: `return True`

> No host is not the same as a host nobody excluded: a page event
> with no url is kept, because dropping evidence for being
> unattributable is the failure this whole rig is built against.

## `main`, [line 114](../../../../backend/scripts/mirror_backfill.py#L114): Comment

Code: `key = row.uri.split(f"s3://{settings.s3_bucket}/", 1)[-1]`

> `uri` is s3://bucket/key and the port takes the key alone.

## `main`, [line 122](../../../../backend/scripts/mirror_backfill.py#L122): Comment

Code: `parsed = [`

> The blob is ndjson -- one event per line, as the extension streamed
> it -- not an object with an `events` array.

## `main`, [line 125](../../../../backend/scripts/mirror_backfill.py#L125): Comment

Code: `body = {`

> The rig re-declares the wire protocol rather than importing it, so the
> batch goes over as the extension sent it. Anything the rig's own
> parser refuses it names in the response; it does not reject the batch.
