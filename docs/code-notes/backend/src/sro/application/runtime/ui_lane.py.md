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

## `K_UI_WAIT_S`, [line 20](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L20): Comment

> How long a step waits for its recorded call to show up, or for the control
> to settle into the state it left when recorded (§6.1, §6.2). Not in the
> plan's own named-constants list (Global Constraints #14); the task brief
> names it directly and it binds nothing outside this lane.

## `ui_payload`, [line 23](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L23): Docstring

> What `sroPage.act` is given: the recorded action, the value this run
> supplies, the target evidence, a verified-run locator if one has been
> learned, and the frame the target was recorded in. `by_id` is only used to
> ask `writes` whether this step is a write -- `step` alone does not carry
> that, since a step's own evidence lives in the run's gesture map, not on
> the step.

## `ui_payload`, [line 23](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L23): Comment

> X2's binding rule: `write` is set to `False` only on a step that is not a
> write; a write step omits the key entirely. The page code treats a missing
> `write` as "this is a write" and never repairs it (`page-code.js`'s `find`:
> "no strategy matched, and a write is never repaired"). Setting `write: true`
> explicitly would say the same thing to the page code, but omitting the key
> is what a payload that predates this rule already does, and is what the
> page code's own default branch assumes -- so a caller who forgets the flag
> fails safe into "never repaired" rather than "always repaired".

## `UiLane.execute`, [line 54](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L54): Docstring

> One step, one act, one confirmation. `primary_gesture` and `value_for` are
> the same evidence-reading rules every lane uses; what is particular to the
> UI lane is entirely in how it confirms: `write_confirmed` from the network
> first (X3's belt), and only when that comes back `None` -- no matching call
> in this run at all -- does it fall back to `_holds`, the control's own
> state. A `_holds` confirmation is never allowed to overrule a `write_confirmed`
> verdict; the network is always asked first because it is evidence the
> control's own DOM state cannot fake.

## `UiLane.execute`, [line 54](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L54): Comment

> `verdict is None and after is not None`: the network was silent (no call at
> all matched what this step's evidence expects to see) and this step
> recorded what its control should look like once done. `held_ok and not
> answer.repaired` -- X2's binding rule -- is the whole point of carrying
> `repaired` on `PageAnswer`: a repaired match found SOME control that scored
> above the threshold, not necessarily the right one, so its own state
> holding is not proof. Only network confirmation can call a repaired write
> `done`; `_holds` alone leaves it `unknown`.

## `UiLane.execute`, [line 54](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L54): Comment

> The read and navigation half of the ladder is symmetrical: `after is not
> None` is also this step's only source of confirmation once there is no
> recorded call at all to check the network against, and a repaired match is
> just as unconfirmed here as it is for a write -- the reasons in the
> `execute` docstring above.

## `UiLane.execute`, [line 54](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L54): Comment

> S6 re-review round 2 (N1): a failed act's own `signals` read can itself
> raise `PageUnsettled` -- the navigation it landed on never settled within
> the driver's own bound. Before any write is attempted (`writing` is
> false, so `about_to_write` was never called) the step never left, so it
> is `failed` with `never_left=True`; once `about_to_write` has run the
> step may already have taken effect, so it is `unknown`, the same verdict
> every other unconfirmed write gets.

## `UiLane._holds`, [line 146](../../../../../../../backend/src/sro/application/runtime/ui_lane.py#L146): Docstring

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
