# Notes for `backend/src/sro/domain/connection/connection.py`

Comments and docstrings moved out of [`backend/src/sro/domain/connection/connection.py`](../../../../../../../backend/src/sro/domain/connection/connection.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/connection/connection.py#L1): Docstring

> A system this tenant can reach. See docs/06-glossary.md#connection.

## `ConnectionStatus`, [line 16](../../../../../../../backend/src/sro/domain/connection/connection.py#L16): Note on the line above

Code: `PENDING = "pending"`

> Created; nobody has logged in yet.

## `ConnectionStatus`, [line 18](../../../../../../../backend/src/sro/domain/connection/connection.py#L18): Note on the line above

Code: `CONNECTED = "connected"`

> A session was captured and is believed usable.

## `ConnectionStatus`, [line 20](../../../../../../../backend/src/sro/domain/connection/connection.py#L20): Note on the line above

Code: `EXPIRED = "expired"`

> The session was rejected. A human logs in again, or the login is replayed.

## `Connection`, [line 24](../../../../../../../backend/src/sro/domain/connection/connection.py#L24): Docstring

> A WMS the tenant has authenticated to.
>
> Holds no secret. The session and the login credentials live in the vault; a
> connection holds the *key* to them, so the row is safe to read, log and back
> up. That separation is what lets a recording be kept and a skill be shared.

## `Connection`, [line 35](../../../../../../../backend/src/sro/domain/connection/connection.py#L35): Note on the line above

Code: `failures_acknowledged_at: datetime | None = None`

> When somebody looked at this system's recent failures and said to carry on.
>
> The circuit breaker asks for a person and, without this, gave them nothing
> to do: every run was refused until the window aged out, including the run
> that would have shown the fault was already fixed. Failures before this
> moment stop counting.

## `Connection.acknowledge_failures`, [line 54](../../../../../../../backend/src/sro/domain/connection/connection.py#L54): Docstring

> Close the breaker by a named decision rather than by waiting.
>
> Recorded rather than silent: a breaker that anybody can clear without
> leaving their name is a breaker that stops meaning anything.

## `Connection.cookie_key`, [line 65](../../../../../../../backend/src/sro/domain/connection/connection.py#L65): Docstring

> Where the executor looks for this system's cookie header.
>
> Facility-less: a login is to a system, not to a site, and a skill that
> names `<system>/<facility>/cookie` falls back to this when its site has
> no session of its own.

## `Connection.session_key`, [line 69](../../../../../../../backend/src/sro/domain/connection/connection.py#L69): Docstring

> Vault key holding the captured browser session.

## `Connection.credential_key`, [line 72](../../../../../../../backend/src/sro/domain/connection/connection.py#L72): Docstring

> Vault key for one credential of this system, scoped per tenant.

## `Connection.rejected`, [line 82](../../../../../../../backend/src/sro/domain/connection/connection.py#L82): Docstring

> The stored session no longer works.
>
> Kept as a state rather than deleted: the connection still knows which
> system it is and which vault keys belong to it, and re-authenticating is
> a login, not a re-setup.
