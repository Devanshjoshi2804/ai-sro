# Notes for `backend/src/sro/application/runtime/broker.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/broker.py`](../../../../../../../backend/src/sro/application/runtime/broker.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_CLOSE_S`, [line 56](../../../../../../../backend/src/sro/application/runtime/broker.py#L56): Note

> How long closing an old account context may take before the broker
> gives up on it and carries on. The S5 review watched one account's hung
> page hold a sibling's disposal for 15 s and more; the root cause was
> Playwright attaching to every target (`SteelClient._browser_call`), and
> with raw CDP a disposal takes about 0.01 s. Five seconds is several
> hundred of those: the bound is for a Steel that stops answering, and
> nothing an account does may hold another account up past it. A context
> that outlives it is logged and left to its container; its lease is
> already expired or broken, so nothing opens a tab on it again.

## `K_HEADERS_WAIT_S`, [line 57](../../../../../../../backend/src/sro/application/runtime/broker.py#L57): Note

> The bound `headers` gives `PageDriver.headers_for` (spec §5.7): the API
> lane's own budget for a header a page never sends, not a sleep the
> driver waits out regardless -- `headers_for` returns the moment it sees
> one. `headers` takes the full `url`, scheme included, because
> `cookies_for` needs it for Secure and Path; `fresh=True` takes a `mark`
> before reloading the tab and asks only for a token sent after it.
> `needs` passes the token names the caller's write carried through to
> `headers_for`, which waits within this bound until each has been seen.

## `SessionBroker`, [line 139](../../../../../../../backend/src/sro/application/runtime/broker.py#L139): Note

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

## `K_CODE_WAIT`, [line 58](../../../../../../../backend/src/sro/application/runtime/broker.py#L58): Constant

> How long a sign-in that asked for a one-time code keeps its page and its
> account for the person answering it. Codes sent by mail or text are
> commonly valid for five to ten minutes; ten covers the code's own life,
> and a code that outlives it is no use to the page anyway. The lease's
> `expires_at` is set to it once, when the lease starts waiting; `beat`
> never shortens it (`SqlBrowserSessionRepository.beat`), and past it the
> account is taken over like any expired lease.

## `SessionBroker.reauth`, [line 379](../../../../../../../backend/src/sro/application/runtime/broker.py#L379): Note

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
> and gets `AccountBusy`, one ask instead of one per queued run. That park
> lasts only until the parking run's `RunSteps.release`, which ends it as the
> run starts to wait (L1): a run asking a person anything but a code holds
> no lease, so a later holder reaches `_sign_in`, finds the refusal latched
> and asks for the password itself. Retrying the step once afterwards is the
> executor's (D2), not the broker's.
>
> The tab's call log is forgotten once the sign-in lands, the same as
> `resume`: the password POST went through this tab, and leaving it in the
> log would let a step from before the re-sign-in confirm a write against
> a call the account never actually made under its new session.

## `SessionBroker.recover`, [line 418](../../../../../../../backend/src/sro/application/runtime/broker.py#L418): Note

> The run's tab is gone (`PageGone` from `reattach`): the account goes
> back through `acquire`. That is already the S7 rule, in one place: a
> READY lease whose context the pool still lists gets a fresh tab under the
> same lease, and only a context the pool no longer lists -- a crashed or
> restarted container -- is settled BROKEN, closed, and replaced by a
> fresh context with the vault's saved state restored. A broken lease is
> never reused: its context is gone with the Chrome that held it, and a
> READY row cannot tell that, only the pool's list can.

## `SessionBroker.resume`, [line 427](../../../../../../../backend/src/sro/application/runtime/broker.py#L427): Note

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

## `SessionBroker._wait_for_a_person`, [line 690](../../../../../../../backend/src/sro/application/runtime/broker.py#L690): Note

> The lease moves to WAITING with `expires_at` at `K_CODE_WAIT`, in one
> compare-and-set `settle`, before the caller hears about it, so no other
> caller can mistake it for an orphan in between. A lease that is no
> longer live cannot wait: `PageGone`. `_park` is shared with `reauth`'s
> password-refusal path, which parks the same way but never raises
> `WaitingForAPerson` itself -- it re-raises whatever `_sign_in` raised.

## `SessionBroker._recover`, [line 503](../../../../../../../backend/src/sro/application/runtime/broker.py#L503): Note

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

