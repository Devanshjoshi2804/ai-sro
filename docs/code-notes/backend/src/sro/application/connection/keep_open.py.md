# Notes for `backend/src/sro/application/connection/keep_open.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/keep_open.py`](../../../../../../../backend/src/sro/application/connection/keep_open.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/keep_open.py#L1): Docstring

> Sign systems back in before their sessions die, not after.
>
> Everything else here reacts: a run fails, a session is refreshed, the run is
> retried. That works and it is not enough -- the first batch of the morning
> should not be the thing that discovers the weekend expired the session, and an
> operator opening the console at 8am should not be looking at a login page.
>
> So a keeper wakes up, asks each connected system whether its session is working
> and how old it is, and replaces the ones that are past half their measured
> life. What "half their life" means is learned per system rather than set here.
>
> It never signs in during an outage, because burning credentials against a
> system that cannot answer is how an account gets locked.
>
> It used to refuse a second thing: signing in while somebody was demonstrating,
> on the premise that this WMS permits one session per account and a server
> login would sign the operator out mid-task. Measured on QA on 2026-09-23
> against the real login chain, two logins for the same account in separate
> browser contexts both stayed valid, so that refusal protected a limit that does
> not exist and was removed. What does exist is a finite browser pool, which is
> why a system can still be left alone (see `Swept.left_alone`).

## module, [line 23](../../../../../../../backend/src/sro/application/connection/keep_open.py#L23): Note on the line above

Code: `KEEPER = PrincipalId("session-keeper")`

> Whose name goes on a login nobody asked for. A refresh is not attributable
> to whoever happened to ask last, and an audit trail that says so is worth the
> one extra constant.

## `Swept`, [line 17](../../../../../../../backend/src/sro/application/connection/keep_open.py#L17): Note on the line above

Code: `left_alone: tuple[str, ...] = ()`

> Systems not signed in this pass because no browser was free to sign in
> with. Until 2026-09-23 this held systems somebody was demonstrating against,
> under the one-session premise; that premise was measured false (see the
> module note) and the field kept its name for the worker's log line.

## `Swept`, [line 20](../../../../../../../backend/src/sro/application/connection/keep_open.py#L20): Note on the line above

Code: `released: tuple[str, ...] = ()`

> Browsers given back because nothing claimed them. This deployment has
> one, and a session that outlived whatever opened it holds it forever.

## `KeepSessionsOpen.sweep`, [line 37](../../../../../../../backend/src/sro/application/connection/keep_open.py#L37): Docstring

> One pass over every connected system, in every tenant.
>
> Nobody is making this request, so there is no tenant to scope it to --
> the keeper reads the connection list itself and acts for each tenant in
> turn, which is the one place in this codebase that crosses that line.
>
> Each tenant's turn is attributed to it (`about`), as `MineLately` does:
> the meter bills a model call to the attributed tenant and refuses one
> nobody is named for, so without it every session-life claim the sweep
> writes lost its embedding (final review I-2, 2026-09-24).

## `KeepSessionsOpen._demonstrating`, [line 64](../../../../../../../backend/src/sro/application/connection/keep_open.py#L64): Docstring

> Whether anybody is teaching right now, anywhere in the deployment.
>
> Only closing a stray capture browser waits for this -- a demonstration's
> own browser can otherwise look exactly like litter in between opening it
> and starting to record. It used to gate lease expiry too (S9 review, M2):
> one demonstration, in any tenant, held up every account's expiry
> everywhere, and a lease nobody was watching kept its context in the one
> Chrome until the demonstration ended. Expiring a lease has nothing to do
> with a demonstration in progress, so `sweep` no longer asks this before
> `expire_leases`, only before `close_strays`.

## `KeepSessionsOpen.sweep`, [line 53](../../../../../../../backend/src/sro/application/connection/keep_open.py#L53): Comment

Code: `released: tuple[str, ...] = ()`

> `expire_leases` always runs (S9): a dead lease's context has nothing to
> do with anybody's demonstration. Only `close_strays` -- the legacy
> capture-browser sweep -- waits for `_demonstrating`, and only when
> nobody is demonstrating: a sign-in opens a browser of its own, and
> reaping between opening and using it would take the slot out from under
> the thing that just asked for it. `expired.steel_sessions`, already
> known, is passed through so a context this same pass just closed for
> its lease is never also treated as an unclaimed capture browser (S9
> review, M6); `expired.contexts` -- never the shared Steel session id a
> sibling lease still names -- is what `released` reports as closed (S9
> re-review round 3, M4).

## `KeepSessionsOpen.sweep`, [line 49](../../../../../../../backend/src/sro/application/connection/keep_open.py#L49): Note on the line above

Code: `except BrowserUnavailable:`

> A demonstration or a run may hold every browser in the pool. That is not
> an outage and not a failed login, and it must not end the sweep for the
> tenants after this one -- the keeper tries again next pass.
