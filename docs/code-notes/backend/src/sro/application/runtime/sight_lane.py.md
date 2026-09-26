# Notes for `backend/src/sro/application/runtime/sight_lane.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/sight_lane.py`](../../../../../../../backend/src/sro/application/runtime/sight_lane.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `ALLOWED`, [line 34](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L34): Constant

> The gestures sight may propose (spec §6.1 Sight). Navigation, dragging and
> anything outside the account's own tab are not offered to the model at all;
> the Computer Use adapter turns anything else it proposes into a refusal.

## `SightLane`, [line 47](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L47): Class

> The last lane: `gemini-3.8-flash` with the Computer Use tool looks at a
> screenshot of the account's own Steel tab and names one point at a time,
> which the driver carries out as CDP mouse and key input in that tab.
>
> - **Action cap.** Each model gets at most `K_SIGHT_ACTIONS` proposals
>   (refusals and waits count); a model that has not finished by then hands
>   over. A `wait` proposal waits on the page settling (`signals`, which
>   waits out the main frame's pending navigation); a page that does not
>   settle ends that model's turn instead of spending the cap on waits.
> - **One escalation.** `flash` first, then `pro` (`gemini-3.1-pro-preview`)
>   once, on the same page, when flash refuses or runs out of actions. Both
>   are built by the container over `metered_client`, so every call is billed
>   and refused by `Meter` once the tenant's daily cap is spent; the lane
>   attributes each call to the run's tenant, workflow and step with
>   `whose.about` so the meter never sees an unattributed call.
> - **A write is sent once.** On a writing step, before every model call and
>   again right before every point, the lane asks the tab's log for a call
>   with the recorded write's method and path shape, from any frame,
>   answered or not (the driver numbers calls when they are SENT). Once one
>   is there sight stops: no further point, no escalation, and the step
>   settles by the own-call rule alone (X7 review C1). The match is broad on
>   purpose, since stopping is the safe direction.
> - **The mark.** Taken right before the first point, not when the step
>   starts, and `mark` forgets the frame the previous step acted in: a call
>   sent while the first screenshot is being read (an autosave) is never this
>   step's call (X7 review I5).
> - **Origin rule.** Home is `scheme://host[:port]` of the primary gesture's
>   recorded URL -- evidence only, never `step.system`, which is model text
>   (X7 review I1), and with the scheme, so an http downgrade on the same
>   host is off the system (M3). The tab is compared with it before every
>   screenshot and again before every point; once it has left, nothing more
>   is shown to the model or done on the page.
> - **Unreachable hits.** A point whose hit test lands in a cross-origin
>   frame is never made (X7 review I2); that model's turn ends. A reachable
>   hit is same-origin by construction, so every point acts in the system.
> - **Secrets.** A step citing any secret gesture is refused before a
>   screenshot is taken: sight never types a credential. A screenshot lives
>   only in the loop iteration that asked about it; it is never logged, put in
>   a result, or kept in the history the model is given.
> - **Settling.** The model saying "done" confirms nothing.
>   - A write is done only by X4's own-call rule (`lanes.same_call`:
>     acting frame, host, path shape, body keys, numbered after the mark)
>     with a wanted status; a 4xx is failed, anything else unknown.
>   - A read is `read` only when its own call answered 2xx.
>   - A step whose primary gesture recorded a move to another page shape is
>     done only when the tab is on that shape now, was not on it at the
>     mark, and every id in the recorded path is confirmed: equal to one of
>     the run's values when the run gave any, else equal to the recorded id
>     (a constant step). The wrong record, or the recorded record on a run
>     that asked for another, is unknown.
>   - Any other step is done only when the recorded locator (with its
>     `frame_path`, strict, never repaired, never a learned locator)
>     resolves to exactly the nearest actionable element under the last
>     point of the primary gesture's kind (the hit's pin), and that control holds the run's value
>     (`value_for`) with the recorded visible and enabled. The right value
>     in the wrong field, a click on any visible element, or a prefilled
>     field that already showed the recording's value are all unknown.
>   - A step where nothing was pointed at is `failed` with `never_left`,
>     since nothing reached the page. Any exception once `about_to_write`
>     has returned is `unknown`, never `never_left`; `Stopped` and
>     cancellation propagate.
> - **Learning.** Only from the element that satisfied the step's check.
>   For a write, that is the last point -- sight stops right after the point
>   its call followed -- and only when that point is of the primary
>   gesture's kind, so a blur-click on Cancel never teaches a typing step.
>   For an element check, the hit it confirmed. A read or a navigation is
>   confirmed by no element and teaches nothing.
> - **Reasons.** A refusal is forgotten once a later point is made, so a
>   step pro acted on never reports flash's refusal (M6).

## `_taught`, [line 373](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L373): Function

> What a hit test teaches (X2 ruling). `None` (nothing, or no unique
> locator) and `unreachable` (a cross-origin frame) teach nothing, and so
> does a hit without its `frame_path`: a locator is never learned apart from
> the frame it was found in. `frame_path` is kept as its JSON text so
> `StepResult.learned` stays a string map. Each hop is kept as its `index`
> and its URL's path only: a live frame's address can carry a session in
> its query, its `;params` or its fragment, and the driver matches a hop by
> `path_shape` and `index` alone, so nothing else is ever stored.

## `SightLane.fill`, [line 86](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L86): Docstring

> Sight for a composed field that exists but will not take the value, through
> `execute`'s own guarded loop (`_guarded`), with the goal `says`, the write's
> page as home, and no `about_to_write` (filling is not writing). The write's
> recorded call is watched: once the model sends it, sight stops acting (X7's
> ruling). After the last point it waits on the write's call the way `execute`
> does, so a Save clicked on the final point is seen; any write call seen makes
> the fill `unknown`, never `done`. It is `done` only when the labelled control
> (`check`, the fill's payload) resolves to exactly the last hit's nearest
> actionable control and holds the value; the locator is learned from that hit.

## `SightLane._guarded`, [line 114](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L114): Docstring

> The one loop both `execute` and `fill` run: drive, wait on the awaited call
> after the last point (so a call the last point caused is in the log before
> settling), settle. An exception after the first point, when a write is watched,
> is `unknown` -- "the write may have gone" -- because the point may have sent it;
> before any point it propagates. `Stopped` and cancellation always propagate.

## `SightLane._drive`, [line 163](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L163): Note

Code: `if await self._sent(held, watched, tried):`

> Checked before the stop: a write already seen going out settles as done
> rather than being left in doubt by a stop that landed after the point.
