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

## `StoreCredentials.execute`, [line 57](../../../../../../../backend/src/sro/application/connection/sign_in.py#L57): Note on the line above

Code: `raise Conflict(`

> A different username than the job recorded is refused, not ignored (fix
> round 5, 2026-09-23). A run types the job's recorded username; silently
> keeping the password while dropping the given username would pair another
> account's password with it -- a refused sign-in on the next run, typed by
> nobody who could see why. Nothing is stored, and the message names the job
> and login origin but neither username nor password. The same username, or a
> job that recorded none, proceeds. The comparison ignores case (task 10,
> 2026-09-24): identity providers match usernames case-insensitively, so
> `OPERATOR-7` against a recorded `operator-7` is the same account, not a 409.
> `SignIn.execute` checks and writes refusals with the password's
> fingerprint (fix round 2), so a refusal only stands for the password it
> refused.

## `SignIn`, [line 68](../../../../../../../backend/src/sro/application/connection/sign_in.py#L68): Docstring

> Open a browser, sign in with what is stored, keep the session it produced.

## `EnsureSignedIn`, [line 183](../../../../../../../backend/src/sro/application/connection/sign_in.py#L183): Docstring

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

## `_is_a_login`, [line 232](../../../../../../../backend/src/sro/application/connection/sign_in.py#L232): Docstring

> Whether this skill is somebody signing in.
>
> By what it was called and what it was for, because a login recorded before
> the system name was derived properly is still a demonstration of this
> login.

## `SignIn._chooser`, [line 137](../../../../../../../backend/src/sro/application/connection/sign_in.py#L137): Docstring

> What a demonstration of this login clicked before the form appeared.
>
> Azure B2C opens by asking which tenant somebody belongs to, and that
> page offers links rather than fields. Which of them is right is a fact
> about this deployment, so it is read from a recording of somebody
> choosing rather than guessed at -- and where nobody has demonstrated a
> login, nothing is chosen and the driver behaves as before.

## `EnsureSignedIn.for_url`, [line 198](../../../../../../../backend/src/sro/application/connection/sign_in.py#L198): Docstring

> Same, for a caller that knows an address and not a system name.
>
> Which is every teaching session: the operator pastes a URL, and which
> connected system that belongs to is ours to work out, not theirs to
> declare.

## `EnsureSignedIn.execute`, [line 204](../../../../../../../backend/src/sro/application/connection/sign_in.py#L204): Docstring

> True if the system is open. False only when nobody can be asked.

## `SignIn.execute`, [line 119](../../../../../../../backend/src/sro/application/connection/sign_in.py#L119): Comment

Code: `await self._browser.close(session.id)`

> The browser existed to produce a session and has done so. Leaving
> it open would hold the provider's only slot against the next
> demonstration.

## `SignIn.execute`, [line 126](../../../../../../../backend/src/sro/application/connection/sign_in.py#L126): Comment

Code: `if self._life is not None and self._clock is not None:`

> The clock this session is measured against starts here.

## `SignIn._chooser`, [line 141](../../../../../../../backend/src/sro/application/connection/sign_in.py#L141): Comment

Code: `matching = [s for s in skills if _is_a_login(s)]`

> Preferring this system's own demonstration, but not requiring it: the
> login taught here is filed under the system name derived when it was
> sealed, and an early one landed under "ai". Passing an option that
> belongs to another system costs nothing -- the driver clicks only text
> that is actually on the page in front of it.

## `EnsureSignedIn.execute`, [line 207](../../../../../../../backend/src/sro/application/connection/sign_in.py#L207): Comment

Code: `return False`

> An outage is not a login problem, and signing in during one only
> burns the credentials against a system that cannot answer.

## `EnsureSignedIn.execute`, [line 209](../../../../../../../backend/src/sro/application/connection/sign_in.py#L209): Comment

Code: `if await self._ageing(ctx, target_system):`

> Working now, and old enough to stop working during whatever is
> about to be asked of it. Replacing it here costs one login;
> finding out halfway through a batch costs the batch.

## `EnsureSignedIn.execute`, [line 213](../../../../../../../backend/src/sro/application/connection/sign_in.py#L213): Inline

Code: `return True`

> the session we have still works

## `EnsureSignedIn.execute`, [line 219](../../../../../../../backend/src/sro/application/connection/sign_in.py#L219): Comment

Code: `await self._life.died(ctx, system=target_system, at=self._clock.now())`

> It used to work and does not now, which is the only way anybody
> learns how long these last.

## `SignIn.execute`, [line 95](../../../../../../../backend/src/sro/application/connection/sign_in.py#L95): Comment

Code: `if (standing := await refusals.standing(key, password)) is not None:`

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

## `SignIn.execute`, [line 113](../../../../../../../backend/src/sro/application/connection/sign_in.py#L113): Comment

Code: `except CredentialsRefused as refused:`

> Only a refusal is latched. Any other failure leaves the password usable.

## `SignIn._credentials`, [line 152](../../../../../../../backend/src/sro/application/connection/sign_in.py#L152): Docstring

> Sign in the way the deployed tenant does (review round 3, 2026-09-23): the
> username the tagged sign-in job recorded, and the password stored under that
> job's login origin, `<tenant>/<login origin>/password` -- the key a run's
> password step reads and the panel's password box writes. Measured on the
> deployed tenant the same day: the connection-level keys were empty, and the
> only stored password was under the login origin.
>
> The connection's own keys are the fallback only when the job knows nothing
> (no tagged job lands on this system, or neither a username nor a password for it). A job that
> knows half names the missing half rather than borrowing a different
> credential from the connection. A job that recorded no username (a sensitive
> field redacted it) reads the one `StoreCredentials` kept beside the
> password, under the login origin.
>
> Returns the login host too, for the refusal message.

## `_recorded`, [line 237](../../../../../../../backend/src/sro/application/connection/sign_in.py#L237): Docstring

> The recorded login for this connection, read from the tenant's tagged
> sign-in jobs and their evidence. See `recorded_login` for which one. A
> module function so `StoreCredentials` and `SignIn` resolve the same login.
>
> The evidence is each job's cited gestures plus the tenant's gestures from
> its first cite to `K_SITTING_GAP_S` after its last: where a sign-in landed
> is read off the doing right after it, which the job itself leaves uncited
> (`checks.signs_in_to`).

## `_key`, [line 248](../../../../../../../backend/src/sro/application/connection/sign_in.py#L248): Docstring

> The vault key a recorded login keeps a field under -- the one a run reads.
