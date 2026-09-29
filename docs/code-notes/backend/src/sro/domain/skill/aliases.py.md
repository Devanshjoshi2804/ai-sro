# Notes for `backend/src/sro/domain/skill/aliases.py`

Notes for [`backend/src/sro/domain/skill/aliases.py`](../../../../../../../backend/src/sro/domain/skill/aliases.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## `JobAlias`, [line 8](../../../../../../../backend/src/sro/domain/skill/aliases.py#L8): Docstring

> A request's wording for one of a job's fields, confirmed by an operator
> (`confirmed_by`, `at`). Only an operator's answer writes one, never the
> model, and it belongs to one job, never to the tenant (design-2 rule 11).
> Stored by R2; the compile check reads them through `alias_map`.
