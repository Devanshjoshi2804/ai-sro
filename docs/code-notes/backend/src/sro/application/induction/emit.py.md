# Notes for `backend/src/sro/application/induction/emit.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/emit.py`](../../../../../../../backend/src/sro/application/induction/emit.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/emit.py#L1): Docstring

> Build a SkillStep from run A's frame. See docs/07-adr/005-dual-recipe.md.

## `_requires_human`, [line 142](../../../../../../../backend/src/sro/application/induction/emit.py#L142): Docstring

> Keyword match, biased towards flagging.
>
> A step wrongly flagged costs an operator ten seconds; one wrongly cleared
> costs an MFA lockout.

## `emit_step`, [line 42](../../../../../../../backend/src/sro/application/induction/emit.py#L42): Comment

Code: `requires_human=_requires_human(frame) or bool(narration and narration.requires_human),`

> Either source may flag a human: the screen shows an MFA field, or the
> operator says they would check with a supervisor here.

## `emit_step`, [line 45](../../../../../../../backend/src/sro/application/induction/emit.py#L45): Comment

Code: `when=when or parameterisation.conditional_on(index),`

> Given for a gesture only one run made, and asked for otherwise: a
> step that types an optional field is conditional on it wherever it
> came from.
