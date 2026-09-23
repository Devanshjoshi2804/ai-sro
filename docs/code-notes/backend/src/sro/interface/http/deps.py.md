# Notes for `backend/src/sro/interface/http/deps.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/deps.py`](../../../../../../../backend/src/sro/interface/http/deps.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `get_context`, [line 46](../../../../../../../backend/src/sro/interface/http/deps.py#L46): Comment

Code: `raise HTTPException(`

> Ours to fix, not theirs, and never a reason to let the request past:
> a deployment that cannot check credentials must refuse, not shrug.

## `get_context`, [line 64](../../../../../../../backend/src/sro/interface/http/deps.py#L64): Comment

Code: `attribute(tenant=caller.tenant_id.value, principal=caller.principal_id.value)`

> From here on, every line this request writes says whose it is. The
> middleware gave it an id before anything knew who was asking; this is
> the first moment anything does. Inside the request's own task, so it
> lasts exactly as long as the request -- see `whose.attribute`.
