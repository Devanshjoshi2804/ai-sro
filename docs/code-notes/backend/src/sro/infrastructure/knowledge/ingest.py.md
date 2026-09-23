# Notes for `backend/src/sro/infrastructure/knowledge/ingest.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/knowledge/ingest.py`](../../../../../../../backend/src/sro/infrastructure/knowledge/ingest.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/knowledge/ingest.py#L1): Docstring

> Load the recorded knowledge base into the store.
>
> Run with `make ingest-kb`. Re-runnable by construction: a claim whose source and
> body have not changed is judged unchanged and nothing is written, so the second
> run reports zero and costs one read per claim.

## module, [line 16](../../../../../../../backend/src/sro/infrastructure/knowledge/ingest.py#L16): Note on the line above

Code: `_DEFAULT_ROOT = Path(__file__).resolve().parents[5] / "knowledge-base"`

> ``index/`` and ``http/`` sit directly under this. There is no
> ``blue-yonder-sce`` subdirectory -- an extra path segment here meant every
> default-args run of `make ingest-kb` found nothing and exited 1 without
> anybody noticing, because the module also logs a clean warning per missing
> file first, which reads as "an empty knowledge base" rather than as broken.

## module, [line 14](../../../../../../../backend/src/sro/infrastructure/knowledge/ingest.py#L14): Comment

Code: `logger = logging.getLogger("sro.knowledge.ingest")`

> Named rather than `__name__`: run as `python -m`, this module is `__main__`,
> which is outside the `sro` tree the log configuration raises to INFO -- so
> every line of the job's own progress would go nowhere.

## `ingest`, [line 37](../../../../../../../backend/src/sro/infrastructure/knowledge/ingest.py#L37): Comment

Code: `filled = await container.backfill_embeddings().execute(ctx)`

> Unchanged claims are deliberately not rewritten, so anything stored before
> embeddings were switched on still has no vector. Filling those in is the
> normal case rather than an edge one.
