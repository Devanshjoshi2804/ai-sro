# Notes for `backend/evals/suites/mining.py`

The mining suite: does MINE find a job the operator really did?

## `K_NOISE_S`, [line 19](../../../../../backend/evals/suites/mining.py#L19): Constant

> Five minutes either side of a job's first and last cite, on the same
> streams: the neighbouring noise of spec §2.2's "A job's cited gestures plus
> neighbouring noise".

## `request_values`, [line 22](../../../../../backend/evals/suites/mining.py#L22): Design

> The values typed in this doing that any job of the same normalised title
> holds among its parameters' `seen_values`: what the job has been seen to
> vary, re-observed here. A job that covers the cites but keeps those values
> as fixed step text cannot run the next request, so it scores a miss. The
> 0-parameter "Create a Customer Type" duplicates (`wfl_88bc`, `wfl_464d`)
> miss their own cases this way, and the 4-parameter job passes its own.
>
> Ceiling: the truth is the stored jobs, mining errors included. A sibling
> that stored search-as-you-type fragments as seen values makes those
> fragments expected (`wfl_b8b3` misses its own case on two of them).

## `Mining.cases`, [line 38](../../../../../backend/evals/suites/mining.py#L38): Design

> One case per known job: its cited gestures plus the noise around them, as
> `as_evidence` renders them for the real pass, and the crossings over that
> day. Expected: the job's cites and its `request_values`.

## `Mining.run`, [line 86](../../../../../backend/evals/suites/mining.py#L86): Design

> Runs the production `propose`, so the case measures the prompt that ships.
> Passes when one proposed job cites at least `K_COVERS` of the expected
> cites and holds every expected value among its parameters' `seen_values`. Sure means anything at all was proposed: a proposal that covers
> nothing is a confident wrong answer.
