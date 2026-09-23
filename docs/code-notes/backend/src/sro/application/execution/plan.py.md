# Notes for `backend/src/sro/application/execution/plan.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/plan.py`](../../../../../../../backend/src/sro/application/execution/plan.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/plan.py#L1): Docstring

> Which step a run performs next, when some of them are done once per thing.
>
> A run's log is positional: the first thing performed is position 0, the second
> is position 1, and that is what makes "has this already been done" answerable
> after a crash. Without loops the position and the step of the plan are the same
> number, which is every skill taught before loops existed.
>
> With a loop they part company, and the expansion cannot be computed up front:
> how many times the body runs is the length of a list the system itself returns
> partway through. So it is computed from what the run has learned so far, and it
> grows as the run goes.

## `Next`, [line 13](../../../../../../../backend/src/sro/application/execution/plan.py#L13): Note on the line above

Code: `values: dict[str, str]`

> What this step is performed with: the run's own values, and the fields of
> the thing this time round the loop is acting on.

## `Next`, [line 15](../../../../../../../backend/src/sro/application/execution/plan.py#L15): Note on the line above

Code: `of: int = 1`

> How many iterations this loop has in total, for the run to say so.

## `next_step`, [line 18](../../../../../../../backend/src/sro/application/execution/plan.py#L18): Docstring

> The step at the run's next position, or None when there is nothing left.
>
> None also where the plan cannot be expanded yet -- but that cannot happen in
> practice: a loop's list is produced by a step *before* its body, so by the
> time the position reaches the body the count is known. If it ever does, the
> honest answer is to stop rather than to guess a count.

## `total_positions`, [line 49](../../../../../../../backend/src/sro/application/execution/plan.py#L49): Docstring

> How many steps this run will perform, as far as it can be known now.
>
> A hint, not a contract: the count grows when a loop's list arrives. Used for
> saying "step 3 of 7" and nothing that decides anything.
