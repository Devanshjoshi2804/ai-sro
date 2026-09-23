# Notes for `backend/src/sro/application/execution/vision_step.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/vision_step.py`](../../../../../../../backend/src/sro/application/execution/vision_step.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/vision_step.py#L1): Docstring

> The last rung: finish a step by looking at the screen.
>
> Reached only when the demonstration's own locators no longer find anything, and
> bounded on every side, because this is the least predictable thing in the system
> pointed at a live warehouse:
>
> - **A budget.** A fixed number of gestures per step. A model that has not
>   finished in that many is not about to.
> - **Allowed actions only.** The step's own gesture plus the ones needed to reach
>   it. A step demonstrated as a click cannot become a navigation.
> - **No writes without authorisation.** Same rule as every other rung: a stage
>   that may not write may not click either.
> - **Every call recorded.** What was sent, what came back, what was redacted
>   first -- whether or not the call worked.
>
> What the model is never allowed to do is decide the step succeeded. `done` is
> recorded as a claim; the assertions from the demonstration are what verify.

## module, [line 15](../../../../../../../backend/src/sro/application/execution/vision_step.py#L15): Note on the line above

Code: `GESTURE_BUDGET = 5`

> Per step. Chosen to be obviously finite rather than tuned: the point is that
> an unbounded loop of a vision model driving a WMS is not a thing that exists.

## module, [line 17](../../../../../../../backend/src/sro/application/execution/vision_step.py#L17): Note on the line above

Code: `_REACHING = (ActionKind.SCROLL, ActionKind.HOVER)`

> Allowed alongside the step's own gesture, because a control can be off
> screen. Deliberately excludes navigation: a step that was demonstrated as a
> click must not become "go somewhere else and try there".

## `PerformWithVision.execute`, [line 44](../../../../../../../backend/src/sro/application/execution/vision_step.py#L44): Docstring

> `ui` is the browser this run is performed in, when that is not the
> deployment's own -- a run bound to a device is performed in somebody's
> Chrome, and the rung that looks has to look at the same screen the rungs
> below it were driving.

## `PerformWithVision.execute`, [line 122](../../../../../../../backend/src/sro/application/execution/vision_step.py#L122): Comment

Code: `return VisionResult(`

> A claim, not a verification. The step's assertions decide.