## `SessionBroker._recorded`, [line 602](../../../../../../../backend/src/sro/application/runtime/broker.py#L602): Note

> The account is where the password is typed -- the identity provider's
> origin that `recorded_login` reads off the credential gesture -- with the
> username the recorded job typed, built by `Account.of`, the same function
> `PUT /v1/secrets` builds the panel's key with (tested key for key). No
> recorded sign-in that lands on the start page, or one that recorded no
> username, is `NeedsAPerson`: typing somebody's password under a guessed
> username is the one thing never to do. A recorded sign-in that is not
> the given account's is refused for the same reason: the chain types the
> recorded username.

## `SessionBroker._sign_in`, [line 623](../../../../../../../backend/src/sro/application/runtime/broker.py#L623): Note

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

## `SessionBroker._save_state`, [line 719](../../../../../../../backend/src/sro/application/runtime/broker.py#L719): Note

> Cookies and localStorage go to the vault under the account's `state` key,
> and only if they fit `K_VAULT_VALUE_BYTES`. A state over the limit is not
> split across keys: the fallback is a fresh sign-in the next time the
> context is lost (spec §12), which costs a sign-in and never a partial
> state that restores half a session. The log line names the account and
> the size, never the state.

## `SessionBroker._reclaim`, [line 755](../../../../../../../backend/src/sro/application/runtime/broker.py#L755): Note

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

## `SessionBroker._sign_in`, [line 647](../../../../../../../backend/src/sro/application/runtime/broker.py#L647): Note

Code: `await self._driver.forget_headers_before(`

> The token floor: a driver mark taken just before the sign-in is
> submitted (and before any one-time code a person types for it) is handed
> to the driver, which then never answers a token from a request numbered
> at or below it. A CSRF or bearer token the page sent before the session
> was renewed is so never replayed after it. The request log is not
> cleared instead: that would also drop the fresh tokens the page sends
> while the sign-in lands. The driver owns the floor because it owns the
> log: the same key, the same lifetime, and `forget` clears both.
>
> ponytail: the floor is per process (the driver is one per process). A
> run in another process gets one 419, its reauth finds the page signed
> in, and its fresh retry succeeds; keep the floor with the lease row if
> that one wasted call ever matters.

## `SessionBroker.reauth`, [line 415](../../../../../../../backend/src/sro/application/runtime/broker.py#L415): Note

Code: `if back_to is not None:`

> A UI or sight lane retried after the sign-in must act on the step's own
> page, not the start page the sign-in ended on; the executor names that
> page as `back_to` and the tab goes there last, still under the lock.

## `SessionBroker.acquire`, [line 166](../../../../../../../backend/src/sro/application/runtime/broker.py#L166): Note

> `park=False` is a caller nothing will resume -- a lookup, which lives
> inside the request that asked. For it a sign-in that needs a person (a
> one-time code, a refused or missing password, in `acquire` or `reauth`) is a
> `NeedsAPerson` it reports as a gap; the account is never parked WAITING,
> so no run on it is turned away for ten minutes behind a question nobody was
> asked. It also attaches to a live lease without taking it: the beat keeps
> the run's holder (`holder=None`), where a run attaching renames it.
>
> A sign-in apart (`patience_s`) that fails leaves its failure in `SignIns` for the
> next ask to hear once. It is news for `K_FAILURE` (ten minutes) -- a refusal heard
> a day later hides a sign-in that would work -- and a write to the account's vault
> (a new password through `ForgetsRefusalOnWrite`, wired to `SignIns.forget` in
> `build_container`) clears it at once: the person fixed what failed.

## `SessionBroker._beaten`, [line 492](../../../../../../../backend/src/sro/application/runtime/broker.py#L492): Note

> A tab is owned from the moment it opens: if the beat does not keep the
> lease -- or is cancelled, a caller's budget running out between the open
> and the beat -- the `finally` closes the tab. `_signed_in` does the same for
> a sign-in, and `_ready` for the settle after it.

## `SessionBroker._ready`, [line 562](../../../../../../../backend/src/sro/application/runtime/broker.py#L562): Note

Code: `except BaseException:`

