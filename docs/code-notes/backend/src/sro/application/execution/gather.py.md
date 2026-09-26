# Notes for `backend/src/sro/application/execution/gather.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/gather.py`](../../../../../../../backend/src/sro/application/execution/gather.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/gather.py#L1): Docstring

> Go and find the values a job needs, in the mailbox the operator reads.
>
> The gap the live deployment named. A run of `Create a Customer Type` needs a
> code and a description; the only source was a person typing them into the
> press, so step 1 -- "Open an email requesting a new customer type" -- refused
> with *"The open email is for customer type GPDP rather than the requested
> ZQ41"*. The run had values and the mailbox had a different request, and nothing
> could go and look.
>
> **Propose, execute through a real port, observe, feed that back.** The shape
> every other loop here uses, and the one every account of agentic loops agrees
> on: gather, act, verify, repeat. What is fed back is a NOTE and never the mail
> -- see `gathering.K_NOTE`. The failure modes of a loop like this are context
> poisoning, distraction and confusion, and raw accumulation is how you get all
> three.
>
> **It refuses rather than guessing.** A parameter nothing could be found for
> comes back in `missing`, and the caller asks a person. This is the same rule
> `write_plan_for` keeps one layer down, for the same reason: a model's reading
> of somebody's mail is not something to put into a warehouse write unasked.
>
> **Every value says which message it came from.** A value read out of a mailbox
> is only as good as the message it was read from, and both the person approving
> the write and an audit a month later need to be able to go and look.
>
> The mailbox is reached through `ToolCaller`, per operator: each reads their own
> mail, and a gather for one person must never see another's. That boundary is
> the port's, not this module's -- it takes the tenant and the principal and
> passes them down.

## module, [line 26](../../../../../../../backend/src/sro/application/execution/gather.py#L26): Note on the line above

Code: `SERVER = "gmail"`

> The connector this looks in. One, named, rather than every connector a
> deployment has: a gather that tried them all would be reading systems nobody
> asked it to read.

## `GatherContext`, [line 29](../../../../../../../backend/src/sro/application/execution/gather.py#L29): Docstring

> Find a job's values in the mailbox, or say which ones are missing.

## `_values_in`, [line 174](../../../../../../../backend/src/sro/application/execution/gather.py#L174): Docstring

> The model's reported values, as far as they are the right shape.
>
> Anything malformed is dropped rather than raising: one bad row in a list of
> two must not lose the good one, and a value with no message behind it is
> dropped by `keep` a moment later anyway.

## `_ran_out`, [line 194](../../../../../../../backend/src/sro/application/execution/gather.py#L194): Docstring

> What happened when the clock beat the mailbox.
>
> Said as what it is rather than as a failure: the run's next move for a
> value nobody found is to ask a person, and that is the same move it makes
> for a mailbox that genuinely does not hold one.

## `_sentence`, [line 199](../../../../../../../backend/src/sro/application/execution/gather.py#L199): Docstring

> What happened, for a person reading the run rather than the code.

## `_also`, [line 207](../../../../../../../backend/src/sro/application/execution/gather.py#L207): Docstring

> The bill so far. Kept because a loop that can ask six times is a loop
> somebody will want the cost of.

## `GatherContext.tools`, [line 35](../../../../../../../backend/src/sro/application/execution/gather.py#L35): Docstring

> The connectors this gather reads through. A mail job sends through
> the same one rather than being handed a second copy of it.

## `GatherContext.execute`, [line 38](../../../../../../../backend/src/sro/application/execution/gather.py#L38): Docstring

> Look, up to `rounds` times, and come back with what was found.
>
> `seen` is what each parameter has been observed taking across the
> demonstrations -- the same `seen_values` the write plan binds by. It is
> shown to the model as the SHAPE of an answer and never as a value to
> reuse: a gather that copied a demonstrated value would create the
> demonstration's record again, which is the defect the whole replay path
> exists to have fixed.

## `GatherContext._look`, [line 138](../../../../../../../backend/src/sro/application/execution/gather.py#L138): Docstring

