# Notes for `backend/src/sro/domain/prompts/mine.py`

Comments and docstrings moved out of [`backend/src/sro/domain/prompts/mine.py`](../../../../../../../backend/src/sro/domain/prompts/mine.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 55](../../../../../../../backend/src/sro/domain/prompts/mine.py#L55): Note on the line above

Code: `version=4,`

> Version 4 (P5, 2026-09-28) is version 3 with the two rules every record now
> shares, appended by `Prompt`. P5 also rewrote MINE to push recall (a small
> doing, one started in mail, one done once is a job; report when unsure):
> the greyorange mining eval kept accuracy at 28.6% but doubled sure-but-wrong
> (28.6% -> 57.1%) and raised cost, so that rewrite was dropped.
>
> Version 3 (T1, 2026-09-27) explains two new keys in `day`: each gesture's
> `tab`, and `opened` (the tabs it opened, each with its opener), so that work
> carried on in a popup reads as one job. `_TASK` is unchanged; the input the
> model is given changed, and that is a prompt change all the same. The mining
> eval (`make eval suite=mining`) measures v3 against the v2 baseline.
>
> Version 2 (M1, 2026-09-26) deleted one sentence from `_TASK`: "Say which
> values look like the same thing appearing in two systems." No field in
> `output_schema` carried the answer and no code read it. The code already
> finds those values itself (`values.shared_values`) and shows them to the
> model as the `crossings` block, so the sentence asked the model to do,
> with nowhere to put it, what had been done for it. The mining eval
> (`make eval suite=mining`) measures v2 against the v1 baseline; the report
> goes in the PR.

## module, [line 56](../../../../../../../backend/src/sro/domain/prompts/mine.py#L56): Note on the line above

Code: `model="gemini-3.8-flash",`

> The model one mining pass asks. The rig's `mine_model`
> (`new_agent_arch/src/rig/config.py:20`) was `gemini-3.1-pro-preview`, and
> it is deliberately no longer the rig's. It was the setting
> `gemini_mine_model` until the prompts became records.
>
> **Measured, 2026-09-21, against pro on identical copies of the deployed
> store** -- 904 gestures, the same 22 known workflows, the same
> `thinking="medium"`, the same window budget:
>
>     pro    8 passes, 2 of 5 finished inside the shipped timeout,
>            107s / 135s / 217s, mean $0.493, 3-10 proposals
>     flash  5 passes, 5 of 5 finished, ~115s, mean $0.235, 9-12 proposals
>
> and, on the number that decides it, **0 new jobs each**. Every proposal
> from both resolved as a job already stored or the same evidence read
> twice, because the store had converged.
>
> So this is not "flash mines better"; nothing here shows that, and a
> converged store cannot show it. It is the rule `PLAN_STEP_ESCALATED` in
> `plan_step.py` already states -- the expensive model earns its price where depth per call
> is the product -- applied to the call that is its opposite. A mining pass
> is 162,000 input tokens, one shallow judgement, and then the nine rules in
> `validate` that do the actual discrimination. The miner's job is recall;
> recall is the cheaper thing to buy, and `validate` is what refuses. Pro
> earns its price at the rescue rung, once per failure, and stays there.
>
> **And then it was re-run, on exactly that.** An operator demonstrated
> `Create a Transport Equipment Type` three times -- a screen this store had
> never held a job for -- and both models were given the same 159,929-token
> prompt over identical copies with that job rolled back:
>
>     flash  learned it,  10 proposed (1 new, 3 same_job, 6 same_occurrence),
>            nothing wrongly refused,   91s,  $0.2396
>     pro    learned it,   8 proposed (1 new, 2 same_job, 4 same_occurrence),
>            nothing wrongly refused,  338s,  $0.5032
>
> The same answer, 2.1x the price and 3.7x the wall clock. Flash gets there
> by thinking four times as hard -- 21,278 thought tokens against 4,821 --
> and still costs less, because thinking is billed at its own output rate.
> Note pro's 338 seconds: under the 120s that shipped before
> `gemini_mine_timeout_ms`, that pass would have died.
>
> So the choice is measured on novel evidence now and not only on a
> converged store. It is still n=1 on a job of this shape, on this
> application: a subtler one -- more steps, more interleaving, two systems --
> is the moment to run it again rather than assume, which costs $0.75 and
> ten minutes and has these numbers to beat.
>
> Both models at `thinking="high"` spend their whole output budget thinking
> and are truncated with nothing kept. The run and all of its numbers are in
> the `thinking` note below -- cited and not copied, because a
> measurement kept in two places is one that drifts.

## module, [line 58](../../../../../../../backend/src/sro/domain/prompts/mine.py#L58): Note on the line above

Code: `thinking="medium",`

> How hard the model is told to think before it answers.
>
> `"high"` is what the rig shipped, and it is not the harmless default it looks
> like. On Gemini, thinking is billed INSIDE `max_output_tokens`: over one day of
> evidence at `high`, Gemini 3.8 Flash spent 62,913 of 65,536 tokens thinking and
> was truncated with 2,609 left to answer in -- three runs out of three, $0.38
> each, nothing kept. At `medium` the same model mined the same day successfully
> and kept 7 of 17 proposed jobs.
>
> `"medium"`, then, and measured on this backend rather than inherited: the first
> real pass over a real store -- 507 gestures from a day of Blue Yonder capture,
> `gemini-3.1-pro-preview` -- did the same thing at `high`. 204,747 in, 65,522
> out, truncated after 2,610 tokens of answer, $2.00 for nothing kept. The same
> evidence at `medium` answered in 6,041 output tokens with 3,362 of thinking,
> cost $0.93, and kept 2 of 3 proposed jobs, which then replayed 2 of 2 as
> themselves. Twice the result at half the price, and the difference is this
> word.
>
> So this constant is a budget decision as much as a quality one, and it belongs
> to whoever configures a model: a model with a small output ceiling wants
> `"medium"`. Both numbers are written down here because the choice cannot be
> made without them -- and because the first was recorded for one model and not
> applied to the one actually configured, which is how the $2.00 was spent.

## module, [line 72](../../../../../../../backend/src/sro/domain/prompts/mine.py#L72): Comment

Code: `"properties": {`

> cites before says: identifying the evidence before
> composing the answer measurably beats the reverse.

## module, [line 95](../../../../../../../backend/src/sro/domain/prompts/mine.py#L95): Comment

Code: `"parameters": {`

> The shape is declared, which it was not. `object` with
> no properties told the model nothing, while
> `chat.understand` and `skill.shape` both read
> `seen_values` off whatever came back -- so a
> model-supplied parameter arrived in whatever shape the
> model guessed and was dropped by `workflow_from`'s name
> check or carried no values anybody reads. Measured across
> three clean mines of a real day: `parameters` came back
> empty every time, on jobs whose evidence plainly showed
> four different customer types being typed.

## module, [line 117](../../../../../../../backend/src/sro/domain/prompts/mine.py#L117): Comment

Code: `"unplaced": {"type": "array", "items": {"type": "string"}},`

> Beside `workflows`, not inside one. It is a fact about the WINDOW --
> what was left over when every job in it had been described -- and it
> was asked for per workflow, so the model attached the window's
> leftovers to whichever job it happened to emit. Four readers then
> took it for a property of that job and refused to serve, schedule or
> fire it: on the first real cross-tab evidence this system ever mined,
> a correct six-step job carried thirty-six unplaced ids, a third of
> which were gestures supporting its own steps, and was never offered.
