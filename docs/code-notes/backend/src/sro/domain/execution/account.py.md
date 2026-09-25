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
> There is no local fallback for a schemeless system any more (there was
> one, `origin_of(system) or system.strip().lower()`, and it is gone):
> `origin_of` itself now retries a schemeless input as `//` + the input, so
> `wms.example`, `WMS.example:443` and `bob:pw@wms.example` all go through
> the one function, the one path, and userinfo is dropped rather than
> lowercased and kept.
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
> `_encoded` percent-encodes with `safe=""`, then also escapes `.` and `~`
> -- the two characters `urllib.parse.quote` always treats as unreserved and
> will not encode on request -- so every character except a letter, a digit,
> `_` or `-` is escaped, `%` included. That makes the encoding injective
> after casefolding: two different usernames can never fold to the same
> key, and a username can never split into more than one path segment --
> `a/../b` becomes one segment, `a%2F%2E%2E%2Fb`, and cannot reach another
> account's key.
>
> This is NOT the Secret Manager adapter's own safe set: `secret_id_for`
> (`infrastructure/vault/secret_manager.py`) rejects `%` too and rewrites it
> to `-`, so two different logical keys can share a physical id's readable
> prefix (`a.b` and the literal username `a-2Eb` both read `a-2eb` there).
> Uniqueness at that layer comes from `secret_id_for`'s own trailing SHA-256
> digest of the full logical key, not from the readable prefix -- the
> logical key only has to be injective, which it is.
>
> ponytail: `casefold` is a ceiling, not a guarantee -- it also joins
> `Straße`/`strasse`, and would join `Lena`/`lena` on a system whose own
> usernames are case-sensitive. Upgrade path if that ever collides two real
> accounts: key on the recorded login's exact spelling instead of a folded
> one, and accept that two spellings of the same account then need their
> own migration.

## `Account.vault_key`, [line 38](../../../../../../../backend/src/sro/domain/execution/account.py#L38): Note

> `as_key` can normalise a field that is only punctuation (`"!!!"`) down to
> the empty string, the same way a blank username would, and for the same
> reason it is refused here rather than silently accepted: a key ending in
> `/` is not one anybody else could ask for on purpose.

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

## `Account.lock_id`, [line 45](../../../../../../../backend/src/sro/domain/execution/account.py#L45): Note

> `pg_advisory_xact_lock` takes a signed 64-bit integer, not a string, so the
> account's key is hashed (SHA-256, first 8 bytes, big-endian, signed) into
> one -- the single-`bigint` form, not the two-`int4` form, because splitting
> the hash in half to add a class id would cut it to 32 bits and make the
> birthday risk real (about 1% at 10,000 accounts); kept whole, it stays
> negligible (about 2.7e-12 at 10,000 accounts).
>
> That single-`bigint` space is also `RUNS_LOCK`'s
> (`container.py:179`, `pg_try_advisory_lock`, one process claiming the
> right to drive runs) -- the two are never split into separate class ids,
> so an account's `lock_id` landing on `5721966` is a real, just
> astronomically unlikely, possibility (about 5e-20 per account). If it ever
> happened, `claim_the_runs` would believe another API process was already
> driving runs. Worth naming if a third advisory lock is ever added here:
> the space is shared by convention, not by a partition the code enforces.

## `Lease.context_id`, [line 71](../../../../../../../backend/src/sro/domain/execution/account.py#L71): Note

> Under the one-container-per-tenant, one-context-per-account ruling,
> `steel_session_id` names the tenant's shared session and is the same for
> every account's lease; it can no longer identify which browser context is
> this account's. Closing or re-attaching to an account's own tab needs its
> own id, so the context id is carried on the lease rather than derived --
> `container_url` and `steel_session_id` stay for now (harmless, if now
> redundant per lease) since S4's `BrowserPool` still expresses close and
> attach in terms of them.

## `LIVE`, [line 62](../../../../../../../backend/src/sro/domain/execution/account.py#L62): Note

> A lease holds its account and its browser context in three states:
> SIGNING_IN while the broker signs in under the lock, READY while runs use
> it, and WAITING while a sign-in's one-time code waits for a person with
> its page kept open (S8). All three count for the one-live-lease index,
> for container capacity, and against reclaiming the context.
