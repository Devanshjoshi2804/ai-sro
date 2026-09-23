# Notes for `backend/src/sro/infrastructure/knowledge/embedding.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/knowledge/embedding.py`](../../../../../../../backend/src/sro/infrastructure/knowledge/embedding.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/knowledge/embedding.py#L1): Docstring

> Embeddings, through Gemini, and the no-op that stands in without a key.

## module, [line 7](../../../../../../../backend/src/sro/infrastructure/knowledge/embedding.py#L7): Note on the line above

Code: `DIMENSIONS = 768`

> Matches the column. `gemini-embedding-001` is asked for this size rather than
> its default, because the store cannot mix two geometries in one index.

## module, [line 9](../../../../../../../backend/src/sro/infrastructure/knowledge/embedding.py#L9): Note on the line above

Code: `_BATCH = 100`

> Requests are capped server-side; a catalogue is thousands of claims.

## `NoEmbedder`, [line 12](../../../../../../../backend/src/sro/infrastructure/knowledge/embedding.py#L12): Docstring

> Retrieval still works: structured filters narrow, terms order.
>
> Worse at synonyms, no worse at anything else — and it is never what decides
> which system or entity a request is about.

## `GeminiEmbedder.embed`, [line 52](../../../../../../../backend/src/sro/infrastructure/knowledge/embedding.py#L52): Comment

Code: `if len(returned) != len(batch):`

> One vector per text, in order, or the store silently attaches the
> wrong meaning to the wrong claim. A short reply is dropped rather
> than aligned by hope.
