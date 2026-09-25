# Notes for `backend/src/sro/application/runtime/sight_lane.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/sight_lane.py`](../../../../../../../backend/src/sro/application/runtime/sight_lane.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `ALLOWED`, [line 29](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L29): Constant

> The gestures sight may propose (spec §6.1 Sight). Navigation, dragging and
> anything outside the account's own tab are not offered to the model at all;
> the Computer Use adapter turns anything else it proposes into a refusal.

## `SightLane`, [line 40](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L40): Class

> The last lane: `gemini-3.8-flash` with the Computer Use tool looks at a
> screenshot of the account's own Steel tab and names one point at a time,
> which the driver carries out as CDP mouse and key input in that tab.
>
> - **Action cap.** Each model gets at most `K_SIGHT_ACTIONS` proposals
>   (refusals and waits count); a model that has not finished by then hands
>   over. There is no sleep between proposals: every proposal takes a fresh
>   screenshot, and the only waiting is the named deadline on the write's own
>   call (`K_UI_WAIT_S`).
> - **One escalation.** `flash` first, then `pro` (`gemini-3.1-pro-preview`)
>   once, on the same page, when flash refuses or runs out of actions. Both
>   are built by the container over `metered_client`, so every call is billed
>   and refused by `Meter` once the tenant's daily cap is spent; the lane
>   attributes each call to the run's tenant, workflow and step with
>   `whose.about` so the meter never sees an unattributed call.
> - **Origin rule.** The tab's origin is compared with the step's system
>   before every screenshot and again before every point. Once the tab has
>   left it, nothing more is shown to the model or done on the page.
> - **Secrets.** A step citing any secret gesture is refused before a
>   screenshot is taken: sight never types a credential. A screenshot lives
>   only in the loop iteration that asked about it; it is never logged, put in
>   a result, or kept in the history the model is given.
> - **Settling.** The model saying "done" confirms nothing. A write is done
>   only by X4's own-call rule (`ui_lane.same_call`: acting frame, host, path
>   shape, body keys, numbered after the mark) with a wanted status; a 4xx is
>   failed, anything else unknown. A read is `read` only when its own call
>   answered 2xx; otherwise `unknown`. A step where nothing was pointed at
>   is `failed` with `never_left`, since nothing reached the page; any
>   exception after a write's first point is `unknown`.
> - **Learning.** `learned` is the hit test of the last point, and only on a
>   `done` or `read` step: an unconfirmed step teaches nothing.

## `_taught`, [line 204](../../../../../../../backend/src/sro/application/runtime/sight_lane.py#L204): Function

> What a hit test teaches (X2 ruling). `None` (nothing, or no unique
> locator) and `unreachable` (a cross-origin frame) teach nothing, and so
> does a hit without its `frame_path`: a locator is never learned apart from
> the frame it was found in. `frame_path` is kept as its JSON text so
> `StepResult.learned` stays a string map.
