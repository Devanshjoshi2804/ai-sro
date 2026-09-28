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

## `Prompt`, [line 36](../../../../../../../backend/src/sro/domain/prompts/record.py#L36): Docstring

> `role` is the old prompt's text up to its first blank line and `task` is
> the rest, both moved verbatim when the prompts became records; `role` +
> blank line + `task` is byte for byte the text each caller used to send.
> `output_schema` is a `Mapping` so a record cannot be edited in place;
> `ask` hands the asker a `dict` copy.

## `Prompt.evidence`, [line 66](../../../../../../../backend/src/sro/domain/prompts/record.py#L66): Docstring

> The task first, the evidence, then the task again.
>
> Question-first ordering was strongest at long context, and restating the
> constraints after the evidence costs almost nothing. Nothing here marks
> which evidence matters most -- doing that was measured to reduce accuracy.
>
> Measured on the miner (this was the docstring of `umbrella.build_prompt`, now gone) and now
> the shape of every prompt: `instructions` opens with the task, and this
> closes with it, once each.

## `fenced`, [line 96](../../../../../../../backend/src/sro/domain/prompts/record.py#L96): Docstring

> A fence the text inside cannot close. Any closing tag in the text is
> written `<\/untrusted`, so the one closing tag in the block is the one
> this function wrote. "Any" is `_CLOSES`: case and whitespace do not matter,
> because a model reads `</UNTRUSTED>` and `</ untrusted>` as the same close.

## `quoted_in`, [line 101](../../../../../../../backend/src/sro/domain/prompts/record.py#L101): Docstring

> Whether a quote a model cites occurs in what it was given. Whitespace and
> case are folded, because a model re-wraps and re-cases what it quotes; an
> empty quote proves nothing and is never "in" anything.

## `conforms`, [line 106](../../../../../../../backend/src/sro/domain/prompts/record.py#L106): Docstring

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

## `Prompt.kept`, [line 74](../../../../../../../backend/src/sro/domain/prompts/record.py#L74): Docstring

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
>
> The same rule one level down (P2 round 1, invariant 14): a top-level field
> the schema lets be null is one item of the answer, so when it is present and
> broken, or required and missing, it becomes null and the rest stands. A
> plan whose `action` is one the schema does not offer keeps its kind and
> falls back to the operator's recorded gesture, as the planner always did
> for a null action; a verdict with no `why` keeps its verdict. A field that
> may not be null -- a plan's `kind`, a verdict's `held` -- still makes the
> whole answer unsure, because the answer means nothing without it. An absent
> optional field is left absent, not filled in.

## `Prompt`, [line 48](../../../../../../../backend/src/sro/domain/prompts/record.py#L48): Note on the line above

Code: `fallback_model: str | None = None`

> The model `sro.application.shared.asking.ask` asks once more when this
> record's model fails: the call raised after the asker's own retries, came
> back with no usable JSON, hit MAX_TOKENS with no data, or every item of the
> record's `unit` was dropped. A partly valid answer is an answer and is not
> asked again.
>
> Decided 2026-09-28, after two QA mail runs on 3.8-flash spent 1402 of 1414
> output tokens thinking and wrote an empty draft: every 3.8-flash record
> that is asked through `ask` falls back to `gemini-3.7-flash`. Pro records
> have none -- 3.7-flash is no stand-in for pro, and a pro record is itself
> the escalation. `SIGHT` is the computer-use record and has none: it
> escalates to pro through `SIGHT_ESCALATED` instead. `READ_SENTENCE`,
> `EXTRACT_VALUES` and `TRANSCRIBE` are asked through `ask` by their adapters,
> so they fall back like the rest.
>
> Ruled (S3 review, controller ruling R1): not a version bump. The fallback is
> a runtime retry, not a model change under Global Constraint 9 -- the record
> is still measured on `model`, and its text and schema are unchanged. The
> cost is that an answer under an unchanged version may come from 3.7-flash;
> the eval report's `Scored.fell_back` and `Report.fallbacks` count those, and
> its markdown shows the count, so a run that leaned on 3.7-flash is visible
> without changing the gate.

## `conforms`, [line 130](../../../../../../../backend/src/sro/domain/prompts/record.py#L130): Note on the line above

Code: `pattern = schema.get("pattern")`

> A string the schema's `pattern` does not find in does not conform. The
> model is told the same pattern (Gemini honours `pattern`); this is the
> check that it kept to it. `re.search`, so a pattern is found anywhere in
> the string, as JSON Schema means it.

## module, [line 21](../../../../../../../backend/src/sro/domain/prompts/record.py#L21): Note

Code: `SECRETS_RULE = (`

> The two rules every product prompt shares -- what it is given is data, and a
> secret is never written into an answer -- are said once, here, and appended by
> `Prompt.instructions` after each record's own rules. P5 first wrote them into
> every record in its own words: some twenty near-copies of one sentence, each
> paid for on every call and each one more place to drift. A record's `rules`
> hold only what was decided for that record (MINE's small, once, mail and
> chores; PLAN_STEP's secret fields filled by the run; TRANSCRIBE's `[secret]`).
> `UNTRUSTED_RULE` names images and audio as well, since a screenshot or a
> narration is not fenced text and the per-record copies existed to cover them.
