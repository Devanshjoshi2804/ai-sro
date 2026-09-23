# Notes for `backend/src/sro/application/induction/loops.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/loops.py`](../../../../../../../backend/src/sro/application/induction/loops.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/loops.py#L1): Docstring

> Reading a loop off two demonstrations that did the same block a different
> number of times.
>
> "Adjust every short-shipped line on this order" is one task, and two honest
> demonstrations of it disagree about how many steps it has. Induction refused
> that pair outright -- *the runs are not two runs of one task* -- which was the
> one thing it could say that was certainly wrong.
>
> The shape recognised here is narrow, and every part of it is checked against
> both runs:
>
> - the block repeats **whole**, the same block in both runs, a different number
>   of times;
> - an **earlier step's response** carried a list whose length is exactly that
>   number, in each run, at the same pointer;
> - every value the block sends that changes from one iteration to the next is a
>   field of the element being acted on, at the **same place in the element**,
>   in every iteration of both runs.
>
> The last rule is what makes this evidence. WebRobot (PLDI 2022, and
> docs/16-what-others-have-solved.md) calls the equivalent test speculate and
> validate: a guessed loop must predict actions it was not built from, or it is
> memorisation with a data structure around it.

## `LoopFound`, [line 28](../../../../../../../backend/src/sro/application/induction/loops.py#L28): Note on the line above

Code: `keep: int`

> How many frames of each run survive: the prefix and one iteration. The
> rest are the same block again and have nothing left to prove.

## `detect`, [line 31](../../../../../../../backend/src/sro/application/induction/loops.py#L31): Docstring

> The loop these two runs are two lengths of, if they are.
>
> None for everything else, which is nearly everything: a pair that is not a
> loop must reach the ordinary refusals unchanged, and a wrong loop is a
> warehouse doing something once per row of a list nobody meant.

## `in_step_space`, [line 99](../../../../../../../backend/src/sro/application/induction/loops.py#L99): Docstring

> The same loop, counting the steps the two runs share.
>
> `detect` reads the frames as they were recorded, and has to: the runs
> differ in length precisely because one iterated more times, so aligning
> them first would destroy the very signal a loop is found by. Everything
> downstream counts aligned steps instead -- what only one operator did is
> not part of the task and `align` drops it.
>
> Two index spaces met here and neither was converted. A pair with one
> unmatched gesture before the block produced a loop whose body named steps
> the version did not have (`a loop covers steps 3-3, and this version has
> 2`), and the same mismatch is why a loop and a skipped field could not be
> induced together at all.
>
> Refused rather than approximated where a frame of the block did not survive
> alignment: the two runs then disagree about what one iteration is, and
> guessing there is what ADR 004 exists to prevent.

## `_shape`, [line 142](../../../../../../../backend/src/sro/application/induction/loops.py#L142): Docstring

> What makes two frames the same step of one task, for this purpose: the
> control, and the call it made with its identifiers taken out.

## `_block_length`, [line 150](../../../../../../../backend/src/sro/application/induction/loops.py#L150): Docstring

> The shortest block both tails are whole repetitions of.
>
> Shortest because it claims the least: a body of one step repeated four times
> is a stronger reading of the same evidence than a body of two repeated
> twice, and it is the one that keeps working when the third demonstration has
> five.

## `_source_of`, [line 168](../../../../../../../backend/src/sro/application/induction/loops.py#L168): Docstring

> The earlier response that said how many there would be.
>
> The same pointer of the same step in both runs, holding a list as long as
> that run's own number of iterations. Anything less is a coincidence: a page
> of results happens to have three rows in the run that did three things.

## `_bindings`, [line 207](../../../../../../../backend/src/sro/application/induction/loops.py#L207): Docstring

> Which values the block sends are fields of the thing it is acting on.
>
> Read off what changes from one iteration to the next, and then required to
> hold for *every* iteration of *both* runs -- including the first, which is
> the one the skill keeps. A rule that explains the iterations it was read
> from and not the others is the memorisation this is arranged against.

## `_varies`, [line 263](../../../../../../../backend/src/sro/application/induction/loops.py#L263): Docstring

> Sites where this position of the block sent something different the
> second time round.

## `_place_in_element`, [line 279](../../../../../../../backend/src/sro/application/induction/loops.py#L279): Docstring

> Where inside one element this value lives -- if the same place explains
> every iteration of both runs.
>
> Read off the first run's first two iterations, then required to hold for all
> of them and for the other run's as well. A place that explains only what it
> was read from explains nothing.

## `_per_iteration`, [line 312](../../../../../../../backend/src/sro/application/induction/loops.py#L312): Docstring

> What this run sent at this site, iteration by iteration.
>
> Read by diffing each iteration against the first: a site that does not
> appear in that diff sent the same thing the first one did.

## `detect`, [line 40](../../../../../../../backend/src/sro/application/induction/loops.py#L40): Comment

Code: `return None`

> Two runs that did the same number of things prove nothing about
> looping. They are a task that does three similar things, and the
> ordinary diff has always read that correctly.

## `detect`, [line 42](../../../../../../../backend/src/sro/application/induction/loops.py#L42): Comment

Code: `return None`

> One gesture that made two calls is split into two steps later, which
> renumbers everything a loop names. Refused rather than guessed at.

## `detect`, [line 44](../../../../../../../backend/src/sro/application/induction/loops.py#L44): Comment

Code: `for prefix in range(1, min(len(shapes_a), len(shapes_b))):`

> Where the block starts is not a guess: the prefix is only right if an
> earlier response holds a list as long as the number of iterations that
> prefix implies -- in *each* run. Tried shortest first, so the loop starts
> as early as the evidence allows.

## `in_step_space`, [line 112](../../../../../../../backend/src/sro/application/induction/loops.py#L112): Comment

Code: `raise InductionFailed(`

> The body survived, but something the runs do not share sits inside
> it. A body with a hole in it is two loops somebody has to be able to
> see separately, which is the rule `Loop` itself states.

## `_block_length`, [line 160](../../../../../../../backend/src/sro/application/induction/loops.py#L160): Comment

Code: `return block`

> The counts differ by construction: `detect` refuses two runs of
> equal length, and both tails start at the same prefix.

## `_bindings`, [line 223](../../../../../../../backend/src/sro/application/induction/loops.py#L223): Comment

Code: `places: dict[str, list[tuple[int, Difference]]] = {}`

> Grouped by where in the element the value comes from, not by where it is
> sent: Blue Yonder's adjust puts the line id in the path and in the body,
> and two parameters that always hold the same value is how a reviewer ends
> up reading a plan that looks like a mis-binding.

## `_bindings`, [line 256](../../../../../../../backend/src/sro/application/induction/loops.py#L256): Comment

Code: `is_the_body=any(isinstance(d.site, TextBodySite) for _, d in sites),`

> A field of the thing being acted on can be a whole non-JSON
> body, where the call this loop repeats sends nothing else.
> Such a value is the body rather than a value inside one, and
> escaping it into a string that is not there would corrupt it.
