# Notes for `backend/src/sro/application/ports/vision.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/vision.py`](../../../../../../../backend/src/sro/application/ports/vision.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/vision.py#L1): Docstring

> The rung below UI replay: a model looking at the screen.
>
> The model **proposes one gesture**. It never touches the browser, never chooses
> when to stop, and never learns what a run is for beyond the step it was asked
> about. Everything it returns is executed by the same driver that executes a
> taught step, so actionability checks and trusted events still apply, and the
> same recording of what happened is produced either way.
>
> One gesture at a time on purpose. A driver handed a whole goal would decide for
> itself when it was finished, and "the model said it was done" is not a
> post-condition anybody can audit.

## `Screen`, [line 10](../../../../../../../backend/src/sro/application/ports/vision.py#L10): Docstring

> What the model is shown. Redacted before it leaves the deployment.

## `Screen`, [line 16](../../../../../../../backend/src/sro/application/ports/vision.py#L16): Note on the line above

Code: `text_digest: str = ""`

> The visible text and control names, when the page yields them. Cheaper
> and more exact than pixels, and the thing to prefer when both exist.

## `ProposedGesture`, [line 23](../../../../../../../backend/src/sro/application/ports/vision.py#L23): Note on the line above

Code: `y: int | None = None`

> Screen coordinates in the screenshot's own pixel space. The adapter
> converts whatever the model returns into these, because a normalised
> coordinate silently means a different pixel on a different viewport.

## `ProposedGesture`, [line 28](../../../../../../../backend/src/sro/application/ports/vision.py#L28): Note on the line above

Code: `done: bool = False`

> The model believes the step is already satisfied. Recorded as a claim,
> never as a verification: what proves a step is the assertion extracted from
> the demonstration.

## `ProposedGesture`, [line 30](../../../../../../../backend/src/sro/application/ports/vision.py#L30): Note on the line above

Code: `refusal: str | None = None`

> The model declined. A refusal is an outcome with a reason, not an error.

## `ProposedGesture`, [line 32](../../../../../../../backend/src/sro/application/ports/vision.py#L32): Note on the line above

Code: `wait: bool = False`

> The model asked to pause rather than act -- a screen still loading, most
> often. Not a gesture with coordinates: a driver that turned this into a
> click "at" wherever an absent x/y defaulted to would perform a real,
> pointless click instead of the wait that was actually asked for.

## `VisionUnavailable`, [line 46](../../../../../../../backend/src/sro/application/ports/vision.py#L46): Docstring

> No vision backend, or egress is switched off for this deployment.
>
> Not a ``DomainError``: the skill and the screen were both fine. Distinct
> from a refusal, which means the model looked and declined.

## `VisionDriver.propose`, [line 36](../../../../../../../backend/src/sro/application/ports/vision.py#L36): Docstring

> One gesture towards ``goal``, given what is on screen now.
