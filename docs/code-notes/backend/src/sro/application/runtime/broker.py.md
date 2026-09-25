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
> 1. A READY, unexpired lease is attached: a new tab first, then a
>    `beat`. Opening the tab is the liveness check Chrome answers; the
>    database cannot, since a READY row outlives a crashed container. A
>    dead context raises `PageGone` before any beat, so a lease is never
>    extended while its session is dead (S7 review, C2). A beat that fails
>    means the lease was taken; the tab is closed and the lock path runs.
> 2. Otherwise, under the account lock (S3), where every session change
>    happens: a lease that meanwhile turned READY is attached; an expired
>    one is taken over through `expire` then a fresh claim, never `settle`
>    (S2). A live lease that cannot be attached is settled BROKEN and
>    replaced at once: a READY one whose tab is `PageGone` sits on a dead
>    context, and a SIGNING_IN one is orphaned by construction, because
>    only `_ready` makes SIGNING_IN leases and it resolves each one before
>    it lets go of the lock (S7 review, I1; no timer, and not `expire`,
>    whose time guard S2 froze). Either way its context is closed.
> 3. A fresh context on the account's pinned container (the container of
>    its latest lease, any state; least-loaded for a new account), a
>    SIGNING_IN lease, the saved state restored from the vault, the start
>    page opened and probed by structure (S6), the recorded chain replayed
>    only if the probe shows a sign-in page, the state saved, the lease
>    settled READY.
>
> Anything that fails after the claim settles the lease BROKEN and closes
> its context, so the next run starts clean rather than attaching to a
> half-signed session. The close runs even when the settle itself fails
> (the database down), so no context is left behind (M4).
>
> Capacity is counted from the live leases of every tenant on each
> container (`busy_containers`), after the old lease is settled, so a
> context being replaced does not count against its own replacement.
>
> The probe tab is the first run's tab: it is already on the start page
> and signed in, and closing it only for the run to open the same page
> again is two more tab operations on a container whose Steel has crashed
> on early tab closes (S5). Its call log is forgotten at the handover:
> the sign-in POST carries the password in its body, and nothing may keep
> it past the sign-in (S7 review, M2).
>
> A one-time-code prompt still ends in `NeedsAPerson` with the context
> closed, so the page asking for the code is gone. Keeping it needs a
> lease state that waits for a person, which I1's orphan rule rules out
> for SIGNING_IN; that belongs to D9 or S8 (S7 review, M5).
>
> `Lease.steel_session_id` is the container's real Steel session, the one
> the pool opened the context in; the context lives only in `context_id`.
> The stray sweeper keeps every session a live lease names, and the broker
> never releases one (S7 review, I3).

## `SessionBroker._recover`, [line 116](../../../../../../../backend/src/sro/application/runtime/broker.py#L116): Note

> `PageGone` from `open_tab` does not only mean the context is dead:
> `driver.py`'s `open_tab` also raises it when a tab fails to attach
> within its time limit on a busy Chrome, or when the new tab's renderer
> crashed -- both times the context itself is still alive (S7 rereview,
> N1). Settling the lease BROKEN and disposing the context on every
> `PageGone` broke every other run on the account mid-step for a transient
> failure, and cost a fresh sign-in it did not need.
>
> The structural signal the pool already has decides it: a context still
> in `pool.contexts(lease.container_url)` gets a fresh tab in the same
> context, under the same lease, rather than the lease being broken. Only
> a context the pool's own list confirms gone falls back to `_ready`'s
> settle-and-reprovision path. A `PageGone` from the retry's own tab is
> not caught here: the context is confirmed alive, so a second failure on
> it is not this function's case to handle and reaches `acquire`'s caller.

## `SessionBroker._recorded`, [line 200](../../../../../../../backend/src/sro/application/runtime/broker.py#L200): Note

> The account is where the password is typed -- the identity provider's
> origin that `recorded_login` reads off the credential gesture -- with the
> username the recorded job typed, built by `Account.of`, the same function
> `PUT /v1/secrets` builds the panel's key with (tested key for key). No
> recorded sign-in that lands on the start page, or one that recorded no
> username, is `NeedsAPerson`: typing somebody's password under a guessed
> username is the one thing never to do. A recorded sign-in that is not
> the given account's is refused for the same reason: the chain types the
> recorded username.

## `SessionBroker._sign_in`, [line 221](../../../../../../../backend/src/sro/application/runtime/broker.py#L221): Note

> The recorded sign-in job's chain (`sign_in_chain`, audit wave 1 Task 10)
> replayed through the UI lane with the vault password as the step's
> secret -- the path QA uses (parent spec §6.4), not the connection-based
> `SignIn`. A password already refused (`#refused`, fingerprinted to the
> value) is never typed again until a new one is stored. A one-time code
> asks a person before and after. The sign-in form still showing after the
> chain is the refusal, latched on the password's key; it is decided by the
> page's structure (S6), never by its text. Each step beats the lease, so a
> long chain keeps it and a lost lease stops the chain.

## `SessionBroker._save_state`, [line 265](../../../../../../../backend/src/sro/application/runtime/broker.py#L265): Note

> Cookies and localStorage go to the vault under the account's `state` key,
> and only if they fit `K_VAULT_VALUE_BYTES`. A state over the limit is not
> split across keys: the fallback is a fresh sign-in the next time the
> context is lost (spec §12), which costs a sign-in and never a partial
> state that restores half a session. The log line names the account and
> the size, never the state.

## `SessionBroker._reclaim`, [line 291](../../../../../../../backend/src/sro/application/runtime/broker.py#L291): Note

> After every fresh claim, the contexts Chrome still lists on that
> container whose lease rows have ended are disposed. A close that hit
> `K_CLOSE_S`, or a process that died between settling and closing, leaves
> one behind; this is where it goes, at the first claim after a restart and
> at every one after. A context with no lease row is left alone: it may be
> another process's, created a moment before its lease commits. Ceiling:
> such a context from a process that died in that moment stays until the
> Steel session is released; writing the lease before the context would
> close it, at the cost of a nullable `context_id`. Failure to reclaim is
> logged, never the acquire's failure.
