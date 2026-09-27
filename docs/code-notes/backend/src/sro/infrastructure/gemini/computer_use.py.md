# Notes for `backend/src/sro/infrastructure/gemini/computer_use.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/gemini/computer_use.py`](../../../../../../../backend/src/sro/infrastructure/gemini/computer_use.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/gemini/computer_use.py#L1): Docstring

> Gemini's computer-use model, asked for exactly one gesture.
>
> The model returns actions from its own fixed set. They are mapped onto the
> ``ActionKind`` the rest of the system already knows, and anything that does not
> map is refused rather than approximated -- a `drag` translated into a click is a
> different gesture performed confidently.
>
> Coordinates come back normalised to 0-1000 and are converted here into the
> screenshot's own pixels, because a normalised coordinate silently means a
> different point on a different viewport.

## module, [line 14](../../../../../../../backend/src/sro/infrastructure/gemini/computer_use.py#L14): Note on the line above

Code: `_ACTIONS: dict[str, ActionKind] = {`

> Its predefined functions to ours. Absence is a refusal, never a nearest
> match: a `drag_and_drop` turned into a click is a different gesture performed
> confidently. Navigation is absent on purpose and excluded at the tool as well.
>
> ``wait_5_seconds`` is handled separately, before this table: it carries no
> coordinates at all, and mapping it onto ``HOVER`` turned "let this finish
> loading" into a real click at whatever an absent x/y defaulted to.

## module, [line 26](../../../../../../../backend/src/sro/infrastructure/gemini/computer_use.py#L26): Note on the line above

Code: `_EXCLUDED = [`

> Predefined functions this rung must not have.
>
> The model requires its own tool -- a plain JSON schema is refused with 400 -- so
> the way to bound it is to remove the functions rather than to ask it politely.
> Navigation is excluded for the reason the step allow-list exists: a gesture
> demonstrated on one screen must not become "go somewhere else and try there".

## `GeminiVisionDriver`, [line 36](../../../../../../../backend/src/sro/infrastructure/gemini/computer_use.py#L36): Docstring

> The SDK is imported inside the adapter: a deployment that sends nothing
> to a hosted model should not load one in order to boot.
>
> Built from a prompt record, `SIGHT` or `SIGHT_ESCALATED`, not a model name:
> the words, the model and the destination all come off the record. The
> escalation to pro is a second record rather than the same record on another
> model because the eval gate measures a record -- each model is measured
> separately, and one record run on two models would be two measurements filed
> under one name.
>
> The goal quotes the step's `says` and the run's values, the history is what
> earlier proposals said, and the visible controls are page text: all three
> are untrusted and go in fences through `Prompt.evidence`.

## `_from_response`, [line 84](../../../../../../../backend/src/sro/infrastructure/gemini/computer_use.py#L84): Docstring

> The model answers with a function call, or with prose meaning it did not act.
>
> Prose is treated as a refusal rather than parsed for intent: a sentence that
> is not a call is the model declining to name a gesture, and guessing one out
> of it is exactly the confident-wrong-action this rung is bounded against.

## `_gesture`, [line 110](../../../../../../../backend/src/sro/infrastructure/gemini/computer_use.py#L110): Docstring

> A named call becomes a gesture, or a refusal. Never an approximation.

## `_from_response`, [line 96](../../../../../../../backend/src/sro/infrastructure/gemini/computer_use.py#L96): Comment

Code: `said = " ".join(`

> Assembled from the text parts rather than `response.text`, which warns
> (correctly) that it is dropping the function call we came for.
