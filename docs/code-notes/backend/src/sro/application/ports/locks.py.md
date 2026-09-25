# Notes for `backend/src/sro/application/ports/locks.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/locks.py`](../../../../../../../backend/src/sro/application/ports/locks.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `AccountBusy`, [line 11](../../../../../../../backend/src/sro/application/ports/locks.py#L11): Docstring

> `hold` raises this, never a raw driver error, when it gives up waiting.
> A caller in the application layer -- S7's broker, D2's step runner --
> cannot catch `sqlalchemy`'s or `asyncpg`'s own exceptions without
> importing them, which `lint-imports` forbids from this layer. This is the
> one shape "this account is busy, try later" ever takes, whichever
> implementation of `AccountLocks` raised it.

## `AccountLocks.hold`, [line 17](../../../../../../../backend/src/sro/application/ports/locks.py#L17): Docstring

> `on_wait` is a contract, not a convenience: an implementation that waits
> at all must call it between attempts, at intervals short enough that a
> caller heartbeating a Temporal activity from it stays alive for the
> whole wait. A caller that does not need to heartbeat -- most tests --
> passes nothing and gets a no-op.

## `AccountLocks.hold_named`, [line 21](../../../../../../../backend/src/sro/application/ports/locks.py#L21): Note on the function

> The same lock under a name that is not an account: a tenant's mining
> (`mining:{tenant}`). One port and one mechanism rather than a second lock
> port, because the effect -- one holder across every process -- is the
> same. `on_wait` has the same contract as `hold`'s.

## `AccountLocks.try_hold_named`, [line 25](../../../../../../../backend/src/sro/application/ports/locks.py#L25): Note on the function

> The same named lock, tried once and never waited on: it yields whether
> it was taken, and holds it for the block only when it was. For work that
> another holder makes unnecessary -- the background sweep's sign-in
> decisions for a tenant another worker is mining.
