# Notes for `backend/src/sro/application/shared/locks.py`

Comments and docstrings moved out of [`backend/src/sro/application/shared/locks.py`](../../../../../../../backend/src/sro/application/shared/locks.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/shared/locks.py#L1): Docstring

> One pass at a time, per event loop.
>
> A lock that outlives the loop it was made for is not a lock, it is an
> exception waiting for the next loop.

## `one_at_a_time`, [line 11](../../../../../../../backend/src/sro/application/shared/locks.py#L11): Docstring

> The named lock belonging to the running event loop, made on first use.
>
> A module-level `asyncio.Lock()` binds to whichever loop first touches it and
> raises `Lock is bound to a different event loop` for every loop after --
> which is what `api._reading` and `mine._mining` were, and what broke the
> moment the suite ran in more than one shard. Latent in production
> too: any process that restarts its loop, and any test runner that gives each
> test its own, hits the same wall.
>
> Keyed weakly, so a finished loop takes its locks with it rather than pinning
> them for the life of the process.
