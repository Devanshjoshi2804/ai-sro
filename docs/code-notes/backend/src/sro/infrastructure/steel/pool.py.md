# Notes for `backend/src/sro/infrastructure/steel/pool.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/pool.py`](../../../../../../../backend/src/sro/infrastructure/steel/pool.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `SteelPool.open`, [line 29](../../../../../../../backend/src/sro/infrastructure/steel/pool.py#L29): Note

> Least-loaded, not first-fit, over the calling tenant's own containers
> (`_containers`) -- a tenant never sees another tenant's URLs, configured
> or falling back to the single shared default together (S4 fix round 1:
> the first pass picked the first container with room, which packs one
> container to capacity before touching a second).
>
> This does not pin an account to the container it lands on. `Lease.
> container_url` already carries that once a lease exists; reading it back
> here, so a returning account keeps its container instead of being
> re-balanced onto whichever one is least loaded that moment, is S7's job,
> not this one's.
