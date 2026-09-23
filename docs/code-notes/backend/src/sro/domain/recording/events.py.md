# Notes for `backend/src/sro/domain/recording/events.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/events.py`](../../../../../../../backend/src/sro/domain/recording/events.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/events.py#L1): Docstring

> One human action and everything that followed. See docs/06-glossary.md#action-frame.

## `InputAction`, [line 33](../../../../../../../backend/src/sro/domain/recording/events.py#L33): Note on the line above

Code: `modifiers: frozenset[str] = frozenset()`

> ``ctrl``, ``shift``, ``alt``, ``meta`` -- a shift-click is a different action.

## `InputAction`, [line 35](../../../../../../../backend/src/sro/domain/recording/events.py#L35): Note on the line above

Code: `secret: bool = False`

> The value was typed into a credential field.
>
> The one thing capture does not keep. Everything else is evidence of what
> happened; a password is an access token to the customer's system, and
> storing it would turn the evidence plane into a credential store. What is
> recorded is that a credential was entered, and where -- enough to replay the
> step from the vault, and useless to anyone who reads the recording.

## `ActionFrame`, [line 50](../../../../../../../backend/src/sro/domain/recording/events.py#L50): Docstring

> A step of a demonstration, with its complete observable context.

## `ActionFrame`, [line 55](../../../../../../../backend/src/sro/domain/recording/events.py#L55): Note on the line above

Code: `page_url: str | None = None`

> The page this gesture happened on, as the recorder saw it.

## `ActionFrame`, [line 57](../../../../../../../backend/src/sro/domain/recording/events.py#L57): Note on the line above

Code: `ax_graph: AxGraph | None = None`

> The page as the human saw it when they acted.

## `ActionFrame.absorbing`, [line 69](../../../../../../../backend/src/sro/domain/recording/events.py#L69): Docstring

> A copy carrying evidence that arrived after this frame was stored.
>
> Capture is drained on an interval, so a response that finishes just
> after a drain belongs to an action already written down. Without this
> the request is discarded and the step loses the very call the skill
> would replay.

## `ActionFrame.primary_request`, [line 84](../../../../../../../backend/src/sro/domain/recording/events.py#L84): Docstring

> The call this frame is about. See `network.primary_of` for the rule.

## `ActionFrame.errors`, [line 88](../../../../../../../backend/src/sro/domain/recording/events.py#L88): Docstring

> Failure signals in this frame -- the 'why' behind a branch.
