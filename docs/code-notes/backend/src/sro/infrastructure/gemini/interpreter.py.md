# Notes for `backend/src/sro/infrastructure/gemini/interpreter.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/gemini/interpreter.py`](../../../../../../../backend/src/sro/infrastructure/gemini/interpreter.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/gemini/interpreter.py#L1): Docstring

> Reading a demonstration with Gemini.
>
> Structured output, so what comes back is checked against a shape before anything
> uses it. What it is asked for is narrow on purpose: describe what happened and
> name the values that look like inputs. It is never asked what the system *should*
> do, or to invent a step nobody performed.

## `_parse`, [line 191](../../../../../../../backend/src/sro/infrastructure/gemini/interpreter.py#L191): Docstring

> A bad shape is a reading with nothing in it, not an exception.
>
> The demonstration is still perfectly usable without a narrative: the calls
> are the skill, and the description is what makes it findable.

## `GeminiInterpreter._ask`, [line 167](../../../../../../../backend/src/sro/infrastructure/gemini/interpreter.py#L167): Docstring

> A structured answer, or `None` for anything that went wrong.
>
> Both callers of this are proposals about candidates -- a sentence on a
> list and a suggestion beside it. Neither is worth an exception: what a
> candidate *is* was decided before this was asked, and stands whatever
> comes back.

## `GeminiInterpreter.read`, [line 141](../../../../../../../backend/src/sro/infrastructure/gemini/interpreter.py#L141): Comment

Code: `logger.warning("the interpreter did not answer; inducing without a reading")`

> An induction that loses its narrative is still an induction: the
> calls are the skill. Failing the whole thing because a hosted
> model answered 500 would throw away two demonstrations.
