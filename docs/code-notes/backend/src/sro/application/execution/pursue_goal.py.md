# Notes for `backend/src/sro/application/execution/pursue_goal.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/pursue_goal.py`](../../../../../../../backend/src/sro/application/execution/pursue_goal.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L1): Docstring

> Work a goal out on the screen, when nobody has demonstrated it.
>
> The rung below this replays what somebody proved. This one has nothing to
> replay: it opens the screen the catalogue names, looks at it, and proposes one
> gesture at a time until the goal is met or the budget runs out.
>
> Everything that makes the other rungs safe applies here and matters more,
> because nothing about this was demonstrated:
>
> - **A budget.** A fixed number of gestures. A model that has not finished in
>   that many is not about to, and an unbounded loop of a vision model driving a
>   live warehouse is not a thing that should exist.
> - **One system.** The browser starts on the connection's own host and any
>   gesture proposed against another is refused. A model that wandered off the
>   WMS would be acting with the operator's session somewhere nobody agreed to.
> - **The operator said go.** A pursuit whose goal changes anything is refused
>   unless somebody confirmed it, exactly as an assisted run is, and the name on
>   the record comes from the credential rather than from the request.
> - **The breaker applies.** A system whose recent runs have been failing is not
>   driven by this rung either. It used to be the one rung that kept going after
>   every other had been stopped, on a screen nobody had proved anything about.
> - **The model never decides it worked.** ``done`` is a claim, recorded as one.
>   What the run reports is what the screen showed afterwards.
>
> And every gesture and call is captured, so a task worked out once can be
> induced into a skill and replayed over the API the next time. The slow rung
> exists to make itself unnecessary.

## module, [line 34](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L34): Note on the line above

Code: `GESTURE_BUDGET = 12`

> Enough to open a screen, fill a short form and save. Chosen to be obviously
> finite rather than tuned: the number that matters is that there is one.

## module, [line 36](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L36): Note on the line above

Code: `_WAIT_SECONDS = 5`

> What the model means by "wait": time for a screen that is still loading to
> finish, not a gesture at whatever coordinates an absent x/y defaulted to.

## module, [line 38](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L38): Note on the line above

Code: `_STUCK = 3`

> Gestures in a row that change nothing before giving up.
>
> Watching the first live pursuit, the model clicked within a few pixels of the
> same point eight times. Nothing told it the screen had not moved, so nothing
> made it try something else.

## module, [line 40](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L40): Note on the line above

Code: `_ALLOWED = (`

> No navigation. The screen is chosen from the catalogue before anything opens;
> a model that could navigate could take the operator's session anywhere.

## module, [line 306](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L306): Note on the line above

Code: `_SETTLE_TRIES = 8`

> How long the screen is given to arrive. A WMS portal redirects twice through
> an identity provider before it renders, so the first read after `navigate` is
> regularly still `about:blank`.

## module, [line 309](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L309): Note on the line above

Code: `_SETTLE_TICKS = 4`

> How many times a screen is re-read before it is called unchanged.
>
> The driver already waits after acting, and against this application that wait
> was not enough: an ExtJS panel swap took longer than it, so the read came back
> identical and the gesture was recorded as having changed nothing. The model was
> then told its correct click had done nothing, three times, and gave up on a
> screen that had in fact moved every time.
>
> Polled rather than lengthened, because most gestures do land inside the wait
> and paying the slowest case on every one of twelve is most of a minute.

## `Unauthorised`, [line 49](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L49): Docstring

> A pursuit that would change the warehouse, with nobody on the record.
>
> The other rungs replay something a person demonstrated and a person
> confirmed. This one has neither, so the confirmation is all there is.

## `Pursued`, [line 56](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L56): Note on the line above

Code: `reached: bool`

> What the model claimed. Never what the system confirms -- that is the
> screen's job, and a pursuit has no demonstration to assert against.

## `Pursued`, [line 62](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L62): Note on the line above

Code: `recording_id: str = ""`

> The demonstration this pursuit left behind. A task worked out on screen
> is evidence exactly as a taught one is -- the same gestures, the same calls,
> the same capture -- which is what lets the slow rung make itself
> unnecessary.

## `Pursued`, [line 64](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L64): Note on the line above

Code: `skill_id: str = ""`

> The skill induced from it, when it reached the goal and the recording
> carried enough to build one.

## `Pursued`, [line 66](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L66): Note on the line above

Code: `authorized_by: str = ""`

> Who confirmed it, where the goal changes anything. Empty on a pursuit
> that only reads. Taken from the credential, never from the request body:
> whether somebody confirmed is the operator's to say, who they are is not.

## `_settled`, [line 312](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L312): Docstring

> The screen once it has finished reacting, or as it is after long enough.

## `_arrived`, [line 322](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L322): Docstring

> ``None`` once the screen is really there; otherwise why it is not.
>
> Checked because a pursuit is expensive and a blank page is indistinguishable
> from a hard task: self-hosted Steel hands every session the same Chrome, and
> a pursuit handed one sitting on `about:blank` spent its whole budget
> clicking a page that was never loaded.

