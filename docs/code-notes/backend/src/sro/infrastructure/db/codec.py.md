# Notes for `backend/src/sro/infrastructure/db/codec.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/codec.py`](../../../../../../../backend/src/sro/infrastructure/db/codec.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/codec.py#L1): Docstring

> Domain objects to JSON and back.
>
> Frames and skill versions are deep, immutable and read as whole documents; a
> column-per-field mapping would be a hundred tables and would still lose the
> parts of a capture that have no fixed shape. They are stored as JSONB and the
> queryable fields are lifted into real columns by the models.
>
> The conversion is derived from the domain's own type annotations. There is no
> second definition of the shape to keep in step, and a field added to a domain
> dataclass is persisted the moment it exists.

## `when`, [line 20](../../../../../../../backend/src/sro/infrastructure/db/codec.py#L20): Docstring

> An ISO instant as a real timestamp, in UTC when it said nothing.
>
> The rig kept every clock as text and the records still carry ISO strings,
> so every repository storing one in a ``timestamptz`` converts on both
> edges. Public and here rather than private to one of them: a naive instant
> must be read as UTC and not as the server's local time -- otherwise a run
> that finished hours before it started -- and that is one rule, not one per
> repository.

## `dump`, [line 38](../../../../../../../backend/src/sro/infrastructure/db/codec.py#L38): Docstring

> Adapter to JSON. Public, because the per-table codecs need it too.

## `dump`, [line 39](../../../../../../../backend/src/sro/infrastructure/db/codec.py#L39): Comment

Code: `return adapter.dump_python(value, mode="json", fallback=dict, warnings=False)`

> ``fallback=dict`` covers the read-only mappings the domain uses to keep
> captured headers immutable; ``warnings=False`` silences the resulting
> "expected dict, got mappingproxy" notice, which is exactly what we mean.
