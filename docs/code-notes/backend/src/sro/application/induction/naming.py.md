# Notes for `backend/src/sro/application/induction/naming.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/naming.py`](../../../../../../../backend/src/sro/application/induction/naming.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/naming.py#L1): Docstring

> Parameter names, derived from where the value was found.
>
> No model is involved: the captured payload already uses the vocabulary of the
> system being automated, and invented names would not match it.

## module, [line 17](../../../../../../../backend/src/sro/application/induction/naming.py#L17): Note on the line above

Code: `CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")`

> Where ``shipmentId`` becomes two words. Shared, because a second copy of
> this that disagreed about digits would split field names one way for naming
> and another way for deciding what is a credential.

## `snake_case`, [line 21](../../../../../../../backend/src/sro/application/induction/naming.py#L21): Docstring

> ``shipmentId`` -> ``shipment_id``; ``Order Number`` -> ``order_number``.

## `singular`, [line 61](../../../../../../../backend/src/sro/application/induction/naming.py#L61): Docstring

> One of whatever this is, as far as spelling alone can say.
>
> Deliberately shallow -- no dictionary, no stemmer. `addresses` has to give
> back `address` and not `addresse`, which is what a bare trailing-s rule
> produced and what then appeared in every sentence the system said out loud:
> "list every addresse at SG". `-es` only collapses after the endings that
> take it, because `modes` is not `mod`.

## `deduplicate`, [line 76](../../../../../../../backend/src/sro/application/induction/naming.py#L76): Docstring

> Suffix a colliding name rather than merging two distinct parameters.

## `_singular`, [line 30](../../../../../../../backend/src/sro/application/induction/naming.py#L30): Comment

Code: `if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):`

> Naive by choice: getting `entries` or `boxes` slightly wrong still yields a
> readable name, which is not worth an inflection dependency.

## `suggest_name`, [line 45](../../../../../../../backend/src/sro/application/induction/naming.py#L45): Comment

Code: `segments = url_path_segments(url)`

> The segment before an id usually names it: /shipments/12345.
> Segments come from the same helper the sites are indexed against;
> splitting the whole URL here would count the scheme and host and
> name every path parameter after the wrong segment.

## `suggest_name`, [line 51](../../../../../../../backend/src/sro/application/induction/naming.py#L51): Comment

Code: `cleaned = name[2:] if name.lower().startswith("x-") else name`

> `X-Wave-Id` reads as `wave_id`: the `x-` prefix says the header is
> non-standard, which is not information the parameter needs.
