# Notes for `backend/src/sro/infrastructure/db/locks.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/locks.py`](../../../../../../../backend/src/sro/infrastructure/db/locks.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 11](../../../../../../../backend/src/sro/infrastructure/db/locks.py#L11): Note on the line above

Code: `K_LOCK_WAIT_S = 120`

> §5.4's own margin: a measured sign-in takes about 50 s -- the form, the
> redirect chain, the app settling -- so a second holder waiting behind one
> is waiting behind a real sign-in, not a wedged one. 120 s gives that room
> to run twice over before `lock_timeout` gives up and the waiter is told so,
> rather than left blocked on a lock nobody is going to release soon.

## `PostgresAccountLocks.hold`, [line 20](../../../../../../../backend/src/sro/infrastructure/db/locks.py#L20): Comment

Code: `async with self._engine.connect() as connection:`

> A session-level lock, on a connection this call owns start to finish and
> nothing else touches: `pg_advisory_lock` holds until the session that took
> it calls `pg_advisory_unlock` or disconnects, unlike a transaction-level
> lock that a `commit` or `rollback` would drop out from under a caller
> mid-restore. That also makes it self-releasing the one way that matters --
> a worker that dies mid sign-in takes its connection down with it, and
> Postgres frees the lock the moment the socket closes, so the account is
> never left held by a process that no longer exists.
