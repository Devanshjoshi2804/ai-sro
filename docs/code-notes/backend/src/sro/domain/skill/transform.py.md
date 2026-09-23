# Notes for `backend/src/sro/domain/skill/transform.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/transform.py`](../../../../../../../backend/src/sro/domain/skill/transform.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/transform.py#L1): Docstring

> What was done to a value between the response that produced it and the call
> that sent it.
>
> A derived parameter is a value an earlier step's response handed to a later one.
> Often it is handed over verbatim, and then there is nothing here to record. Just
> as often it is not: the WMS answers `42` and the ERP is sent `LPN-00042`, and a
> system that can only recognise the verbatim case asks an operator for a number
> the previous step already knew.
>
> Small on purpose. Every operation here is one a person can read off two examples
> and check by eye, because a transformation nobody can check is a guess with a
> data structure around it. Anything more expressive belongs behind a
> demonstration, not behind an inference.

## `Transform`, [line 18](../../../../../../../backend/src/sro/domain/skill/transform.py#L18): Docstring

> An ordered list of operations, applied left to right.
>
> Stored as plain strings rather than as a class hierarchy because a skill
> version is a document that has to survive being read back by a later version
> of this code: `("prefix", "LPN-")` still means what it meant.

## `Transform.said_plainly`, [line 49](../../../../../../../backend/src/sro/domain/skill/transform.py#L49): Docstring

> For the reviewer, who has to agree this is what the task does.
