# Notes for `backend/scripts/recipe.py`

Notes for [`backend/scripts/recipe.py`](../../../../backend/scripts/recipe.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## module, [line 1](../../../../backend/scripts/recipe.py#L1): Docstring

> `make recipe job=<id> tenant=<t>`: a job's compiled view, printed as YAML
> for reading. It is not an import format (L1): nothing reads it back, and
> the job is compiled fresh from its evidence each time.

## `as_yaml`, [line 13](../../../../backend/scripts/recipe.py#L13): Docstring

> A twenty-line emitter rather than PyYAML: PyYAML is only installed
> transitively, and the view is plain data (dicts, lists, strings, numbers,
> booleans, null). Scalars go through `json.dumps`, which is valid YAML and
> quotes every string, so a value that looks like a YAML keyword is never
> misread.
