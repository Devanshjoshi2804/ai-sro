# Notes for `backend/src/sro/application/runtime/broker.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/broker.py`](../../../../../../../backend/src/sro/application/runtime/broker.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_CLOSE_S`, [line 51](../../../../../../../backend/src/sro/application/runtime/broker.py#L51): Note

> How long closing an old account context may take before the broker
> gives up on it and carries on. The S5 review watched one account's hung
> page hold a sibling's disposal for 15 s and more; the root cause was
> Playwright attaching to every target (`SteelClient._browser_call`), and
> with raw CDP a disposal takes about 0.01 s. Five seconds is several
> hundred of those: the bound is for a Steel that stops answering, and
> nothing an account does may hold another account up past it. A context
> that outlives it is logged and left to its container; its lease is
> already expired or broken, so nothing opens a tab on it again.

## `K_HEADERS_WAIT_S`, [line 52](../../../../../../../backend/src/sro/application/runtime/broker.py#L52): Note

> The bound `headers` gives `PageDriver.headers_for` (spec §5.7): the API
> lane's own budget for a header a page never sends, not a sleep the
> driver waits out regardless -- `headers_for` returns the moment it sees
> one. `headers` takes the full `url`, scheme included, because
> `cookies_for` needs it for Secure and Path; `fresh=True` takes a `mark`
> before reloading the tab and asks only for a token sent after it.
> `needs` passes the token names the caller's write carried through to
> `headers_for`, which waits within this bound until each has been seen.

## `SessionBroker`, [line 56](../../../../../../../backend/src/sro/application/runtime/broker.py#L56): Note

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
> A one-time-code prompt keeps its page: the lease moves to WAITING
> (`_wait_for_a_person`), its tab and context stay open, and the caller
> gets `WaitingForAPerson`. A WAITING lease found under the lock is not an
> orphan the way a SIGNING_IN one is -- nobody is expected to hold the lock
> for it, a person is expected to answer -- so while the pool still lists
> its context the caller gets `AccountBusy` and queues (D8); once its own
> deadline passes, `expire` takes it over like any other; a WAITING lease
> whose context the pool no longer lists is settled BROKEN as before
> (S7 review, M5).
>
> `Lease.steel_session_id` is the container's real Steel session, the one
> the pool opened the context in; the context lives only in `context_id`.
> The stray sweeper keeps every session a live lease names, and the broker
> never releases one (S7 review, I3).

## `K_CODE_WAIT`, [line 53](../../../../../../../backend/src/sro/application/runtime/broker.py#L53): Constant

> How long a sign-in that asked for a one-time code keeps its page and its
> account for the person answering it. Codes sent by mail or text are
> commonly valid for five to ten minutes; ten covers the code's own life,
> and a code that outlives it is no use to the page anyway. The lease's
> `expires_at` is set to it once, when the lease starts waiting; `beat`
> never shortens it (`SqlBrowserSessionRepository.beat`), and past it the
> account is taken over like any expired lease.

## `SessionBroker.reauth`, [line 150](../../../../../../../backend/src/sro/application/runtime/broker.py#L150): Note

> A step found the session signed out (the API lane's 401/403/419, or
> `expired(signals, recorded_page)` on the UI lane): the run's tab is
> reloaded at the start page under the account lock, and only a tab that
> still shows a sign-in page signs in. Every run on the account shares one
> context, so the first run through the lock signs every tab back in; the
> runs queued behind it reload, find the page signed in, and go on. That
> is why each waiter reloads before it decides, rather than acting on the
> failure it saw before it waited: its failure is already stale.
>
> The lease is read again under the lock. A lease no longer live is
> `PageGone` (the caller recovers); a WAITING one means another run's
> sign-in is waiting for a person's code, and signing in again would send
> a second code and throw the first page away, so the caller gets
> `AccountBusy` and queues. A refused password is latched by `_sign_in`
> (the vault's `#refused` key), so a caller that reaches `_sign_in` again
> gets `NeedsAPerson` at once without retyping. A `NeedsAPerson(kind=
> "password")` out of `_sign_in` also parks the lease WAITING, the same
> `_park` the one-time-code path uses -- so a caller queued behind the
> lock never reaches `_sign_in` at all; it sees the WAITING lease first
> and gets `AccountBusy`, one ask instead of one per queued run. Retrying
> the step once afterwards is the executor's (D2), not the broker's.
>
> The tab's call log is forgotten once the sign-in lands, the same as
> `resume`: the password POST went through this tab, and leaving it in the
> log would let a step from before the re-sign-in confirm a write against
> a call the account never actually made under its new session.

## `SessionBroker.recover`, [line 172](../../../../../../../backend/src/sro/application/runtime/broker.py#L172): Note

> The run's tab is gone (`PageGone` from `reattach`): the account goes
> back through `acquire`. That is already the S7 rule, in one place: a
> READY lease whose context the pool still lists gets a fresh tab under the
> same lease, and only a context the pool no longer lists -- a crashed or
> restarted container -- is settled BROKEN, closed, and replaced by a
> fresh context with the vault's saved state restored. A broken lease is
> never reused: its context is gone with the Chrome that held it, and a
> READY row cannot tell that, only the pool's list can.

## `SessionBroker.resume`, [line 181](../../../../../../../backend/src/sro/application/runtime/broker.py#L181): Note

> The hook D5's answer calls once a person has dealt with the one-time
> code on the page `WaitingForAPerson` named (its `held` carries the lease
> and tab ids). Filling the code is the answerer's, not the broker's.
>
> The lease read before the lock can be stale by the time this holds the
> account lock, so `lease.live(now)` is checked again under the lock,
> against the same clock `_wait_for_a_person` set the deadline from.
> The sweeper (S9) can expire this same lease the moment its deadline
> passes, without taking this lock at all, so a snapshot check alone is
> not enough: settling it back to READY off a page nobody looked at for
> however long it sat past its deadline would revive a lease the rest of
> the system already treats as abandoned. Past its deadline, `resume`
> never touches this lease again: it goes through `_ready`, under the
> same held lock, which expires the stale row with its own compare-and-set
> and does a normal fresh acquire and sign-in.
>
> Otherwise, the page decides what it is asking for by the same structural
> signals `_sign_in` uses, not by `a_sign_in_page` alone: a visible
> one-time-code field asks again (`WaitingForAPerson`, the lease left
> WAITING until the same deadline); a page that shows some other sign-in
> form -- a password prompt, most likely a refusal, since the account was
> mid-code -- goes down `_sign_in`'s own refusal path (`NeedsAPerson`,
> `kind="password"`) rather than being asked for a code again until the
> deadline runs out. Otherwise the lease is settled READY with a fresh
> `now + K_LEASE_TTL` deadline, in one compare-and-set guarded on the old
> deadline not yet having passed -- before the tab goes to the start page,
> not after -- so this settle and the sweeper's own expiring compare-and-set
> (which needs the deadline already past) exclude each other: whichever
> commits first is the one that happens, never both. A lost settle, or a
> `beat` that comes back false after the goto and the save, is `PageGone`:
> the lease was swept out from under this call. Otherwise the state is
> saved, the tab's call log forgotten (the code went through it), and the
> lease beaten again for the resuming run.

