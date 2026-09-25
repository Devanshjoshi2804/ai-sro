# Notes for `backend/src/sro/application/runtime/broker.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/broker.py`](../../../../../../../backend/src/sro/application/runtime/broker.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_CLOSE_S`, [line 41](../../../../../../../backend/src/sro/application/runtime/broker.py#L41): Note

> How long closing an old account context may take before the broker
> gives up on it and carries on. The S5 review watched one account's hung
> page hold a sibling's disposal for 15 s and more; the root cause was
> Playwright attaching to every target (`SteelClient._browser_call`), and
> with raw CDP a disposal takes about 0.01 s. Five seconds is several
> hundred of those: the bound is for a Steel that stops answering, and
> nothing an account does may hold another account up past it. A context
> that outlives it is logged and left to its container; its lease is
> already expired or broken, so nothing opens a tab on it again.

## `SessionBroker`, [line 44](../../../../../../../backend/src/sro/application/runtime/broker.py#L44): Note

> One account, one lease, one browser context in its tenant's Steel
> container; every run on that account is a tab in that context (§5.3).
> `acquire` is the order the spec gives:
>
> 1. A READY, unexpired lease is attached with a new tab -- after a
>    `beat`. The beat is the liveness check: it is a compare-and-set on a
>    live state, and whoever takes a lease over expires it first (also a
>    compare-and-set), so a beat that succeeds means nobody has closed the
>    context and a tab is never opened on one whose lease is not live.
> 2. Otherwise, under the account lock (S3), where every session change
>    happens: a lease that meanwhile turned READY is attached; an expired
>    one is taken over through `expire` then a fresh claim, never `settle`
>    (S2), and its context closed; a lease still SIGNING_IN and unexpired
>    under the lock belongs to a holder that died mid sign-in, and is
>    `AccountBusy` until its TTL runs out (at most `K_LEASE_TTL`).
> 3. A fresh context on the account's pinned container (the container of
>    its latest lease, any state; least-loaded for a new account), a
>    SIGNING_IN lease, the saved state restored from the vault, the start
>    page opened and probed by structure (S6), the recorded chain replayed
>    only if the probe shows a sign-in page, the state saved, the lease
>    settled READY.
>
> Anything that fails after the claim settles the lease BROKEN and closes
> its context, so the next run starts clean rather than attaching to a
> half-signed session.
>
> The probe tab is the first run's tab: it is already on the start page
> and signed in, and closing it only for the run to open the same page
> again is two more tab operations on a container whose Steel has crashed
> on early tab closes (S5).
>
> `Lease.steel_session_id` carries the context id: the pool hands back the
> id it opens and closes by, and the container's own Steel session is
> never the broker's to release.

## `SessionBroker._recorded`, [line 164](../../../../../../../backend/src/sro/application/runtime/broker.py#L164): Note

> The account is where the password is typed -- the identity provider's
> origin that `recorded_login` reads off the credential gesture -- with the
> username the recorded job typed, built by `Account.of`, the same function
> `PUT /v1/secrets` builds the panel's key with (tested key for key). No
> recorded sign-in that lands on the start page, or one that recorded no
> username, is `NeedsAPerson`: typing somebody's password under a guessed
> username is the one thing never to do. A recorded sign-in that is not
> the given account's is refused for the same reason: the chain types the
> recorded username.

## `SessionBroker._sign_in`, [line 185](../../../../../../../backend/src/sro/application/runtime/broker.py#L185): Note

> The recorded sign-in job's chain (`sign_in_chain`, audit wave 1 Task 10)
> replayed through the UI lane with the vault password as the step's
> secret -- the path QA uses (parent spec §6.4), not the connection-based
> `SignIn`. A password already refused (`#refused`, fingerprinted to the
> value) is never typed again until a new one is stored. A one-time code
> asks a person before and after. The sign-in form still showing after the
> chain is the refusal, latched on the password's key; it is decided by the
> page's structure (S6), never by its text. Each step beats the lease, so a
> long chain keeps it and a lost lease stops the chain.

## `SessionBroker._save_state`, [line 229](../../../../../../../backend/src/sro/application/runtime/broker.py#L229): Note

> Cookies and localStorage go to the vault under the account's `state` key,
> and only if they fit `K_VAULT_VALUE_BYTES`. A state over the limit is not
> split across keys: the fallback is a fresh sign-in the next time the
> context is lost (spec §12), which costs a sign-in and never a partial
> state that restores half a session. The log line names the account and
> the size, never the state.
