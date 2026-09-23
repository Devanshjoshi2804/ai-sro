# Notes for `backend/src/sro/infrastructure/gemini/null_intent.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/gemini/null_intent.py`](../../../../../../../backend/src/sro/infrastructure/gemini/null_intent.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/gemini/null_intent.py#L1): Docstring

> No intent parser. Chat still resolves a skill and asks for its values.

## `NoIntentParser.read`, [line 16](../../../../../../../backend/src/sro/infrastructure/gemini/null_intent.py#L16): Docstring

> Nothing read. The caller falls back to matching the words themselves,
> which is worse and is meant to be: a deployment with no model reads a
> sentence literally rather than pretending to understand it.
