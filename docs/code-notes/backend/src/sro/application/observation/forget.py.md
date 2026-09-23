# Notes for `backend/src/sro/application/observation/forget.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/forget.py`](../../../../../../../backend/src/sro/application/observation/forget.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/forget.py#L1): Docstring

> An operator deleting their own evidence.
>
> The button in the extension that says "purge the last hour" and means it. Scoped
> to the principal on the credential, never to the tenant: one operator does not
> get to erase another's day, and nothing here reaches across tenants at all.

## `Forgotten`, [line 17](../../../../../../../backend/src/sro/application/observation/forget.py#L17): Note on the line above

Code: `artifacts: int = 0`

> Screenshots and oversized bodies, which are most of what an operator
> means when they ask for their evidence to be deleted.

## `ForgetObservations`, [line 20](../../../../../../../backend/src/sro/application/observation/forget.py#L20): Docstring

> Rows go, then blobs.
>
> That order on purpose: a row pointing at an object that is gone is a miner
> error somebody sees, and an object nobody points at is a lifecycle rule's
> problem. The reverse leaves evidence readable after it was said to be
> deleted, which is the one outcome that makes the promise a lie.

## `ForgetObservations.execute`, [line 27](../../../../../../../backend/src/sro/application/observation/forget.py#L27): Comment

Code: `bound = since if since.tzinfo else since.replace(tzinfo=UTC)`

> A naive `since` is UTC, which is the rule `_bound` keeps for the
> audit read and `codec.when` keeps on the storage edge. Without it
> asyncpg hands the bare datetime to Postgres and it comes back as the
> API HOST's local time: an operator on a +05:30 machine asking to
> forget everything since 09:00 deleted from 03:30Z -- five and a half
> extra hours of their own day, rows and screenshots, answered 200. It
> is the one read that cannot be run again to check.
