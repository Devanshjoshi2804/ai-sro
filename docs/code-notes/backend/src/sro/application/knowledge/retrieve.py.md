# Notes for `backend/src/sro/application/knowledge/retrieve.py`

Comments and docstrings moved out of [`backend/src/sro/application/knowledge/retrieve.py`](../../../../../../../backend/src/sro/application/knowledge/retrieve.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/knowledge/retrieve.py#L1): Docstring

> Find what is known, structurally first.
>
> The order matters more than the ranking. Filter by system, kind and entity, and
> only then let similarity order what survived. A nearest neighbour over the whole
> store returns another system's endpoint with total confidence, and a wrong
> answer that is confident and fast is the failure mode this whole design is
> arranged against.

## `Question`, [line 19](../../../../../../../backend/src/sro/application/knowledge/retrieve.py#L19): Note on the line above

Code: `automation_only: bool = False`

> Keep only claims strong enough to drive a call. A screen's help text is
> worth showing an operator and is not worth building a request from.

## `Retrieve.execute`, [line 38](../../../../../../../backend/src/sro/application/knowledge/retrieve.py#L38): Comment

Code: `terms=question.text,`

> Terms still narrow when a vector is present: similarity is an
> ordering, and on a store this size it will always return
> twenty of something. The ternary here used to run backwards
> -- it dropped the WHERE the moment embedding succeeded,
> which is the common case, and left nothing but system/kind
> between a question and a confident nearest neighbour from
> another entity entirely.
