# Notes for `backend/src/sro/domain/prompts/read_request.py`

Comments and docstrings moved out of [`backend/src/sro/domain/prompts/read_request.py`](../../../../../../../backend/src/sro/domain/prompts/read_request.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 11](../../../../../../../backend/src/sro/domain/prompts/read_request.py#L11): Note on the line above

Code: `_TASK = """\`

> The first paragraph of the task -- the prompt's second -- is the product.
>
> A mined job is named after the one demonstration it was read from, values and
> all, so a door told only "answer which job they mean" compares an operator's
> sentence against a title that describes a single past doing and answers null.
> Without that paragraph the door named no job for five real operator sentences;
> with it, five of five.

## module, [line 67](../../../../../../../backend/src/sro/domain/prompts/read_request.py#L67): Comment

Code: `"values": {`

> A list of pairs, not a map: the Gemini Developer API refuses
> `additionalProperties` with a 400 -- "only supported in Gemini
> Enterprise Agent Platform mode" -- and a map of parameter name to
> value is exactly that. Found the first time this door met the real
> API, which it had shipped without ever doing.

## module, [line 77](../../../../../../../backend/src/sro/domain/prompts/read_request.py#L77): Comment

Code: `"sure": {"type": "boolean"},`

> How sure, and what else it nearly was.
>
> The door always named a job. Asked "lets create warehouse equipment
> type" by an operator whose tenant holds exactly that job, an earlier
> version of this system answered "Create a customer type does that"
> with no way for anything downstream to know it had guessed -- and a
> guess that creates one wrong record is a nuisance, while the same
> guess against a list of twenty is twenty wrong records in a
> warehouse.
>
> `sure` is the model's own reading of whether the sentence names ONE
> of these jobs plainly. `also` is what it nearly said instead, which
> is what a person is asked to choose between.

## module, [line 79](../../../../../../../backend/src/sro/domain/prompts/read_request.py#L79): Comment

Code: `"items": {`

> Several things, one job. "Add these three equipment types" is one
> job done three times, and until this existed the door could only
> answer the first: the values of one thing, in `values`, and the
> other two lost between a mail and a browser that had just proved it
> could do them.
>
> A list of lists of pairs, for the same reason `values` is a list of
> pairs one level up: the Developer API refuses `additionalProperties`,
> so a map of parameter name to value cannot be asked for at any depth.
