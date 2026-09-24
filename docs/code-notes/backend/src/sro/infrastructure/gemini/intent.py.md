# Notes for `backend/src/sro/infrastructure/gemini/intent.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/gemini/intent.py`](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py#L1): Docstring

> Reading parameter values out of a sentence, with Gemini.
>
> Extraction only. The skill is already chosen and its parameters are already
> declared; what comes back is checked against that list, so a value for a
> parameter the skill does not have is dropped rather than sent.

## `_answered`, [line 148](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py#L148): Docstring

> The model's answer, or ``None`` when it did not give one.
>
> Google answers `500 INTERNAL` often enough that a chat request carrying one
> straight through is a nightly outage: the operator asked how many suppliers
> there are and was told the system is broken, for a call whose whole job is
> to *suggest* a reading that is then checked against real skills.
>
> So a model failure is an absent opinion, not an error. Everything here has
> a deterministic path underneath it, which is exactly why this is safe.

## `GeminiIntentParser.read`, [line 63](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py#L63): Docstring

> What the sentence means. Never what to run.
