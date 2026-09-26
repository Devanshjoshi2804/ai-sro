# Notes for `backend/evals/suites/mining.py`

The mining suite: does MINE find a job the operator really did?

## `K_NOISE_S`, [line 15](../../../../../backend/evals/suites/mining.py#L15): Constant

> Five minutes either side of a job's first and last cite, on the same
> streams: the neighbouring noise of spec §2.2's "A job's cited gestures plus
> neighbouring noise".

## `request_values`, [line 18](../../../../../backend/evals/suites/mining.py#L18): Design

> The crossing values ("Values appearing in more than one system") seen on the
> job's own cites. A value typed in the mail and again in the app is what the
> request asked for, so the job must hold it in a parameter: a job that keeps
> it as fixed step text ("Create a Customer Type" mined with no parameters,
> its codes inside a "Read email instructions" step) cannot run the next
> request, and scores a miss.

## `Mining.cases`, [line 34](../../../../../backend/evals/suites/mining.py#L34): Design

> One case per known job: its cited gestures plus the noise around them, as
> `as_evidence` renders them for the real pass, and the crossings over that
> day. Expected: the job's cites and its `request_values`.

## `Mining.run`, [line 73](../../../../../backend/evals/suites/mining.py#L73): Design

> Runs the production `propose`, so the case measures the prompt that ships.
> Passes when one proposed job cites at least `K_COVERS` of the expected
> cites and holds every expected value among its parameters' `seen_values`. Sure means anything at all was proposed: a proposal that covers
> nothing is a confident wrong answer.
