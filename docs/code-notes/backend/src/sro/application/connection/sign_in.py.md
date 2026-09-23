# Notes for `backend/src/sro/application/connection/sign_in.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/sign_in.py`](../../../../../../../backend/src/sro/application/connection/sign_in.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/sign_in.py#L1): Docstring

> Connect once, stay connected.
>
> Keeping a session alive by refreshing it from every capture only works while
> somebody keeps using the system. Leave it a long weekend and the session dies
> of old age, and the operator is back at a login page -- which is not what a
> connected system means to anybody who has used one.
>
> So the connection can hold credentials, encrypted in the vault, and sign itself
> back in. That is what makes it a connector rather than a saved password: a human
> enters it once, and everything after that -- a demonstration, a batch at 3am, an
> API call that needs a fresh cookie header -- finds the system already open.
>
> The credentials are typed by the driver into the system's own login page. They
> are never logged, never returned by any endpoint, never written into a
> recording, and never sent to any host but the one the connection names.

## `NoCredentials`, [line 23](../../../../../../../backend/src/sro/application/connection/sign_in.py#L23): Docstring

> Nothing stored to sign in with, so nothing can be done unattended.

## `StoreCredentials`, [line 34](../../../../../../../backend/src/sro/application/connection/sign_in.py#L34): Docstring

> Keep what a human typed once, so nothing has to ask them again.

## `SignIn`, [line 50](../../../../../../../backend/src/sro/application/connection/sign_in.py#L50): Docstring

> Open a browser, sign in with what is stored, keep the session it produced.

## `EnsureSignedIn`, [line 128](../../../../../../../backend/src/sro/application/connection/sign_in.py#L128): Docstring

> A session, whatever it takes -- and nothing more than it takes.
>
> Called before anything that needs the system open. If the stored session
> still works it does nothing at all, because signing in again would throw
> away a working session and spend a login and a browser for nothing.
>
> This also used to cite a system that permits one session at a time, where a
> second login would sign the operator's own browser out. Measured on QA on
> 2026-09-23, two logins for the same account in separate browser contexts
> both stayed valid; the behaviour stands on the reasons above without it.

## `_is_a_login`, [line 177](../../../../../../../backend/src/sro/application/connection/sign_in.py#L177): Docstring

> Whether this skill is somebody signing in.
>
> By what it was called and what it was for, because a login recorded before
> the system name was derived properly is still a demonstration of this
> login.

## `SignIn._chooser`, [line 102](../../../../../../../backend/src/sro/application/connection/sign_in.py#L102): Docstring

> What a demonstration of this login clicked before the form appeared.
>
> Azure B2C opens by asking which tenant somebody belongs to, and that
> page offers links rather than fields. Which of them is right is a fact
> about this deployment, so it is read from a recording of somebody
> choosing rather than guessed at -- and where nobody has demonstrated a
> login, nothing is chosen and the driver behaves as before.

## `EnsureSignedIn.for_url`, [line 143](../../../../../../../backend/src/sro/application/connection/sign_in.py#L143): Docstring

> Same, for a caller that knows an address and not a system name.
>
> Which is every teaching session: the operator pastes a URL, and which
> connected system that belongs to is ours to work out, not theirs to
> declare.

## `EnsureSignedIn.execute`, [line 149](../../../../../../../backend/src/sro/application/connection/sign_in.py#L149): Docstring

> True if the system is open. False only when nobody can be asked.

## `SignIn.execute`, [line 87](../../../../../../../backend/src/sro/application/connection/sign_in.py#L87): Comment

Code: `await self._browser.close(session.id)`

> The browser existed to produce a session and has done so. Leaving
> it open would hold the provider's only slot against the next
> demonstration.

## `SignIn.execute`, [line 94](../../../../../../../backend/src/sro/application/connection/sign_in.py#L94): Comment

Code: `if self._life is not None and self._clock is not None:`

> The clock this session is measured against starts here.

## `SignIn._chooser`, [line 106](../../../../../../../backend/src/sro/application/connection/sign_in.py#L106): Comment

Code: `matching = [s for s in skills if _is_a_login(s)]`

> Preferring this system's own demonstration, but not requiring it: the
> login taught here is filed under the system name derived when it was
> sealed, and an early one landed under "ai". Passing an option that
> belongs to another system costs nothing -- the driver clicks only text
> that is actually on the page in front of it.

## `EnsureSignedIn.execute`, [line 152](../../../../../../../backend/src/sro/application/connection/sign_in.py#L152): Comment

Code: `return False`

> An outage is not a login problem, and signing in during one only
> burns the credentials against a system that cannot answer.

## `EnsureSignedIn.execute`, [line 154](../../../../../../../backend/src/sro/application/connection/sign_in.py#L154): Comment

Code: `if await self._ageing(ctx, target_system):`

> Working now, and old enough to stop working during whatever is
> about to be asked of it. Replacing it here costs one login;
> finding out halfway through a batch costs the batch.

## `EnsureSignedIn.execute`, [line 158](../../../../../../../backend/src/sro/application/connection/sign_in.py#L158): Inline

Code: `return True`

> the session we have still works

## `EnsureSignedIn.execute`, [line 164](../../../../../../../backend/src/sro/application/connection/sign_in.py#L164): Comment

Code: `await self._life.died(ctx, system=target_system, at=self._clock.now())`

> It used to work and does not now, which is the only way anybody
> learns how long these last.
