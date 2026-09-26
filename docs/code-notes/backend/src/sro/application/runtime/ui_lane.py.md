# Notes for `backend/src/sro/application/runtime/ui_lane.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/ui_lane.py`](../../../../../../../backend/src/sro/application/runtime/ui_lane.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L1): Docstring

> The UI lane acts on the recorded control through the page code already
> injected into the run's own tab (X1), inside the recorded frame (E3's
> `frame_path`), and confirms the step from conditions -- a matching network
> call, or the control's own state -- never a fixed sleep. `ui_driver.py`'s
> `wait_for_timeout(1200)` after every action is exactly the pattern this
> replaces: every wait here is `wait_for_call` or `wait_for`, both bounded by
> `K_UI_WAIT_S` and both polling a real condition.

## `K_UI_WAIT_S`, [line 37](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L37): Comment

> How long a step waits for its recorded call to show up, or for the control
> to settle into the state it left when recorded (§6.1, §6.2). Not in the
> plan's own named-constants list (Global Constraints #14); the task brief
> names it directly and it binds nothing outside this lane.

## `ui_payload`, [line 41](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L41): Docstring

> What `sroPage.act` is given: the recorded action, the value this run
> supplies, the target evidence, a verified-run locator if one has been
> learned, and the frame the target was recorded in. `by_id` is only used to
> ask `writes` whether this step is a write -- `step` alone does not carry
> that, since a step's own evidence lives in the run's gesture map, not on
> the step.

## `ui_payload`, [line 41](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L41): Comment

> X2's binding rule: `write` is set to `False` only on a step that is not a
> write; a write step omits the key entirely. The page code treats a missing
> `write` as "this is a write" and never repairs it (`page-code.js`'s `find`:
> "no strategy matched, and a write is never repaired"). Setting `write: true`
> explicitly would say the same thing to the page code, but omitting the key
> is what a payload that predates this rule already does, and is what the
> page code's own default branch assumes -- so a caller who forgets the flag
> fails safe into "never repaired" rather than "always repaired".

## `_NOTHING_SENT`, [line 38](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L38): Comment

> The `act` failures that dispatched nothing: no control was found, the
> recorded frame is gone, or -- on evidence with no `frame_path` -- the probe
> found the control in more than one frame and refused to guess which one
> (X4 re-review R2). Only these set `never_left`, so a step that never
> reached the system can be offered to the next lane without asking anyone.
> `not_actionable` is not here: the control was found and acting on it threw
> part way, so something may have happened.

## `UiLane.execute`, [line 85](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L85): Docstring

> One step, one act, one confirmation. `primary_gesture` and `value_for` are
> the same evidence-reading rules every lane uses. A write announces itself
> (`about_to_write`) before anything is sent; from then on, any exception is
> `unknown` with `never_left=False` -- the request may have gone out, and an
> exception counted as a failed lane would let the next lane send it again
> (X4 review I5). `Stopped` and `CancelledError` still propagate: they are
> the run being stopped, not an outcome of the write.

## `UiLane._perform`, [line 118](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L118): Docstring

> The mark is taken before the act, and only calls sent after it count. Of
> those, only the ones matching the recorded call's method and path shape
> (`own`) are this step's: a read takes its values only from its own GET,
> and a write's created record only from its own 201 -- never the first 2xx
> or 201 on the tab, which may be polling, telemetry or an audit trail (X4
> review I2/I3).
>
> A write is `done` only when `write_confirmed` finds its own call with a
> success status. Silence -- the call never came, or the log was lost to a
> reconnect -- is `unknown` (spec §6.2: settled by a read-back or asks). The
> after-state can only take `done` back to `unknown` (the control did not end
> up as recorded, or the match was repaired); it never raises `unknown` or
> `failed` to `done`. A Save button is still visible whether or not the save
> happened, so its state can never stand in for the call (X4 review C1).
>
> A non-write whose after-state does not hold is `failed` with a fingerprint.
> A repaired match is never `done`: it found SOME control above the repair
> threshold, not necessarily the recorded one, so with its state holding or
> no state recorded at all it is `unknown` (X2's binding rule; X4 review I1).

## `UiLane._perform`, [line 118](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L118): Comment

> S6 re-review round 2 (N1): a failed act's own `signals` read can itself
> raise `PageUnsettled` -- the navigation it landed on never settled within
> the driver's own bound. Before any write is attempted (`writes(step,
> ctx.by_id)` is false, so `about_to_write` was never called) the step
> never left, so it is `failed` with `never_left=True`; once
> `about_to_write` has run the step may already have taken effect, so it
> is `unknown`, the same verdict every other unconfirmed write gets.

## `UiLane._holds`, [line 226](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L226): Docstring

> Whether the element `act` touched -- not a fresh resolve -- now shows what
> the recording says it should. `value` wins over `after.value` when set: the
> run may have typed a different value than the one recorded (a parameter),
> and what the control should hold is what THIS run asked for, not what the
> demonstration happened to type. `pin` from the just-received `answer`, not
> from the outgoing `payload`: X2's binding rule ("pass the pin from `act`'s
> answer into `holds`") is what makes `sroPage.holds` check the exact element
> `act` pinned (`globalThis.__sroActed`) instead of re-resolving -- and
> re-resolving is exactly what let a wrong repair verify itself as `done`
> before that fix.

## `confirming`, [line 247](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L247): Docstring

> The keys come from the call that confirmed the write -- the own call whose
> status `write_confirmed` accepts (`accepts`) -- never simply the first own call:
> a refused attempt carrying the field, followed by an accepted retry without it,
> confirms nothing about the field.

## `learned_payload`, [line 65](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L65): Function

> A locator the sight lane learned is looked for in the frame its hit test
> answered, and alone there (`target: {}`, so no recorded resolver and no
> repair runs in that frame). `ui_payload` leaves such a locator out, so the
> recorded locators keep their recorded frame. A learned locator with no
> `frame_path` (learned from evidence or a typed limit) stays in
> `ui_payload`, in the recorded frame, as before.

## `UiLane._perform`, [line 129](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L129): Note

Code: `first = learned_payload(payload, ctx.learned.get(step.order))`

> The learned locator first, in its own frame. Only when that sent nothing
> (`_NOTHING_SENT`: the control or the frame is not there) is the recorded
> payload acted on; any other answer is the step's answer, settled against
> the payload that produced it.

## `UiLane.execute`, [line 98](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L98): Note

Code: `value is None`

> A control that puts a value, on a step that carries parameters, with no
> value bound to it: nothing is typed. Typing `None` would clear the field,
> and the recording's value is never a substitute. Failed, never having
> left, so the step goes to a person rather than into somebody's form.
