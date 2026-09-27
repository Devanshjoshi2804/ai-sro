# Notes for `backend/evals/suites/mining.py`

The mining suite: does MINE find a job the operator really did?

## `K_NOISE_S`, [line 23](../../../../../backend/evals/suites/mining.py#L23): Constant

> Five minutes either side of a job's first and last cite, on the same
> streams: the neighbouring noise of spec §2.2's "A job's cited gestures plus
> neighbouring noise".

## `request_values`, [line 26](../../../../../backend/evals/suites/mining.py#L26): Design

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

## `Mining.cases`, [line 83](../../../../../backend/evals/suites/mining.py#L83): Design

> One case per known job: its cited gestures plus the noise around them, as
> `as_evidence` renders them for the real pass, and the crossings over that
> day. Expected: the job's cites and its `request_values`.

## `Mining.run`, [line 133](../../../../../backend/evals/suites/mining.py#L133): Design

> Runs the production `propose`, so the case measures the prompt that ships.
> Passes when one proposed job cites at least `K_COVERS` of the expected
> cites, at least `K_OWN` of its own cites are the case's, and it holds every
> expected value among the parameters it SHIPS (`_shipped`): the model's
> `seen_values` plus what the typed-values rule in code adds
> (`parameters_across`, M3), over gestures rebuilt from each day item's
> `evidence.gesture` (`_gesture`: kind, value, accessible name, label, item
> id). Scoring only `propose()` could not show M3, which moved parameters
> from the model to code. A truncated item carries no value and adds
> nothing, so the score under-counts rather than over-counts. The case
> format is unchanged. An errored call is
> carried on `Scored.error`. `propose` gets no known jobs and no knowledge,
> as the brief set it: the eval cannot see extend-don't-mint behaviour.
> `Mining.asker` is the container's patient mining asker, the one `mine_pass`
> uses (its timeout is the mining one, not the default 120 s). Sure means anything at all was proposed: a proposal that covers
> nothing is a confident wrong answer.

## `Mining.cases`, [line 91](../../../../../backend/evals/suites/mining.py#L91): Comment

Code: `if workflow.chore:`

> No case from a chore. The miner is right to skip a sign-in, so a case
> expecting one is a miss it could never avoid -- the greyorange baseline
> (MINE v2) carried several of its 8 empty answers this way. The frozen set must
> be rebuilt (`rebuild=1`) for this to take, which retires that baseline.