> A lease is READY only when its context is signed in, for every exit: a
> sign-in that was cancelled, timed out, needed a person or had its password
> refused leaves the context on a sign-in page (or a code prompt), and a READY
> lease there is one every later ask attaches to and finds signed out. So each
> of them settles it BROKEN and closes the context (`_broken`); only a park on a
> one-time code (`WaitingForAPerson`) keeps its lease, WAITING, for the person
> who will answer it. The code-asked latch in the vault, not a standing lease,
> is what stops a second password being typed at a code-guarded account. `reauth`
> follows the same rule for a re-sign-in that ends short of signed in.

## `SessionBroker._sign_in`, [line 645](../../../../../../../backend/src/sro/application/runtime/broker.py#L645): Note

Code: `if not park and since is not None and self._clock.now() - since < K_CODE_WAIT:`

> The code-asked latch (`CodeAsked`, the `RefusedCredentials` shape in the
> same vault). Once a system has asked this account for a one-time code, a
> caller nothing will resume -- a lookup -- does not type the password again
> until `K_CODE_WAIT` has passed: every password typed at a code-guarded
> account sends its owner another code or push, and a question a minute would
> be a push a minute (MFA fatigue, and an identity provider's lockout). The
> gap names the code instead. A run parks and asks as before. A sign-in that
> lands -- `_sign_in` to its end, or `resume` after a person typed the code --
> clears the latch.

## `SessionBroker.signed_out`, [line 295](../../../../../../../backend/src/sro/application/runtime/broker.py#L295): Note

> Whether the tab shows a sign-in page (a password form, a code prompt, or
> the identity provider's trip). A lookup asks before it photographs: an
> attached lease may be READY on a context whose session has lapsed or is
> waiting on a code, and a picture of a login form is not an answer.

## `SessionBroker.unpark`, [line 471](../../../../../../../backend/src/sro/application/runtime/broker.py#L471): Note

Code: `and lease.waits_for == waits_for`

> Ends a park at once: under the account's lock, and only while the lease
> is still WAITING for what the caller names (a `resume` that won the lock
> first leaves it READY and untouched), its deadline moves to now and it is
> expired in the same commit, then its context is closed with its page. A
> lease is per account, so another run may have parked it on a one-time code
> meanwhile; a password answer never ends that park. The next acquire signs
> in afresh on a new lease.

## `SessionBroker.resume`, [line 432](../../../../../../../backend/src/sro/application/runtime/broker.py#L432): Note

Code: `if lease is None or lease.state is not LeaseState.WAITING or lease.waits_for != "code":`

> Only a park on a one-time code is resumed. A park on a password is ended by
> the parking run's `release` as it starts to wait, or by the password being
> stored (`unpark`) when that release never ran.

## `SessionBroker._park`, [line 712](../../../../../../../backend/src/sro/application/runtime/broker.py#L712): Note

Code: `holder=lease.holder,`

> A park names the run that parked it, so only that run's end or answer
> ends it. Every `Held` a run is handed names that run as the lease's holder
> (`reattach`, `_beaten`, `_ready`, `resume`), because the row's own holder is
> whoever beat last among the runs sharing the account's lease.


## `SessionBroker._sign_in`, [line 663](../../../../../../../backend/src/sro/application/runtime/broker.py#L663): Note

Code: `f"signing in to {account.origin} stopped at '{step.says}': {result.reason}"`

> A failed step on a page that is no longer a sign-in page. The page is read once
> when the step fails and that read is the one the tail judges (a second read could
> catch the page on its way back to the form, and a password refusal would be
> latched for one never submitted). A failed step is not "signed in" until the
> page, sent to the start url, reads as not a sign-in page again: a magic-link
> page, an IdP error page or a callback error has no password box either, and
> nothing is saved to the vault for it. If it still is one, a person is needed
> and nothing is latched as refused. QA 2026-10-02: a cold lookup stopped at "Type the password: no strategy and no
> repair matched" after 34 s, and the very next lookup attached to the lease it
> left and read in 2.5 s -- the context WAS signed in. The recorded chain is a
> way to a signed-in page (here Keycloak -> B2C -> the app, where the identity
> provider's own session can finish the sign-in while a step is still looking for
> its control). When a step finds nothing to act on and the page now says it is
> not a sign-in page, the chain ends there and the tail judges the page as it
> always did. A page still asking for a password or a code keeps the old answer:
> a person is needed, and nothing is latched as refused.
