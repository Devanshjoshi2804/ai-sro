# Notes for `backend/src/sro/application/ports/ui.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/ui.py`](../../../../../../../backend/src/sro/application/ports/ui.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/ui.py#L1): Docstring

> Driving the interface, for when replaying the call is not enough.
>
> The port is deliberately about one gesture. A driver that took a whole plan
> would decide for itself what to do when a control could not be found, and that
> decision -- retry, escalate, stop -- belongs where it can be recorded.

## `ResolvedLocator`, [line 12](../../../../../../../backend/src/sro/application/ports/ui.py#L12): Docstring

> A locator with its parameters filled in, ready to try.

## `UiOutcome`, [line 22](../../../../../../../backend/src/sro/application/ports/ui.py#L22): Note on the line above

Code: `matched_by: LocatorStrategy | None = None`

> Which locator worked. Recorded because a step that only ever matches on
> the last fallback is a step about to break.

## `UiOutcome`, [line 24](../../../../../../../backend/src/sro/application/ports/ui.py#L24): Note on the line above

Code: `candidates: int = 0`

> How many controls the winning locator matched. More than one is a
> warning: the driver acted on the first visible match.

## `UiUnavailable`, [line 49](../../../../../../../backend/src/sro/application/ports/ui.py#L49): Docstring

> No browser to drive. Not a ``DomainError``: the plan was fine.
>
> Distinct from "the control was not found", which is a fact about the page
> and means the skill has drifted from the system it was taught on.

## `UiDriver.perform`, [line 30](../../../../../../../backend/src/sro/application/ports/ui.py#L30): Docstring

> Try each locator in order and act on the first that resolves.

## `UiDriver.current_url`, [line 38](../../../../../../../backend/src/sro/application/ports/ui.py#L38): Docstring

> Where the driven browser is, for the run's record.

## `UiDriver.capture`, [line 40](../../../../../../../backend/src/sro/application/ports/ui.py#L40): Docstring

> What is on screen, for a rung that has to look at it.

## `UiDriver.for_session`, [line 42](../../../../../../../backend/src/sro/application/ports/ui.py#L42): Docstring

> The same driver, bound to a particular browser.
>
> Anything that opens its own browser has to drive that one: a driver
> pointed at the deployment's default will navigate one Chrome and look
> at another, which is indistinguishable from a model that cannot see.

## `UiDriver.perform_at`, [line 44](../../../../../../../backend/src/sro/application/ports/ui.py#L44): Docstring

> Act at a point, for a gesture that came from pixels rather than a
> locator. Kept apart from ``perform`` so a coordinate can never be
> mistaken for a control the demonstration actually identified.