> One call to the mailbox, as this operator. What was asked, and what
> came back -- both as text, because history is a note and not a payload.
>
> A connector that refuses is not an exception here: it is an observation
> the next round is told about, exactly as an empty search would be. The
> loop then has a chance to try a different query rather than the whole
> gather failing on one bad call.

## `GatherContext._search`, [line 157](../../../../../../../backend/src/sro/application/execution/gather.py#L157): Docstring

> One search, by whatever words were chosen for it.

## `GatherContext._ask_the_mailbox`, [line 162](../../../../../../../backend/src/sro/application/execution/gather.py#L162): Docstring

> One call, as this operator. What was asked, and what came back.
>
> A connector that refuses is an observation the next round is told
> about, not an exception: the loop then has a chance to try a different
> query rather than the whole gather failing on one bad call.

## `GatherContext.execute`, [line 50](../../../../../../../backend/src/sro/application/execution/gather.py#L50): Comment

Code: `unasked: set[str] = set()`

> Names the mail offered that this job declares no parameter for. A
> request asking for a field the job cannot take is a request half
> done, and silence about the other half is the fault this exists to
> stop being invisible.

## `GatherContext.execute`, [line 54](../../../../../../../backend/src/sro/application/execution/gather.py#L54): Comment

Code: `until = time.monotonic() + patience`

> A clock as well as a counter. See `K_PATIENCE_S`: rounds bound how
> many times this looks, and on the day the model answers a round with
> a 5xx the retry that follows is measured in minutes.

## `GatherContext.execute`, [line 56](../../../../../../../backend/src/sro/application/execution/gather.py#L56): Comment

Code: `opening = because.strip() or job.strip()`

> The first look is not the model's to choose.
>
> Asked to find values with nothing to start from, it answered `done`
> with no values on round one and never touched the mailbox -- a
> refusal to look wearing the face of a conclusion. Measured on the
> deployment 2026-09-16: a run with no values gathered nothing and the
> connector logged no request at all.
>
> So the job's own name is the first query, deterministically, and the
> model's first decision is made with results in front of it. Cheaper
> by a call, and it means "the mailbox does not hold this" is always a
> statement about the mailbox rather than about the prompt.

## `GatherContext.execute`, [line 66](../../../../../../../backend/src/sro/application/execution/gather.py#L66): Comment

Code: `left = until - time.monotonic()`

> What is left of the budget, and never more. `K_ROUNDS` bounds
> how many times this looks; this bounds how long looking may
> take, which on the day the model answers with a 5xx is a
> different number by two orders of magnitude.

## `GatherContext.execute`, [line 68](../../../../../../../backend/src/sro/application/execution/gather.py#L68): Comment

Code: `return Gathered(`

> The same answer as a mailbox that holds nothing, because to
> the run it is the same fact: nobody found the value, so a
> person is asked. What WAS found is kept -- a code read in the
> first round is not less true for the second round being slow.

## `GatherContext.execute`, [line 118](../../../../../../../backend/src/sro/application/execution/gather.py#L118): Comment

Code: `unasked |= set(dropped(offered, wanted))`

> What it offered that this job has no parameter for, kept so
> somebody can be told. See `dropped`.

## `GatherContext.execute`, [line 126](../../../../../../../backend/src/sro/application/execution/gather.py#L126): Comment

Code: `history.append(note("nothing was asked", str(answer.data.get("why") or "")))`

> A round that asked for nothing is a round that cannot be
> followed by a better one: the history would be identical and
> so would the next answer. Stopping is cheaper than spending
> the rest of the budget proving it.

## `GatherContext._look`, [line 151](../../../../../../../backend/src/sro/application/execution/gather.py#L151): Comment

Code: `tool, arguments = "get_message", {"id": message}`

> `id`, which is what the connector declares. It was `message_id`
> for one afternoon and every read asked for an empty id, so the
> loop searched six times against bodies that were never fetched --
> and refused, correctly, on nothing. An argument name is a
> contract between two programs;
> `test_the_gather_asks_for_what_the_connector_declares` holds it.
