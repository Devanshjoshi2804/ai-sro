# Notes for `backend/src/sro/domain/prompts/record.py`

Comments and docstrings moved out of [`backend/src/sro/domain/prompts/record.py`](../../../../../../../backend/src/sro/domain/prompts/record.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/prompts/record.py#L1): Docstring

> A prompt is a record: its name, version, model, thinking, role, task, what it
> is given, the schema its answer must match, its rules and the cases seen
> before. Every prompt sent through `Asker` is one of these, in
> `sro.domain.prompts`, and `sro.application.shared.asking.ask` is the one
> way one is sent. A change to a record's text, schema, model or thinking bumps
> its `version` and is measured by `make eval` before it merges.

## module, [line 11](../../../../../../../backend/src/sro/domain/prompts/record.py#L11): Note on the line above

Code: `K_FENCE = "untrusted"`

> The tag untrusted text is wrapped in. Mail, page text, outlines and what an
> operator typed arrive inside a fence and never beside the instructions, so a
> mail that says "ignore every rule" is a quotation the model was told is data,
> not a sentence in its task.
>
> A fence and not an escape: a model reads markup, not escapes. Text JSON-escaped
> into a string still reads as words to the model, and it has no way to tell
> where the operator's sentence stops and the system's begins; a named block it
> does see the edges of.

## `Prompt`, [line 30](../../../../../../../backend/src/sro/domain/prompts/record.py#L30): Docstring

> `role` is the old prompt's text up to its first blank line and `task` is
> the rest, both moved verbatim when the prompts became records; `role` +
> blank line + `task` is byte for byte the text each caller used to send.
> `output_schema` is a `Mapping` so a record cannot be edited in place;
> `ask` hands the asker a `dict` copy.

## `Prompt.evidence`, [line 59](../../../../../../../backend/src/sro/domain/prompts/record.py#L59): Docstring

> The task first, the evidence, then the task again.
>
> Question-first ordering was strongest at long context, and restating the
> constraints after the evidence costs almost nothing. Nothing here marks
> which evidence matters most -- doing that was measured to reduce accuracy.
>
> Measured on the miner (this was the docstring of `umbrella.build_prompt`, now gone) and now
> the shape of every prompt: `instructions` opens with the task, and this
> closes with it, once each.

## `fenced`, [line 77](../../../../../../../backend/src/sro/domain/prompts/record.py#L77): Docstring

> A fence the text inside cannot close. Any closing tag in the text is
> written `<\/untrusted`, so the one closing tag in the block is the one
> this function wrote. "Any" is `_CLOSES`: case and whitespace do not matter,
> because a model reads `</UNTRUSTED>` and `</ untrusted>` as the same close.

## `quoted_in`, [line 82](../../../../../../../backend/src/sro/domain/prompts/record.py#L82): Docstring

> Whether a quote a model cites occurs in what it was given. Whitespace and
> case are folded, because a model re-wraps and re-cases what it quotes; an
> empty quote proves nothing and is never "in" anything.

## `conforms`, [line 87](../../../../../../../backend/src/sro/domain/prompts/record.py#L87): Docstring

> Whether an answer matches its schema. A miss is no answer (Global Constraint
> 10): code validates every model answer, and an answer that breaks its schema
> counts as unsure, never as an answer.
>
> A subset of JSON schema, and deliberately so: Gemini's response-schema subset
> -- `type`, `properties`, `required`, `items`, `enum`, `nullable`.
> Anything else (`description`, `propertyOrdering`) says nothing about
> validity and is ignored, and so is a type this does not know: the ceiling is
> that a schema using a keyword outside that subset is checked only as far as
> the subset reaches. Upgrade path: `jsonschema`, once a record needs more.
> Keys the schema does not name are allowed, as Gemini allows them.

## `Prompt.kept`, [line 67](../../../../../../../backend/src/sro/domain/prompts/record.py#L67): Docstring

> The answer with every item of the record's `unit` that breaks its schema
> dropped, and the rest kept. A record names its unit when its answer is a
> list of independent things: MINE's `workflows`, GATHER's `values`. One
> malformed job then costs that job and not the pass that paid to find the
> others, and one value read without its message costs that value and not
> the gather. A record whose whole answer is one thing (a reading, a mail,
> a verdict) names none, and a miss anywhere in it is no answer.
>
> Only the unit's items are filtered. Whatever else breaks the schema --
> the unit missing, or not a list -- is still no answer.
