# Notes for `backend/src/sro/domain/skill/loop.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/loop.py`](../../../../../../../backend/src/sro/domain/skill/loop.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/loop.py#L1): Docstring

> A block of steps the task does once per thing in a list.
>
> "Adjust every short-shipped line on this order" is one task, and until this
> existed it was not expressible: a skill was a flat list of steps, so two honest
> demonstrations of it -- one order with two short lines, one with three --
> disagreed about how many steps the task has, and induction refused the pair
> saying they were not two runs of one task. They were.
>
> What a loop is here is narrower than it sounds, and deliberately so. The list is
> one an earlier step's *response* carried: the system said which lines are short,
> and the operator acted on each. So the iteration count is the system's own
> answer at run time rather than a number anybody guessed, and every value the
> body sends is a field of the element it is acting on.

## `Binding`, [line 9](../../../../../../../backend/src/sro/domain/skill/loop.py#L9): Docstring

> A parameter of the loop's body, and where in the element it comes from.

## `Binding`, [line 11](../../../../../../../backend/src/sro/domain/skill/loop.py#L11): Note on the line above

Code: `pointer: str`

> A JSON pointer *within one element*, e.g. `/lineId`. Relative because the
> element changes every iteration and the pointer does not.

## `Loop`, [line 22](../../../../../../../backend/src/sro/domain/skill/loop.py#L22): Note on the line above

Code: `over_step_index: int`

> The step whose response carried the list.

## `Loop`, [line 24](../../../../../../../backend/src/sro/domain/skill/loop.py#L24): Note on the line above

Code: `over_pointer: str`

> JSON pointer to the list in that response.

## `Loop`, [line 27](../../../../../../../backend/src/sro/domain/skill/loop.py#L27): Note on the line above

Code: `last_step: int`

> The body, inclusive. Contiguous by construction: a demonstration does the
> steps of one iteration one after another, and a body with a hole in it would
> be two loops somebody has to be able to see separately.

## `Loop.describe`, [line 59](../../../../../../../backend/src/sro/domain/skill/loop.py#L59): Docstring

> For the reviewer, above the band of steps it wraps.
