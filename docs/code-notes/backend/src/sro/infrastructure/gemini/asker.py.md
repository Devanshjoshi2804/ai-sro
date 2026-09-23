# Notes for `backend/src/sro/infrastructure/gemini/asker.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/gemini/asker.py`](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L1): Docstring

> Gemini, with structured output and a bill.
>
> Every call records its tokens and what they cost. A model call with no cost row
> is a model call nobody can defend at the end of the month.
>
> Search grounding is never enabled: it voids zero data retention (thirty days of
> storage, no opt-out), and this process reads live customer payloads.

## module, [line 14](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L14): Note on the line above

Code: `K_MAX_OUTPUT_TOKENS = 65536`

> What one answer may run to. A mining pass writes every workflow it found,
> each step citing gestures by id; a day's worth is thousands of tokens and the
> default ceiling cut one off.
>
> Thinking is counted inside this on Gemini, not beside it, and that is a trap
> worth knowing: Gemini 3.8 Flash at effort `high` spent 62,913 of the 65,536
> thinking about one day of evidence and had 2,609 left to write its answer in --
> truncated, three runs out of three, $0.38 each for nothing. A budget cannot fix
> it (the API takes a level or a budget, never both, and this model ignores the
> budget); the level is the knob, and a model that thinks too much for its own
> ceiling needs a lower one. Anthropic bills thinking outside its ceiling and is
> unaffected.

## module, [line 17](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L17): Note on the line above

Code: `LESS_THINKING: dict[Effort, Effort] = {"high": "medium", "medium": "low", "low": "minimal"`

> One step down the only knob there is.
>
> `maxOutputTokens` is a hard ceiling on thinking AND answer together -- Google
> says so in as many words -- and 65,536 is the model's own limit, not a setting.
> There is no thinking budget on Gemini 3.x: the API takes a level, and a model
> that thinks too much for its own ceiling needs a lower one.
>
> So a truncated pass is not a failure to report, it is a level to lower. Asked
> again one step down, once: measured on this deployment 2026-09-21, the same
> 158,193-token window that spent all 65,536 tokens thinking at `medium` and
> answered nothing answered at `low` in 10,757 tokens for $0.16, and kept a job.
> Without this the pass costs $0.36 and yields nothing at all.
>
> `minimal` is the floor, and a call already there is one nothing here can help.

## module, [line 40](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L40): Note on the line above

Code: `K_TRIES = 3`

> How many times one call is attempted before it is recorded as failed.
>
> Only for a transient server fault -- see `_worth_retrying`. Measured: three
> mining passes over acme's 555 gestures, and **two of them died on a 504
> DEADLINE_EXCEEDED** from Google's own backend on a 154,200-token prompt. That
> is not this deployment's timeout expiring (a client timeout raises
> `httpx.ReadTimeout`, not a `ServerError` carrying a JSON body); it is the far
> end giving up on a large request. A mining prompt is two orders of magnitude
> bigger than a reading prompt, so the failure lands there and almost never on a
> reading.
>
> Three attempts and not more, because the honest position on a retry is that
> `unpriced` says it: a call that failed may already have been billed, so every
> retry risks paying twice for one answer. Two extra attempts against a 2-in-3
> failure rate is worth that; ten would not be.

## module, [line 42](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L42): Note on the line above

Code: `K_BACKOFF_S = 2.0`

> Waited before a retry, multiplied by the attempt number. A server that just
> gave up on a large request is a server that wants a moment.

## module, [line 44](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L44): Note on the line above

Code: `K_TIMEOUT_MS = 120_000`

> The default ceiling on one call, in milliseconds -- see
> `Settings.gemini_timeout_ms`, which is where a deployment changes it. Stated
> here as well so a caller that builds this adapter directly (a script, a
> bake-off) is bounded too rather than inheriting the SDK's no-timeout.

## `truncated`, [line 20](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L20): Docstring

> Whether the model stopped because it hit the output ceiling. The SDK
> says so on the candidate's `finish_reason`; compared by name so a fake and
> the enum both read. A cut-off answer is not "not json": it is a page the
> model was not allowed to finish, and the row should say which.

## `build_config`, [line 27](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L27): Docstring

> The config every call uses. No tools, ever — see the module docstring.

## `_worth_retrying`, [line 47](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L47): Docstring