## `_holds_a_session`, [line 342](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L342): Docstring

> Whether this browser carries the application's own cookie.
>
> The identity provider's cookies are set before anybody signs in, so their
> presence proves nothing. The application's do not exist until a login
> finished.

## `PursueGoal.execute`, [line 101](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L101): Docstring

> ``watching`` is told each gesture as it happens.
>
> A browser being driven on somebody's behalf with nothing on screen for
> two minutes is indistinguishable from a hang.
>
> ``using`` is told which browser this took, so whoever is watching can
> say so -- and so the reaper that releases forgotten sessions can tell
> this one is not forgotten.

## `PursueGoal._keep`, [line 263](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L263): Docstring

> Seal what was recorded, and induce a skill when it proved something.
>
> Only when the goal was reached. A pursuit that ran out of budget half
> way through a form recorded a half-filled form, and inducing a skill
> from that would teach the system to do the wrong thing quickly.

## `PursueGoal._browser_for`, [line 279](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L279): Docstring

> A signed-in browser if this tenant has one, otherwise a new one.
>
> Returns whether it was borrowed, because a borrowed browser is not ours
> to close and its session is not ours to overwrite.
>
> The set searched used to be every browser in the deployment, matched on
> a cookie host. So a pursuit could pick up another tenant's signed-in
> browser, drive it, and capture everything it did into a recording filed
> under the wrong customer.

## `PursueGoal._brief`, [line 291](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L291): Docstring

> The goal, plus the values the operator gave for it.
>
> Given rather than guessed. A model asked to work out a transport mode
> code on screen will invent one, and it will look plausible.

## `PursueGoal._session_of`, [line 297](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L297): Docstring

> The stored session, so the browser starts signed in.
>
> A blank browser sent at a WMS lands on a login page, and a model asked
> to reach a goal from there will try to sign in.

## `PursueGoal.execute`, [line 128](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L128): Comment

Code: `await refuse_if_breaker_is_open(uow, ctx, target_system, now)`

> Before the browser opens, so a system that is failing is not
> driven twelve more times to find that out.

## `PursueGoal.execute`, [line 135](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L135): Comment

Code: `start = connection.base_url`

> The catalogue named a screen on another host. That is a bad entry,
> not an instruction.

## `PursueGoal.execute`, [line 143](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L143): Comment

Code: `session, borrowed = await self._browser_for(ctx, connection)`

> A browser somebody is already signed into, before opening one that is
> not. Restoring cookies into a fresh browser lands on the identity
> provider here -- the WMS does not accept a transplanted session -- so
> a pursuit that opens its own browser spends its whole budget clicking
> a login page, which is exactly what it did.

## `PursueGoal.execute`, [line 144](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L144): Comment

Code: `if using is not None:`

> Claimed, so the reaper leaves it alone: a browser being driven and a
> browser somebody forgot about look identical from outside.

## `PursueGoal.execute`, [line 153](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L153): Comment

Code: `started = await self._start_recording.execute(`

> Recorded exactly as a demonstration is, and before the first
> gesture: what a pursuit does on screen is evidence of the same
> kind an operator's hands produce, and a task worked out once
> should never have to be worked out again.

## `PursueGoal.execute`, [line 165](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L165): Comment

Code: `detail = landed`

> Nothing to look at. Twelve screenshots of a blank page cost a
> model call each and end in "the screen did not change", which
> reads as the task being impossible -- it was the browser.

## `PursueGoal.execute`, [line 195](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L195): Comment

Code: `reached = True`

> A claim, not a verification. A pursuit has no demonstration
> to assert against, so what it reports is what it was told.

## `PursueGoal.execute`, [line 199](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L199): Comment

Code: `gesture = "waited — " + (proposed.reasoning or "letting the screen finish")`

> Not a gesture: nothing was clicked, so nothing about the
> screen not changing afterwards means the model is stuck.

## `PursueGoal.execute`, [line 212](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L212): Comment

Code: `after = await _settled(ui, seen_before)`

> What changed, not only what was attempted. The model was
> being handed its own past coordinates and nothing else, so it
> clicked the same place eight times without ever learning that
> the screen had not moved.

## `PursueGoal.execute`, [line 237](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L237): Comment

Code: `detail = (`

> Three gestures, nothing moved. A model that has not
> affected the screen in three tries is not about to, and
> spending the rest of the budget proves it slowly.

## `PursueGoal.execute`, [line 150](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L150): Comment

Code: `if not borrowed:`

> Never close a browser we did not open: it belongs to whoever
> signed into it, and closing it logs a warehouse operator out.

## `PursueGoal._keep`, [line 275](../../../../../../../backend/src/sro/application/execution/pursue_goal.py#L275): Comment

Code: `logger.info("pursuit %s left nothing to induce: %s", recording_id, refusal)`

> A pursuit that reached its goal without leaving evidence a skill
> can be built from is still a success; it just cannot be repeated
> cheaply yet, and saying so beats a skill nobody can trust.
