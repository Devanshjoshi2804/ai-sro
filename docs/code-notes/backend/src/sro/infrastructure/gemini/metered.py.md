# Notes for `backend/src/sro/infrastructure/gemini/metered.py`

Comments and docstrings for [`backend/src/sro/infrastructure/gemini/metered.py`](../../../../../../../backend/src/sro/infrastructure/gemini/metered.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/gemini/metered.py#L1): Docstring

> Every model call is billed in one place: the client every Gemini adapter is
> handed.
>
> Before this, only `GeminiAsker` priced its answers, and whether a price reached
> the day's bill depended on the caller writing it down. The mining pass, the
> gesture reading, the chat door and a run did; the mail look, the gather, the
> mail job's drafting, the "is it an answer" reading and the lookup plan did
> not, and the intent parser, the vision driver, the transcriber and the
> embedder never priced anything at all. The cap was judged on part of the bill.
>
> The container now hands every adapter a `Metered` client in place of the SDK's
> own. The adapter cannot reach the model except through it, so a new caller --
> or a new adapter built by `container.py` -- is billed without remembering to
> be. `model_spend` is the one table the day's spend is summed from.
>
> `GeminiInterpreter` is deliberately not metered: its callers (induction and
> the old candidate naming) are being deleted.

## `Meter.check`, [line 29](../../../../../../../backend/src/sro/infrastructure/gemini/metered.py#L29): Docstring

> The cap, asked before every call, for the tenant the work is attributed to
> (`sro.whose`). Over it, `OverCap` is raised in place of the call, which every
> adapter already treats as the model being unreachable: the asker answers with
> an error, the intent parser falls back to what can be decided without it,
> and the others raise to their callers as a network failure would.
>
> No tenant named raises `Unattributed`: nobody's cap can be asked and nobody's
> bill can show the call, so it is a wiring bug surfaced at the call rather
> than an unreadable row. Entry points name the tenant: HTTP in `deps.py`,
> Temporal activities in `activities._context`, runs in `run_workflow`, the
> miner's sweep and `read_cron` per tenant, triggers in `FireTrigger`, and the
> knowledge CLIs. A negative cap -- the shipped default -- is then answered
> without a query.

## `Meter.record`, [line 40](../../../../../../../backend/src/sro/infrastructure/gemini/metered.py#L40): Docstring

> One `model_spend` row per answered call, in its own unit of work: the money
> was spent whether or not the caller's transaction commits.
>
> Priced as `GeminiAsker` prices its own answers -- thinking tokens are billed
> as output -- and `unpriced` only when there was no prompt count or the price
> table does not know the model, which the cap reads as blind. A missing output
> or thinking count is zero: proto3 drops a zero `candidatesTokenCount`, and
> reading that as unknown made one empty answer block a capped tenant for the
> day, the asker's own lower-effort retry included.
>
> A write that fails is logged and swallowed: the caller already has an answer
> that was paid for, and losing it as well would be the worse outcome.

## `Metered`, [line 75](../../../../../../../backend/src/sro/infrastructure/gemini/metered.py#L75): Docstring

> Stands where `genai.Client` stood, exposing the two methods the adapters use
> under the same path: `client.aio.models.generate_content` and
> `client.aio.models.embed_content`. Failed calls are not billed -- they raise
> before `record` -- and a retry that answers is billed once for that answer.

## `Metered.generate_content`, [line 86](../../../../../../../backend/src/sro/infrastructure/gemini/metered.py#L86): Comment

Code: `tools = getattr(usage, "tool_use_prompt_token_count", None) or 0`

> The computer-use driver's tool prompt is input the model is billed for, and
> it is reported beside the prompt, not inside it.

## `Metered.embed_content`, [line 99](../../../../../../../backend/src/sro/infrastructure/gemini/metered.py#L99): Comment (debt)

Code: `sent = sum(len(str(one)) for one in contents)`

> ponytail: the Gemini Developer API returns no token count for embeddings
> (only Vertex does), so the tokens are estimated at `K_CHARS_PER_TOKEN`
> characters each. Recording the call as
> unpriced instead would make every embedding blind and stop a capped tenant
> after its first retrieval. Replace with `count_tokens` if the estimate is
> ever the number somebody disputes.
