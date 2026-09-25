# Notes for `backend/src/sro/infrastructure/steel/pool.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/pool.py`](../../../../../../../backend/src/sro/infrastructure/steel/pool.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `SteelPool.open`, [line 29](../../../../../../../backend/src/sro/infrastructure/steel/pool.py#L29): Note

> Least-loaded, not first-fit, over the calling tenant's own containers
> (`_containers`) -- a tenant never sees another tenant's URLs, configured
> or falling back to the single shared default together (S4 fix round 1:
> the first pass picked the first container with room, which packs one
> container to capacity before touching a second).
>
> `pinned` keeps a returning account on the container its last lease was
> on (the broker reads it from `browser_sessions`, S7): when that container
> is still one of the tenant's, it is the only candidate, and a full one is
> `PoolFull` rather than a silent move -- the account's cookies, and
> whatever the system bound to where they came from, stay put. A pinned
> URL that is no longer configured for the tenant (a container removed) is
> ignored and the account is placed least-loaded like a new one.
