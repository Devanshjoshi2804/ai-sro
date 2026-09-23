# Notes for `backend/src/sro/application/ports/embedding.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/embedding.py`](../../../../../../../backend/src/sro/application/ports/embedding.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/embedding.py#L1): Docstring

> Text to a vector, for ordering candidates a structured filter already chose.
>
> Optional in the same way transcription is: without a backend, retrieval falls
> back to matching terms, which is worse at synonyms and no worse at anything
> else. It is never the thing that decides which system or which entity a request
> is about -- that is a filter, not a distance.

## `Embedder.dimensions`, [line 11](../../../../../../../backend/src/sro/application/ports/embedding.py#L11): Docstring

> Fixed per deployment: the column is sized by it, so changing model
> means re-embedding rather than mixing two geometries in one index.

## `Embedder.embed`, [line 13](../../../../../../../backend/src/sro/application/ports/embedding.py#L13): Docstring

> One vector per text, in order. Empty when unavailable.
