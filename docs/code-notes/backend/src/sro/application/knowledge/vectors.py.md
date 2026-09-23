# Notes for `backend/src/sro/application/knowledge/vectors.py`

Comments and docstrings moved out of [`backend/src/sro/application/knowledge/vectors.py`](../../../../../../../backend/src/sro/application/knowledge/vectors.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/knowledge/vectors.py#L1): Docstring

> Embedding, treated as the optional thing it is.
>
> Similarity only *orders* what a structured filter already chose, so a backend
> that is unreachable, unauthenticated or slow must cost the caller its ordering
> and nothing else. Measured the hard way: with a bad key, an unguarded call took
> down every conversation and every ingest, for a feature whose absence is a
> supported deployment.

## `embed_or_none`, [line 10](../../../../../../../backend/src/sro/application/knowledge/vectors.py#L10): Docstring

> One vector per text, or an empty one each. Never raises.

## `embed_or_none`, [line 20](../../../../../../../backend/src/sro/application/knowledge/vectors.py#L20): Comment

Code: `logger.warning("embedding unavailable; retrieval falls back to matching terms")`

> Broad on purpose: every SDK has its own exception tree, and the answer
> is the same for all of them -- carry on without an ordering.
