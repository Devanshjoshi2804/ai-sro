# Notes for `backend/src/sro/domain/shared/prices.py`

Comments and docstrings moved out of [`backend/src/sro/domain/shared/prices.py`](../../../../../../../backend/src/sro/domain/shared/prices.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/shared/prices.py#L1): Docstring

> What a model call costs, and what it answered.
>
> The prices are dollars per million tokens; a model missing from the table is
> unpriced, never free.

## `DaySpend`, [line 43](../../../../../../../backend/src/sro/domain/shared/prices.py#L43): Docstring

> What one tenant has been billed for since midnight UTC.
>
> ``blind`` is read beside the sum rather than derived from it, because the
> two say different things and only one of them can be trusted: a model name
> the price table never knew about records $0.0000 with ``unpriced`` set, so
> a day summed on ``cost_usd`` alone reads as free while it spends. A day
> whose cost cannot be established is not a cheap day, and the rule that
> judges this pair says so.

## `Answer`, [line 68](../../../../../../../backend/src/sro/domain/shared/prices.py#L68): Note on the line above

Code: `truncated: bool = False`

> Whether the model was cut off by the output ceiling rather than
> answering.
>
> A fact about the call and not a kind of error, because the caller acts on
> it: thinking is billed inside `maxOutputTokens` on Gemini and the ceiling
> is the model's own, so the only remedy is to think less. `GeminiAsker`
> reads this to ask again one level down. Told apart from `error` rather
> than parsed back out of it, for the reason every sentence in this system
> is: a name read out of prose breaks the first time the prose is reworded.

## module, [line 5](../../../../../../../backend/src/sro/domain/shared/prices.py#L5): Comment

Code: `PRICES: dict[str, tuple[float, float]] = {`

> Dollars per million tokens, (input, output).

## module, [line 6](../../../../../../../backend/src/sro/domain/shared/prices.py#L6): Inline

Code: `"gemini-3.8-flash": (0.75, 3.75),`

> introductory, to 2026-12-31

## module, [line 7](../../../../../../../backend/src/sro/domain/shared/prices.py#L7): Inline

Code: `"gemini-3.7-flash": (0.75, 3.75),`

> introductory, to 2026-12-31; from 2027-01-01 (1.50, 7.50), as 3.8-flash.
> Read off https://ai.google.dev/gemini-api/docs/pricing on 2026-09-28 (paid
> tier, standard). Added with the flash records' fallback: QA billed a
> 3.7-flash call at $0.00 while the row was missing, and an unpriced row
> makes the day blind, which trips the cap for the rest of the day.

## module, [line 10](../../../../../../../backend/src/sro/domain/shared/prices.py#L10): Inline

Code: `"gemini-3.1-pro": (2.00, 12.00),`

> doubles to (4, 18) above 200K

## module, [line 11](../../../../../../../backend/src/sro/domain/shared/prices.py#L11): Comment

Code: `"gemini-3.1-pro-preview": (2.00, 12.00),`

> A preview is priced like the model it previews. Without these rows a real
> pass on a preview name records cost_usd 0.0 with unpriced=True -- which is
> honest, and useless: the measurement run that proved this architecture
> works billed $1.12 and every row said free. A name missing from this table
> is the one failure mode `unpriced` cannot fix, because nothing downstream
> can price a call the table never knew about.

## module, [line 14](../../../../../../../backend/src/sro/domain/shared/prices.py#L14): Comment

Code: `"gemini-embedding-001": (0.15, 0.00),`

> An embedding model bills input only, and this table's shape is (in, out).
> Zero for output is the truth here rather than a missing row: a name
> absent from this table records the whole call as unpriced, and the
> embedder runs on every reading of the knowledge store.

## module, [line 15](../../../../../../../backend/src/sro/domain/shared/prices.py#L15): Comment

Code: `"gemini-embedding-2": (0.20, 0.00),`

> Gemini Embedding 2, $0.20/M in. Dearer than the model it replaces by a
> third, and worth it for what the knowledge store is for: this is the one
> place a similarity is allowed to decide anything, and it decides which
> prose a model is shown. Text only at this rate -- the multimodal rates are
> image $0.45/M, audio $6.50/M, video $12.00/M, and nothing here sends any
> of those yet.

## module, [line 20](../../../../../../../backend/src/sro/domain/shared/prices.py#L20): Comment

Code: `LONG_PROMPT_PRICES: dict[str, tuple[float, float]] = {`

> Above a 200K-token prompt, Gemini 3.1 Pro's rates double.

## module, [line 39](../../../../../../../backend/src/sro/domain/shared/prices.py#L39): Comment

Code: `Effort = Literal["minimal", "low", "medium", "high"]`

> The levels the SDK accepts. Narrowed to a Literal rather than left as str
> because google-genai does not reject an unknown one: ThinkingLevel("nonsense")
> returns a pseudo-member carrying the typo straight to the API on 2.22.0. A
> constant that silently means "model default" is the exact failure wiring
> a record's `thinking` was meant to close, one layer down, so mypy catches it instead.

## `Answer`, [line 66](../../../../../../../backend/src/sro/domain/shared/prices.py#L66): Comment

Code: `thought_tokens: int = 0`

> Part of out_tokens for pricing, kept separately so a reader can see how
> much of the bill was reasoning nobody ever read.

## `Answer`, [line 68](../../../../../../../backend/src/sro/domain/shared/prices.py#L68): Comment

Code: `truncated: bool = False`

> True when cost_usd cannot be trusted: the model is missing from PRICES,
> or the SDK did not give back real usage counts. A $0.00 row and an
> honestly-unpriced row look the same in cost_usd alone -- this is what
> tells them apart.

## `Answer`, [line 72](../../../../../../../backend/src/sro/domain/shared/prices.py#L72): Comment

Code: `dropped: int = 0`

> How many items of the prompt record's `unit` `ask` dropped for breaking
> the schema, so an eval can report a drop rate. A count and never the items:
> they are a model's reading of somebody's mail and pages.

## `Answer`, [line 73](../../../../../../../backend/src/sro/domain/shared/prices.py#L73): Note on the line above

Code: `fell_back: bool = False`

> Whether the record's fallback model was asked for this answer (see
> `sro.application.shared.asking.ask`), whichever answer came back. The eval
> harness counts these per suite.

## `Answer`, [line 74](../../../../../../../backend/src/sro/domain/shared/prices.py#L74): Note on the line above

Code: `malformed: bool = False`

> Told apart from a call that never answered: set only when `ask`'s schema
> check throws away a response that broke the record's schema (GC 10), never
> when the model call itself raised, returned no text, or gave back text
> that was not JSON. `data is None` alone cannot tell a caller which one
> happened, and some callers must -- a transcription that fails to call the
> model on both attempts must raise, where one that answered with the wrong
> shape on both attempts stays silence. Combined with `first.malformed or
> second.malformed` across a fallback, so a hard failure on one model and a
> malformed answer on the other still reads as "something answered."
