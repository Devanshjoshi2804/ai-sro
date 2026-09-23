# Notes for `backend/src/sro/application/induction/transform.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/transform.py`](../../../../../../../backend/src/sro/application/induction/transform.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/transform.py#L1): Docstring

> Reading, off two examples, what was done to a value on its way between steps.
>
> The diff finds a data dependency by exact equality: a value the response carried
> and the next call sent. Nothing else was ever recognised, so a value that was
> reformatted on the way -- `42` answered by the WMS, `LPN-00042` sent to the ERP
> -- looked like a value nobody could account for, and became a question for an
> operator who has no idea where the number comes from either.
>
> What makes this evidence rather than pattern-matching is where it is used: the
> transformation is read off one run and then has to explain the *other* run's
> pair as well, from the same place in the same response. Two runs agreeing is the
> same standard the rest of the diff holds itself to. See
> docs/16-what-others-have-solved.md, and Leno et al. (arXiv:2001.01007) for the
> general form of the problem -- theirs searches a space of programs with A*,
> which is the right shape once a transformation is worth more than the six this
> can express.

## module, [line 7](../../../../../../../backend/src/sro/application/induction/transform.py#L7): Note on the line above

Code: `SHORTEST_SOURCE = 2`

> A single character carried into a longer string is not evidence of anything.
> `7` appears inside a hundred values by accident, and a rule read off one of them
> would be a confident wrong answer of the kind ADR 004 exists to prevent.

## `discover`, [line 10](../../../../../../../backend/src/sro/application/induction/transform.py#L10): Docstring

> How `source` becomes `target`, if this can say so exactly.
>
> None where it cannot, which is most of the time and is the point: an
> unexplained value stays a value the operator is asked for, and being asked
> is better than being sent something invented.

## `_locate`, [line 40](../../../../../../../backend/src/sro/application/induction/transform.py#L40): Docstring

> Where this value sits inside the target, and what was done to it there.
>
> Tried in order of how much is being claimed: as it is, then recased, then
> zero-padded -- so a value that appears verbatim is never explained by a
> longer story about padding.

## `_placed`, [line 59](../../../../../../../backend/src/sro/application/induction/transform.py#L59): Docstring

> The first occurrence that is not part of a longer number.
>
> `42` occurs inside `LPN-00042`, and reading that as "prefix `LPN-000`"
> reproduces this example and gets the next one wrong: the run where the WMS
> answered `7` would be sent `LPN-0007`. A digit touching a digit is not the
> boundary of the value -- so that occurrence is skipped, and padding is
> found instead, which is what actually happened.

## `discover`, [line 37](../../../../../../../backend/src/sro/application/induction/transform.py#L37): Comment

Code: `return candidate if candidate.apply(source) == target else None`

> Built from the pair, then checked against it. A construction that does not
> reproduce its own example is a bug, and shipping it would put an invented
> value in a warehouse write.
