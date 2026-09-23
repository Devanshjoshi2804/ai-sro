# Notes for `backend/src/sro/application/execution/self_heal.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/self_heal.py`](../../../../../../../backend/src/sro/application/execution/self_heal.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/self_heal.py#L1): Docstring

> Repair the session a run needs, once, and write down what was learned.
>
> The loop this replaces was done by hand: read the failing step, notice the
> redirect to a login page, take a browser, sign in, observe what the application
> sends, put it in the vault, run it again. Every part of that is mechanical, and
> none of it needed the person it took.
>
> What makes it safe to automate is what it is *not* allowed to touch. A remedy
> recovers something the target system owns -- a session, a token, the page the
> application calls from. It never edits a step, a parameter or an assertion:
> those are evidence from a demonstration, and evidence is changed by
> demonstrating again. So the worst a wrong diagnosis can do is waste one retry.
>
> Once per step, and once per run for the same remedy, because a system that
> signs you out twice in a minute is telling you something a third login will not
> fix.
>
> And it is not silent. Every heal is recorded on the step it repaired, and what
> it proved -- that this endpoint needs this header, that this system rotates its
> session -- goes to the knowledge store, so the next run reads it instead of
> rediscovering it. That is the difference between a retry and a brain.

## `Healed`, [line 24](../../../../../../../backend/src/sro/application/execution/self_heal.py#L24): Note on the line above

Code: `detail: str`

> What was actually done, for the step's record. Names no value.

## `Healed`, [line 26](../../../../../../../backend/src/sro/application/execution/self_heal.py#L26): Note on the line above

Code: `repaired: bool = True`

> False when the symptom was diagnosed and the repair did not happen.
>
> Worth returning rather than swallowing: a read that came back 302 was
> reported to the operator as "assertion_failed", which describes the
> assertion and not the reason -- the session was gone, and the healer could
> not take a browser to renew it because the provider had none to give. Both
> of those are things a person can act on; "assertion_failed" is not.

## `HealBudget`, [line 30](../../../../../../../backend/src/sro/application/execution/self_heal.py#L30): Docstring

> One attempt per step, one per remedy per run.
>
> Not a rate limit. A second identical failure after a successful repair means
> the diagnosis was wrong, and the useful thing then is a person reading one
> clear failure rather than a log of six.

## `SelfHeal.attempt`, [line 61](../../../../../../../backend/src/sro/application/execution/self_heal.py#L61): Docstring

> Repair what the symptom points at, or return None and leave it alone.

## `SelfHeal._mark_expired`, [line 111](../../../../../../../backend/src/sro/application/execution/self_heal.py#L111): Docstring

> Say on the connection what a run just proved about its session.
>
> Called only for `REFRESH_SESSION`, and the caller does that gating: a
> missing minted header or a permission the operator does not have says
> nothing about whether the login still works, and marking those expired
> would send somebody to sign in again over a problem signing in cannot
> fix.

## `SelfHeal._refresh_context`, [line 135](../../../../../../../backend/src/sro/application/execution/self_heal.py#L135): Docstring

> Take what the application sends beside its cookies, without a login.
>
> Deliberately not a sign-in: on a system that permits one session at a
> time, signing in again to fix a token would sign the operator's own
> browser out. If the session itself is gone this returns nothing and the
> step fails honestly.

## `SelfHeal._load`, [line 160](../../../../../../../backend/src/sro/application/execution/self_heal.py#L160): Docstring

> The stored session, so the browser starts where the operator left it.
>
> A blank browser sent to the application lands on a login page and mints
> nothing worth having.

## `SelfHeal._learn`, [line 168](../../../../../../../backend/src/sro/application/execution/self_heal.py#L168): Docstring

> What the repair proved about the system, for the next run to read.
>
> Observed rather than reproduced: one repair shows the system behaves
> this way once. A second run that heals the same way is what makes it a
> habit, and the store's own supersession rules handle that.

## `SelfHeal.attempt`, [line 83](../../../../../../../backend/src/sro/application/execution/self_heal.py#L83): Comment

Code: `return None`

> Escalation is the run's decision, not a repair: it changes which
> rung performs the task, and the table that governs it already
> exists.

## `SelfHeal.attempt`, [line 99](../../../../../../../backend/src/sro/application/execution/self_heal.py#L99): Comment

Code: `if finding.remedy is Remedy.REFRESH_SESSION:`

> The session is gone and could not be brought back. Written on the
> connection, because until now nothing ever reached
> `ConnectionStatus.EXPIRED` -- the enum existed, `rejected()`
> existed, and no caller anywhere called it. So a console that had
> said "connected" the day the session died went on saying it
> through every run that discovered otherwise, and the one screen
> somebody checks before asking why a task stopped working was the
> one screen that did not know.

## `SelfHeal._apply`, [line 126](../../../../../../../backend/src/sro/application/execution/self_heal.py#L126): Comment

Code: `return None`

> An outage is not a session problem, and signing in during one
> spends the credentials against a system that cannot answer.

## `SelfHeal._apply`, [line 128](../../../../../../../backend/src/sro/application/execution/self_heal.py#L128): Comment

Code: `return await self._refresh_context(ctx, target_system, facility)`

> The session is alive and the call was still turned away, so
> what expired is what the executor carries beside it -- the
> token the page mints, the context in the Referer. Signing in
> again would do nothing at best and, on a system that permits
> one session, take the operator's browser down at worst.
>
> Found by watching this fire against the live WMS: the healer
> reported success and the retry came back 302 all the same.

## `SelfHeal._refresh_context`, [line 143](../../../../../../../backend/src/sro/application/execution/self_heal.py#L143): Comment

Code: `session, borrowed = await self._browsers.take(ctx)`

> A provider with no browser to give is not "no repair available": it
> is the reason, and it is reported rather than swallowed.

## `SelfHeal._refresh_context`, [line 146](../../../../../../../backend/src/sro/application/execution/self_heal.py#L146): Comment

Code: `await self._browser.restore(session.id, await self._load(ctx, connection))`

> A borrowed browser is somebody's own, already signed in.
> Restoring stored cookies over the top of it replaces a live
> session with an older one.

## `SelfHeal._refresh_context`, [line 148](../../../../../../../backend/src/sro/application/execution/self_heal.py#L148): Comment

Code: `cookies = list(await self._browser.session_cookies(session.id))`

> Both, from this browser, in this order. A token minted in one
> session and a cookie kept from another authenticate nothing: the
> first attempt at this took the token alone, reported success, and
> the retry was refused exactly as before.

## `SelfHeal._refresh_context`, [line 145](../../../../../../../backend/src/sro/application/execution/self_heal.py#L145): Comment

Code: `if not borrowed:`

> Never one we did not open: it belongs to whoever signed into it,
> and closing it logs a warehouse operator out mid-shift.