## `SessionBroker._wait_for_a_person`, [line 383](../../../../../../../backend/src/sro/application/runtime/broker.py#L383): Note

> The lease moves to WAITING with `expires_at` at `K_CODE_WAIT`, in one
> compare-and-set `settle`, before the caller hears about it, so no other
> caller can mistake it for an orphan in between. A lease that is no
> longer live cannot wait: `PageGone`. `_park` is shared with `reauth`'s
> password-refusal path, which parks the same way but never raises
> `WaitingForAPerson` itself -- it re-raises whatever `_sign_in` raised.

## `SessionBroker._recover`, [line 226](../../../../../../../backend/src/sro/application/runtime/broker.py#L226): Note

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
>
> ponytail: a context the pool still lists but that can never open a tab in
> (Chrome accepted the context but its renderer is wedged) is never broken
> here -- every call retries the same tab open and reaches the caller as
> `PageGone` again. The lease is never taken over. This is bounded, not
> unbounded: D2's step retry policy retries a fixed number of times inside
> the run's own start-to-close budget (`K_STEP_LIMIT_S`), so a wedged
> context costs that run its budget rather than looping forever. Upgrade
> path if this bites: count consecutive `PageGone`s per lease and settle
> BROKEN past a threshold, the same structural signal `_ready` already
> uses for a container the pool no longer lists.

## `SessionBroker._recorded`, [line 318](../../../../../../../backend/src/sro/application/runtime/broker.py#L318): Note

> The account is where the password is typed -- the identity provider's
> origin that `recorded_login` reads off the credential gesture -- with the
> username the recorded job typed, built by `Account.of`, the same function
> `PUT /v1/secrets` builds the panel's key with (tested key for key). No
> recorded sign-in that lands on the start page, or one that recorded no
> username, is `NeedsAPerson`: typing somebody's password under a guessed
> username is the one thing never to do. A recorded sign-in that is not
> the given account's is refused for the same reason: the chain types the
> recorded username.

## `SessionBroker._sign_in`, [line 339](../../../../../../../backend/src/sro/application/runtime/broker.py#L339): Note

> The recorded sign-in job's chain (`sign_in_chain`, audit wave 1 Task 10)
> replayed through the UI lane with the vault password as the step's
> secret -- the path QA uses (parent spec §6.4), not the connection-based
> `SignIn`. A password already refused (`#refused`, fingerprinted to the
> value) is never typed again until a new one is stored. A one-time code,
> before the chain or after it, keeps the page open and waits for a person
> (`_wait_for_a_person`). The sign-in form still showing after the
> chain is the refusal, latched on the password's key; it is decided by the
> page's structure (S6), never by its text. Each step beats the lease, so a
> long chain keeps it and a lost lease stops the chain.

## `SessionBroker._save_state`, [line 402](../../../../../../../backend/src/sro/application/runtime/broker.py#L402): Note

> Cookies and localStorage go to the vault under the account's `state` key,
> and only if they fit `K_VAULT_VALUE_BYTES`. A state over the limit is not
> split across keys: the fallback is a fresh sign-in the next time the
> context is lost (spec §12), which costs a sign-in and never a partial
> state that restores half a session. The log line names the account and
> the size, never the state.

## `SessionBroker._reclaim`, [line 438](../../../../../../../backend/src/sro/application/runtime/broker.py#L438): Note

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
