# Notes for `backend/evals/suites/mining.py`

The mining suite: does MINE find a job the operator really did?

## `K_NOISE_S`, [line 20](../../../../../backend/evals/suites/mining.py#L20): Constant

> Five minutes either side of a job's first and last cite, on the same
> streams: the neighbouring noise of spec §2.2's "A job's cited gestures plus
> neighbouring noise".

## `request_values`, [line 23](../../../../../backend/evals/suites/mining.py#L23): Design

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

## `Mining.cases`, [line 42](../../../../../backend/evals/suites/mining.py#L42): Design

> One case per known job: its cited gestures plus the noise around them, as
> `as_evidence` renders them for the real pass, and the crossings over that
> day. Expected: the job's cites and its `request_values`.

## `Mining.run`, [line 90](../../../../../backend/evals/suites/mining.py#L90): Design

> Runs the production `propose`, so the case measures the prompt that ships.
> Passes when one proposed job cites at least `K_COVERS` of the expected
> cites, at least `K_OWN` of its own cites are the case's, and it holds every
> expected value among its parameters' `seen_values`. An errored call is
> carried on `Scored.error`. `propose` gets no known jobs and no knowledge,
> as the brief set it: the eval cannot see extend-don't-mint behaviour.
> `Mining.asker` is the container's patient mining asker, the one `mine_pass`
> uses (its timeout is the mining one, not the default 120 s). Sure means anything at all was proposed: a proposal that covers
> nothing is a confident wrong answer.
