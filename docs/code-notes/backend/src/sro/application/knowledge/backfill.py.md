# Notes for `backend/src/sro/application/knowledge/backfill.py`

Comments and docstrings moved out of [`backend/src/sro/application/knowledge/backfill.py`](../../../../../../../backend/src/sro/application/knowledge/backfill.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/knowledge/backfill.py#L1): Docstring

> Give existing claims their vectors.
>
> Turning embeddings on later is the normal case, not an edge one: a deployment
> runs on structured filters for weeks, then somebody decides sending titles to a
> hosted model is acceptable. Everything already stored has no vector, and nothing
> re-ingests it — an unchanged claim is deliberately not rewritten.
>
> So this exists, and it is idempotent by construction: it only ever asks for the
> entries that have no vector yet.

## module, [line 12](../../../../../../../backend/src/sro/application/knowledge/backfill.py#L12): Note on the line above

Code: `_BATCH = 200`

> Rows per transaction. Small enough that an interrupted backfill loses a page
> rather than an afternoon, and the next run picks up where it stopped.

## `BackfillEmbeddings.execute`, [line 20](../../../../../../../backend/src/sro/application/knowledge/backfill.py#L20): Docstring

> Returns how many entries were given a vector.

## `BackfillEmbeddings.execute`, [line 45](../../../../../../../backend/src/sro/application/knowledge/backfill.py#L45): Comment

Code: `logger.warning("embedding produced no vectors; stopping with %d done", filled)`

> The embedder answered with nothing usable. Looping would ask
> for the same page forever.
