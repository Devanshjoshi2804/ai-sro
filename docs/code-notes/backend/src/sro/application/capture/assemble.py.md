# Notes for `backend/src/sro/application/capture/assemble.py`

Comments and docstrings moved out of [`backend/src/sro/application/capture/assemble.py`](../../../../../../../backend/src/sro/application/capture/assemble.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/capture/assemble.py#L1): Docstring

> Group capture events into ordered ActionFrames.
>
> Grouping rules and their known limits: docs/03-backend-walkthrough.md#frame-assembly.

## module, [line 15](../../../../../../../backend/src/sro/application/capture/assemble.py#L15): Note on the line above

Code: `_NOT_A_STEP = frozenset({ActionKind.SCROLL, ActionKind.HOVER})`

> Gestures that move attention rather than change anything.

## `AssemblyResult`, [line 22](../../../../../../../backend/src/sro/application/capture/assemble.py#L22): Note on the line above

Code: `unattached_requests: tuple[CapturedRequest, ...]`

> Traffic with no preceding action *in this batch*.
>
> Two very different causes, and the caller can tell them apart because it
> knows whether the recording already has frames:
>
> - page-load noise before the first human action, which is genuinely orphaned
> - the tail of the previous action, when a response finished after the last
>   drain. Those belong to the frame that is already stored; dropping them
>   would silently cost that step its network plan, which is the part a skill
>   is actually built from.

## `AssemblyResult`, [line 26](../../../../../../../backend/src/sro/application/capture/assemble.py#L26): Note on the line above

Code: `sources: tuple[InputEvent, ...] = ()`

> The gesture each frame was opened by, in frame order.
>
> Which events survive to become frames is this module's rule -- a scroll is
> dropped, an input at the same instant as its effects sorts before them --
> and a caller that needs to know where a frame came from must not restate
> that rule to find out. A screenshot is joined to its gesture through here,
> by identity rather than by matching a timestamp that two gestures could
> share.

## `assemble_frames`, [line 40](../../../../../../../backend/src/sro/application/capture/assemble.py#L40): Docstring

> Fold events into frames: an input opens one, its effects attach to it.

## `assemble_frames`, [line 48](../../../../../../../backend/src/sro/application/capture/assemble.py#L48): Comment

Code: `continue`

> Moving the viewport is not a step, and treating it as one
> costs the step before it its own evidence: a scroll between a
> click and its responses opens a frame that absorbs them. Two
> runs then attribute the same calls to different steps and the
> diff calls that a divergence.

## `assemble_frames`, [line 55](../../../../../../../backend/src/sro/application/capture/assemble.py#L55): Comment

Code: `open_frames[-1].snapshot = event.snapshot`

> Keep the first: it was taken at action time, which is the
> state the human was looking at when they decided to act.

## `_sort_key`, [line 82](../../../../../../../backend/src/sro/application/capture/assemble.py#L82): Comment

Code: `priority = 0 if isinstance(event, InputEvent) else 1`

> CDP does not order across domains. At an identical timestamp the input is
> the cause, so it must sort before the effects it produced.
