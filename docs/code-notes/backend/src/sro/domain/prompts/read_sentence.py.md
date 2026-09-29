# Notes for `backend/src/sro/domain/prompts/read_sentence.py`

Notes on [`backend/src/sro/domain/prompts/read_sentence.py`](../../../../../../../backend/src/sro/domain/prompts/read_sentence.py). Each note names the code it explains (function or class, then the line in the current file).

## module, [line 25](../../../../../../../backend/src/sro/domain/prompts/read_sentence.py#L25): Note on the line above

Code: `READ_SENTENCE = Prompt(`

> What one chat sentence means, never what to run. It was `_READING` and an
> inline schema in `sro.infrastructure.gemini.intent`, text verbatim.
>
> On `3.8-flash`, which was `gemini_intent_model`: 
> Chat: reading one sentence, extracting values. An operator is waiting, so
> this is the fast one -- measured at ~2.3s against ~4.8s for the pro model,
> for a job where the answer is checked against the skills that exist anyway.

## module, [line 78](../../../../../../../backend/src/sro/domain/prompts/read_sentence.py#L78): Note on the line above

Code: `EXTRACT_VALUES = Prompt(`

> Values for named parameters, out of a request. It was `_INSTRUCTIONS` in
> `sro.infrastructure.gemini.intent`, text verbatim.
>
> The schema here is the base object: the parameters are the job's, so
> `GeminiIntentParser.extract` adds one string property per parameter to a copy
> before it asks. The record never carries one job's names.
