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

## `NoCredentials`, [line 28](../../../../../../../backend/src/sro/application/connection/sign_in.py#L28): Docstring

> Nothing stored to sign in with, so nothing can be done unattended.

## `StoreCredentials`, [line 39](../../../../../../../backend/src/sro/application/connection/sign_in.py#L39): Docstring

> Keep what a human typed once, so nothing has to ask them again.
>
> One key per password (review round 4, 2026-09-23). When a tagged sign-in job
> records where this system logs in, the password goes to
> `<tenant>/<login origin>/password` -- the key `SignIn` and a run's password
> step read and a refusal is latched on -- so storing here is used, and lifts
> that refusal. Before, it went to the connection's own key, which a recorded
> login never reads. The username is stored under the login origin only when
> the job recorded none; the job's own username wins, as it does in a run. With
> no recorded login, the connection's keys, as before.

## `SignIn`, [line 61](../../../../../../../backend/src/sro/application/connection/sign_in.py#L61): Docstring

> Open a browser, sign in with what is stored, keep the session it produced.

## `EnsureSignedIn`, [line 174](../../../../../../../backend/src/sro/application/connection/sign_in.py#L174): Docstring

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

## `_is_a_login`, [line 223](../../../../../../../backend/src/sro/application/connection/sign_in.py#L223): Docstring

> Whether this skill is somebody signing in.
>
> By what it was called and what it was for, because a login recorded before
> the system name was derived properly is still a demonstration of this
> login.

## `SignIn._chooser`, [line 128](../../../../../../../backend/src/sro/application/connection/sign_in.py#L128): Docstring

> What a demonstration of this login clicked before the form appeared.
>
> Azure B2C opens by asking which tenant somebody belongs to, and that
> page offers links rather than fields. Which of them is right is a fact
> about this deployment, so it is read from a recording of somebody
> choosing rather than guessed at -- and where nobody has demonstrated a
> login, nothing is chosen and the driver behaves as before.

## `EnsureSignedIn.for_url`, [line 189](../../../../../../../backend/src/sro/application/connection/sign_in.py#L189): Docstring

> Same, for a caller that knows an address and not a system name.
>
> Which is every teaching session: the operator pastes a URL, and which
> connected system that belongs to is ours to work out, not theirs to
> declare.

## `EnsureSignedIn.execute`, [line 195](../../../../../../../backend/src/sro/application/connection/sign_in.py#L195): Docstring

> True if the system is open. False only when nobody can be asked.

## `SignIn.execute`, [line 110](../../../../../../../backend/src/sro/application/connection/sign_in.py#L110): Comment

Code: `await self._browser.close(session.id)`

> The browser existed to produce a session and has done so. Leaving
> it open would hold the provider's only slot against the next
> demonstration.

## `SignIn.execute`, [line 117](../../../../../../../backend/src/sro/application/connection/sign_in.py#L117): Comment

Code: `if self._life is not None and self._clock is not None:`

> The clock this session is measured against starts here.

## `SignIn._chooser`, [line 132](../../../../../../../backend/src/sro/application/connection/sign_in.py#L132): Comment

Code: `matching = [s for s in skills if _is_a_login(s)]`

> Preferring this system's own demonstration, but not requiring it: the
> login taught here is filed under the system name derived when it was
> sealed, and an early one landed under "ai". Passing an option that
> belongs to another system costs nothing -- the driver clicks only text
> that is actually on the page in front of it.

## `EnsureSignedIn.execute`, [line 198](../../../../../../../backend/src/sro/application/connection/sign_in.py#L198): Comment

Code: `return False`

> An outage is not a login problem, and signing in during one only
> burns the credentials against a system that cannot answer.

## `EnsureSignedIn.execute`, [line 200](../../../../../../../backend/src/sro/application/connection/sign_in.py#L200): Comment

Code: `if await self._ageing(ctx, target_system):`

> Working now, and old enough to stop working during whatever is
> about to be asked of it. Replacing it here costs one login;
> finding out halfway through a batch costs the batch.

## `EnsureSignedIn.execute`, [line 204](../../../../../../../backend/src/sro/application/connection/sign_in.py#L204): Inline

Code: `return True`

> the session we have still works

## `EnsureSignedIn.execute`, [line 210](../../../../../../../backend/src/sro/application/connection/sign_in.py#L210): Comment

Code: `await self._life.died(ctx, system=target_system, at=self._clock.now())`

> It used to work and does not now, which is the only way anybody
> learns how long these last.

## `SignIn.execute`, [line 88](../../../../../../../backend/src/sro/application/connection/sign_in.py#L88): Comment

Code: `if (standing := await refusals.standing(key)) is not None:`

> A password already refused is not submitted again -- not by the keeper's
> next pass, not by `EnsureSignedIn`, not by anyone -- until that vault key is
> written again (see `ForgetsRefusalOnWrite`). Checked before a browser is
> opened, so a latched connection costs nothing.
>
> The key is the one `_credentials` actually read the password from, so the
> latch lands on the same key the run engine and the panel use.
>
> The message names the system, the login host that needs a new password and
> its vault key -- never the password -- so the operator knows where to store
> a new one (review round 4).

## `SignIn.execute`, [line 106](../../../../../../../backend/src/sro/application/connection/sign_in.py#L106): Comment

Code: `except CredentialsRefused as refused:`

> Only a refusal is latched. Any other failure leaves the password usable.

## `SignIn._credentials`, [line 143](../../../../../../../backend/src/sro/application/connection/sign_in.py#L143): Docstring

> Sign in the way the deployed tenant does (review round 3, 2026-09-23): the
> username the tagged sign-in job recorded, and the password stored under that
> job's login origin, `<tenant>/<login origin>/password` -- the key a run's
> password step reads and the panel's password box writes. Measured on the
> deployed tenant the same day: the connection-level keys were empty, and the
> only stored password was under the login origin.
>
> The connection's own keys are the fallback only when the job knows nothing
> (no tagged job, or neither a username nor a password for it). A job that
> knows half names the missing half rather than borrowing a different
> credential from the connection. A job that recorded no username (a sensitive
> field redacted it) reads the one `StoreCredentials` kept beside the
> password, under the login origin.
>
> Returns the login host too, for the refusal message.

## `_recorded`, [line 228](../../../../../../../backend/src/sro/application/connection/sign_in.py#L228): Docstring

> The recorded login for this connection, read from the tenant's tagged
> sign-in jobs and their evidence. See `recorded_login` for which one. A
> module function so `StoreCredentials` and `SignIn` resolve the same login.

## `_key`, [line 239](../../../../../../../backend/src/sro/application/connection/sign_in.py#L239): Docstring

> The vault key a recorded login keeps a field under -- the one a run reads.
