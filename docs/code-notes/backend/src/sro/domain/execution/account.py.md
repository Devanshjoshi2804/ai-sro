# Notes for `backend/src/sro/domain/execution/account.py`

Why the code in [`backend/src/sro/domain/execution/account.py`](../../../../../../../backend/src/sro/domain/execution/account.py) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## `Account.key`, [line 29](../../../../../../../backend/src/sro/domain/execution/account.py#L29): Note

> The vault key today (`secret_key_of`, `domain/execution/secrets.py`) is
> `{tenant}/{origin}/{field}`. Two systems behind one identity provider share
> an origin (the IdP's), so their passwords land on the same key; two
> operators signed in to the same system share a key too, so the second
> operator's saved state overwrites the first's. Putting the username in the
> key -- `{tenant}/{origin}/{username}/password|state` -- gives each account
> its own row for both.
>
> The username is casefolded (`lena@example.com` and `Lena@Example.com` are
> one account, not two) and percent-encoded with `/` and every character
> outside `@+-_` (and the always-unreserved letters, digits and `_.-~`)
> escaped, so a username can never inject a path segment -- `a/../b` cannot
> reach another account's key.

## `K_LEASE_TTL`, [line 13](../../../../../../../backend/src/sro/domain/execution/account.py#L13): Constant

> Two minutes. Holders heartbeat a lease every 30 s (§5.2); a lease that has
> gone four heartbeats without one is a holder that crashed or a worker that
> was killed mid-step, not a slow one, so the sweeper is free to release it
> for the next acquire.

## `K_VAULT_VALUE_BYTES`, [line 15](../../../../../../../backend/src/sro/domain/execution/account.py#L15): Constant

> 64 KiB, the write limit of the vault backend (Secret Manager). A saved
> session state (cookies and localStorage) is checked against this before
> the write is attempted, so an oversized state fails with a clear reason
> instead of a vault error surfacing three calls away.

## `Account.lock_id`, [line 36](../../../../../../../backend/src/sro/domain/execution/account.py#L36): Note

> `pg_advisory_lock` takes a signed 64-bit integer, not a string, so the
> account's key is hashed (SHA-256, first 8 bytes, big-endian, signed) into
> one. Two accounts collide only if two distinct keys hash to the same 8
> bytes -- not a risk this deployment's account count reaches.
