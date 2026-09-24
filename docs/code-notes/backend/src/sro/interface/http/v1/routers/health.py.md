# Notes for `backend/src/sro/interface/http/v1/routers/health.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/health.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/health.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `ready`, [line 55](../../../../../../../../../backend/src/sro/interface/http/v1/routers/health.py#L55): Comment

Code: `checks = await container.readiness()`

> Two facts, not one. A database that answers and is behind its code is
> reachable and useless -- which is the state that cost an afternoon of
> diagnosis aimed at the wrong half of the system. Both come back from one
> connection: see `Container.readiness`.
