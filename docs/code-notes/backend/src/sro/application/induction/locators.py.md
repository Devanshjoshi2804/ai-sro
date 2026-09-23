# Notes for `backend/src/sro/application/induction/locators.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/locators.py`](../../../../../../../backend/src/sro/application/induction/locators.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/locators.py#L1): Docstring

> Which of a fingerprint's signals are worth replaying by, in what order.
>
> The fingerprint records everything about a control at one moment. Most of it is
> worthless tomorrow: an ExtJS DOM id is assigned in render order, bounds move
> with the window, and a grid cell's text is the record being worked on rather
> than the control's name. What survives is the component the application itself
> addresses, a test id where a team put one, an accessible role and name where the
> framework emits them, and stable visible text.
>
> Two runs are available here, which is what makes this more than a guess: a
> signal that differs between the runs is a property of the record, not of the
> control, so it becomes a parameter rather than a literal or is dropped.

## module, [line 7](../../../../../../../backend/src/sro/application/induction/locators.py#L7): Note on the line above

Code: `_GENERATED_ID = ("ext-gen", "ext-element", "ext-comp")`

> Id prefixes a framework hands out in render order. Never worth recording.

## `build_locators`, [line 10](../../../../../../../backend/src/sro/application/induction/locators.py#L10): Docstring

> Locators for one control, strongest first.
>
> ``other`` is the same step's target from the second demonstration. Where a
> signal differs between the two it is describing the record rather than the
> control: ``value_placeholder`` -- the parameter the diff already created for
> that step's value -- is used in its place if it matches, and otherwise the
> signal is dropped rather than pinned to run one's data.

## `_stable`, [line 55](../../../../../../../backend/src/sro/application/induction/locators.py#L55): Docstring

> The value to record for a signal, or ``None`` to drop it.
>
> Identical across both runs means it belongs to the control. Different means
> it belongs to the record: usable only if the diff already named that value,
> in which case the locator carries the parameter and finds the right row for
> whatever the run is about.
