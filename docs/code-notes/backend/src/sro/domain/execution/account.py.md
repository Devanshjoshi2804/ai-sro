# Notes for `backend/src/sro/domain/execution/account.py`

Why the code in [`backend/src/sro/domain/execution/account.py`](../../../../../../../backend/src/sro/domain/execution/account.py) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## `Account.of`, [line 28](../../../../../../../backend/src/sro/domain/execution/account.py#L28): Note

> The origin is built with `origin_of` (`domain/shared/hosts.py`) -- the same
> function `secret_key_of` and the panel's own key already use -- and not a
> function that keeps the scheme. `origin_of` lowercases the host, drops the
> default port and drops any userinfo, so a bare host (what the panel sends,
> `application/execution/plan_step.py`) and a full URL with a different case
> or an explicit `:443` (what a broker reads from a start URL) land on the
> same key. A function that kept the scheme would give one account two keys,
> and the run asking for the password the operator just stored would find
> nothing there.
>
> A blank or whitespace-only username is refused here, not just at the API:
> `Account.of` is the one door every caller uses, HTTP or not, and a caller
> that let a blank one through would build `{tenant}/{origin}//{field}` --
> an unreadable key nobody else can write to on purpose. Refusing past
> `K_USERNAME_MAX_LEN` is the same guard against the same failure at the
> other end: a caller who has a value that long almost certainly does not
> have a username.

## `Account.key`, [line 35](../../../../../../../backend/src/sro/domain/execution/account.py#L35): Note

> `lena@example.com` and `Lena@Example.com` are one account, not two, so the
> username is casefolded before it goes in the key.
>
> `_encoded` percent-encodes with the same safe set the vault's own Secret
> Manager adapter allows (`secret_id_for`, `infrastructure/vault/secret_manager.py`
> -- letters, digits, `_` and `-`, checked against its `_ALLOWED` pattern
> without importing it, since domain code may not depend on infrastructure).
> Everything else -- `/`, `.`, `~`, punctuation -- is escaped, including the
> two characters `urllib.parse.quote` always treats as unreserved and will
> not encode on request. A username can therefore never split into more than
> one path segment: `a/../b` becomes one segment, `a%2F%2E%2E%2Fb`, and
> cannot reach another account's key.
>
> ponytail: `casefold` is a ceiling, not a guarantee -- it also joins
> `Straße`/`strasse`, and would join `Lena`/`lena` on a system whose own
> usernames are case-sensitive. Upgrade path if that ever collides two real
> accounts: key on the recorded login's exact spelling instead of a folded
> one, and accept that two spellings of the same account then need their
> own migration.

## `K_LEASE_TTL`, [line 14](../../../../../../../backend/src/sro/domain/execution/account.py#L14): Constant

> Two minutes. Holders heartbeat a lease every 30 s (§5.2); a lease that has
> gone four heartbeats without one is a holder that crashed or a worker that
> was killed mid-step, not a slow one, so the sweeper is free to release it
> for the next acquire.

## `K_VAULT_VALUE_BYTES`, [line 16](../../../../../../../backend/src/sro/domain/execution/account.py#L16): Constant

> 64 KiB, the write limit of the vault backend (Secret Manager). A saved
> session state (cookies and localStorage) is checked against this before
> the write is attempted, so an oversized state fails with a clear reason
> instead of a vault error surfacing three calls away.

## `K_USERNAME_MAX_LEN`, [line 18](../../../../../../../backend/src/sro/domain/execution/account.py#L18): Constant

> 254, the longest an email address can be end to end under RFC 5321 -- the
> shape every username seen in this codebase so far has had. A bound exists
> so a caller's mistake (a token or a whole cookie pasted where a username
> belongs) is refused with a reason rather than accepted and hashed into a
> key nobody chose on purpose.

## `Account.lock_id`, [line 42](../../../../../../../backend/src/sro/domain/execution/account.py#L42): Note

> `pg_advisory_lock` takes a signed 64-bit integer, not a string, so the
> account's key is hashed (SHA-256, first 8 bytes, big-endian, signed) into
> one. Two accounts collide only if two distinct keys hash to the same 8
> bytes -- not a risk this deployment's account count reaches.

## `Lease.context_id`, [line 67](../../../../../../../backend/src/sro/domain/execution/account.py#L67): Note

> Under the one-container-per-tenant, one-context-per-account ruling,
> `steel_session_id` names the tenant's shared session and is the same for
> every account's lease; it can no longer identify which browser context is
> this account's. Closing or re-attaching to an account's own tab needs its
> own id, so the context id is carried on the lease rather than derived --
> `container_url` and `steel_session_id` stay for now (harmless, if now
> redundant per lease) since S4's `BrowserPool` still expresses close and
> attach in terms of them.
