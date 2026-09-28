# Notes for `backend/src/sro/infrastructure/gemini/intent.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/gemini/intent.py`](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py#L1): Docstring

> Reading parameter values out of a sentence, with Gemini.
>
> Extraction only. The skill is already chosen and its parameters are already
> declared; what comes back is checked against that list, so a value for a
> parameter the skill does not have is dropped rather than sent.

## `GeminiIntentParser.read`, [line 35](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py#L35): Note on the line above

Code: `if answer is None:`

> The model's answer, or ``None`` when it did not give one.
>
> Google answers `500 INTERNAL` often enough that a chat request carrying one
> straight through is a nightly outage: the operator asked how many suppliers
> there are and was told the system is broken, for a call whose whole job is
> to *suggest* a reading that is then checked against real skills.
>
> So a model failure is an absent opinion, not an error. Everything here has
> a deterministic path underneath it, which is exactly why this is safe.
>
> Both questions go through `sro.application.shared.asking.ask`, so a
> failure on 3.8-flash is asked once more on 3.7-flash, and an answer that
> breaks the record's schema is no answer (GC 10) -- a reading missing a
> required field is an empty `Reading`, never one filled with defaults.
> "No answer" is `ask`'s answer with no data, after its fallback. `OverCap`
> and `Unattributed` are refusals, not failures, and reach the caller as they
> do on every other `ask` path (chat maps `OverCap` to 429).

## `GeminiIntentParser.read`, [line 25](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py#L25): Docstring

> What the sentence means. Never what to run.

## `GeminiIntentParser.extract`, [line 51](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py#L51): Comment

Code: `schema: dict[str, Any] = copy.deepcopy(dict(EXTRACT_VALUES.output_schema))`

> `EXTRACT_VALUES` holds the base object; the parameters are this job's, so
> one string property per parameter goes into a copy. A deep copy, because the
> record is shared by every request and its nested dicts are not frozen.
> The copy goes on a `replace` of the record, so `ask` sends and checks this
> job's schema under the record's name, version, model and fallback.

## `GeminiIntentParser.extract`, [line 61](../../../../../../../backend/src/sro/infrastructure/gemini/intent.py#L61): Comment

Code: `"parameters": json.dumps(list(parameters), ensure_ascii=False),`

> The parameter names are fenced like the request. They are the job's field
> labels, read off the page it was demonstrated on, so they are page text, and
> page text is untrusted (invariant 7).
