# Notes for `backend/src/sro/domain/observation/mining.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/mining.py`](../../../../../../../backend/src/sro/domain/observation/mining.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/mining.py#L1): Docstring

> What one mining pass cost, kept apart from what it found.

## `MiningPass`, [line 7](../../../../../../../backend/src/sro/domain/observation/mining.py#L7): Docstring

> One reading of one tenant's day, and what it cost.
>
> A pass makes exactly one model call. Every workflow it found names this
> pass rather than carrying a copy of its bill: three workflows out of one
> $0.04 call summed to $0.12 when they each carried it.

## `MiningPass`, [line 13](../../../../../../../backend/src/sro/domain/observation/mining.py#L13): Note on the line above

Code: `thought_tokens: int = 0`

> Inside out_tokens, not beside them.

## `MiningPass`, [line 20](../../../../../../../backend/src/sro/domain/observation/mining.py#L20): Note on the line above

Code: `learned_parameters: int = 0`

> Parameters this pass added to jobs it had seen before.
>
> Kept apart from `kept`, because they answer different questions: `kept` is
> what the pass recognised, this is what it LEARNT. A pass that recognises
> nothing new and widens two parameters did real work, and without this the
> row says it did nothing.
>
> It is also the only figure that can say whether parameter learning is
> getting better. `MineResult` computed it from the first day and the row had
> nowhere to put it, so a pass that learnt three left no record it had --
> measured on 2026-09-09, when the second pass over the real store learnt
> exactly that and the only place the number appeared was a return value in
> a terminal. The rig has the same gap; this is not a port regression, it is
> an inherited one that had to stop here to be measurable at all.

## `MiningPass`, [line 26](../../../../../../../backend/src/sro/domain/observation/mining.py#L26): Note on the line above

Code: `left_out: int = 0`

> How much evidence this pass was shown, and how much the budget dropped.
>
> Beside `coverage`, which is a different question: coverage says where the
> pass's citations fell WITHIN its window, and these say how much of the
> tenant there was to put in one. A pass that left nothing out has read
> everything there was; one that left evidence out has more to say about
> evidence that has not changed, which is what the scheduled sweep reads to
> decide whether to pay for another pass.

## `MiningPass`, [line 27](../../../../../../../backend/src/sro/domain/observation/mining.py#L27): Note on the line above

Code: `unplaced: int = 0`

> How many gestures of its window the pass said it could not place.
>
> Beside `coverage` and `left_out`, which are the other two figures about
> the READING rather than about what it found. This one lived on `Workflow`
> until 2026-09-15, where four readers took the window's leftovers for a
> property of whichever job the model had attached them to and refused to
> serve, schedule or fire it.
>
> The model's own claim, unverified and high by construction: it cites about
> one gesture per step and calls the rest unplaced.

## `MiningPass`, [line 30](../../../../../../../backend/src/sro/domain/observation/mining.py#L30): Note on the line above

Code: `error: str | None = None`

> Why it found nothing, when it found nothing for a reason the API gave.
> An honest zero and a refused call are the same row without this.