> Whether this failure is the far end's and might not happen again.
>
> A 5xx is the server saying it could not, which is the one class of failure
> a second attempt can fix. A 4xx is this deployment being wrong -- a bad
> schema, a revoked key, a quota -- and retrying it spends money to be told
> the same thing. 429 is deliberately NOT retried here: it is the quota
> speaking, and hammering it is how a rate limit becomes a ban.
>
> Read off `code` rather than by catching `ServerError` by name, so an SDK
> that renames its exceptions does not silently turn this off.

## `GeminiAsker.__init__`, [line 53](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L53): Docstring

> `client` is for tests; production passes an api_key and nothing else.
>
> `timeout_ms` is passed on to the SDK because its own default is no
> timeout, and a call with no timeout is not slow -- it is indefinite.
> One hung socket held a reading pass for 19 hours here, having read
> nothing and said nothing.

## `build_config`, [line 33](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L33): Comment

Code: `max_output_tokens=K_MAX_OUTPUT_TOKENS,`

> The most the model may write back. Left to the default, a mining
> pass over a whole day came back cut mid-string at 17,313 characters
> and was filed as "not json": $1.16 for nothing, and nothing said
> why. The models this rig names all write up to this.

## `build_config`, [line 34](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L34): Comment

Code: `thinking_config=None`

> Self-consistency was measured at a 0.4% gain for 20x the cost, so
> K_SAMPLES is 1 and this is the knob instead. None leaves the model's
> own default alone, which is what the per-gesture reading wants.
> ThinkingLevel(...) because the SDK types the field as its own enum,
> and a plain str fails mypy. It takes "high" case-insensitively.

## `GeminiAsker.ask`, [line 82](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L82): Comment

Code: `logger.info("the answer hit the output ceiling at %s; asking again at %s", effort, lower)`

> The first call was billed whether or not it said anything, so the
> second's numbers are ADDED to it rather than replacing them: a row
> that reported only the answer that arrived would understate a pass
> that had to ask twice, which is the one figure this is about.

## `GeminiAsker._parts`, [line 102](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L102): Comment

Code: `parts: list[Any] = [part for part in (instructions, evidence) if part]`

> A falsy instruction would otherwise ship as a leading Part(text=''):
> benign in the SDK, and rejected by some endpoints. umbrella.py passes
> instructions="" on every call.

## `GeminiAsker._parts`, [line 105](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L105): Comment

Code: `for more in images:`

> Further pictures, in the order given: a rescue shows the page as it
> is now and then the page the failed attempt left behind.

## `GeminiAsker._asked_once`, [line 114](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L114): Comment

Code: `with doing("model.ask") as span:`

> The most expensive thing this system does, and the one whose time
> nothing could account for: a request that took ninety seconds said so
> and said nothing about which of its model calls that was.

## `GeminiAsker._asked_once`, [line 125](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L125): Comment

Code: `except Exception as raised:`

> Broad on purpose: a rig keeps going, and the row records why.

## `GeminiAsker._asked_once`, [line 137](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L137): Comment

Code: `return Answer(unpriced=True, error=f"{type(problem).__name__}: {problem}")`

> The call may or may not have been billed before it failed, and we
> cannot tell -- so the cost figure (0.0 here) is not to be trusted.

## `GeminiAsker._asked_once`, [line 142](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L142): Comment

Code: `thought_tokens = getattr(usage, "thoughts_token_count", None) or 0`

> Thinking tokens are billed at the OUTPUT rate, with no discount tier,
> and candidates_token_count does not include them -- the SDK carries
> them separately. Reading only candidates_token_count understated every
> figure this rig has ever produced, and understated them by more the
> harder the prompt was. K_EFFORT = "high" exists to spend these, so a
> short visible answer can carry thousands of billed tokens the bill
> showed and we did not.

## `GeminiAsker._asked_once`, [line 145](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L145): Comment

Code: `out_tokens = (raw_out or 0) + thought_tokens`

> Kept apart in the record and added together for the bill: one number
> says what the model wrote, the other says what it cost.

## `GeminiAsker._asked_once`, [line 150](../../../../../../../backend/src/sro/infrastructure/gemini/asker.py#L150): Comment

Code: `return Answer(`

> The SDK returns None rather than raising when a call is blocked or
> comes back with no candidates. Parsing that as "{}" would file a
> refusal as a confident empty answer.
