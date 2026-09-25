# Notes for `backend/src/sro/domain/execution/lanes.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/lanes.py`](../../../../../../../backend/src/sro/domain/execution/lanes.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 13](../../../../../../../backend/src/sro/domain/execution/lanes.py#L13): Note on the line above

Code: `K_SIGHT_ACTIONS = 6`

> §6.1's fixed number of actions per step for the sight lane: a Computer Use
> loop that could act without limit would let one step keep spending model
> calls and cost against a job that has already gone wrong, rather than fail
> and hand the step to the operator (D4).

## `Lane`, [line 16](../../../../../../../backend/src/sro/domain/execution/lanes.py#L16): Docstring

> The four lanes an executor actually runs a step on (§6.1): a tool call, an
> API replay, the UI, or the sight model. `operator` (D7) is deliberately
> not a fifth member here, even though it is a value `StepMark.lane` can
> hold (D1 typed that field as a bare `str` for exactly this reason). A
> write the operator made in their own browser before a Steel takeover was
> never executed by any of these four -- nothing here drove it, verified it
> or can be asked to run it again -- so it does not belong on the ladder
> `lanes_for` walks or the known-broken list `Broken` names. D7's own plan
> keeps it as a plain string recorded on a mark and checks for it explicitly
> (`RunSteps.step`'s already-written branch treats a `Lane` value and the
> literal `"operator"` differently) rather than teaching this enum a state
> that never executes anything.

## `Verdict`, [line 23](../../../../../../../backend/src/sro/domain/execution/lanes.py#L23): Note on the line above

Code: `Verdict = Literal["done", "read", "failed", "unknown"]`

> §6.2's four, verbatim -- "There is no bare success." Not D1's `Wrote`
> (`progress.py`), which shares three of the four spellings but names a
> different thing: `Verdict` is what a lane decided about one attempt at one
> step; `Wrote` is what `Progress` has durably recorded about whether a
> write went out, across however many attempts and retries a step takes to
> settle. A step can be `verdict="unknown"` on its first try and still end
> `wrote="done"` once a read-back or an operator's answer settles it -- the
> two only ever meet at `StepResult.verdict`, which is one of the inputs
> `Progress.settle` takes to decide the other.

## `StepResult.never_left`, [line 42](../../../../../../../backend/src/sro/domain/execution/lanes.py#L42): Comment

Code: `never_left: bool = False`

> Whether this one attempt at the step left at all: `True` means no request
> for the step's write ever reached the target from this lane -- a UI lane
> that never found the submit control never left; one that clicked it and
> then lost the page might have. Defaults to `False`, the safe reading: a
> lane that says nothing about whether its write left is treated as one
> that might have. D1's `Progress.settle(..., never_left=True)` clears a
> `sending` mark back to unsent only when the caller can say the write is
> confirmed never to have reached the far side; otherwise a `failed`
> verdict becomes `unknown`, never "safe to retry". A step tries more than
> one lane, so a single attempt's flag is not the answer for the step --
> `never_left_step` combines every attempt tried for the step (X8's job)
> before it reaches `settle`.

## `never_left_step`, [line 109](../../../../../../../backend/src/sro/domain/execution/lanes.py#L109): Docstring

> ANDs `never_left` across every lane tried for one step: the step itself
> never left only if none of its attempts did. One lane that reached the
> target (API 5xx, say) makes the step's own write uncertain even if a
> later lane in the same step gave up before trying -- the step's
> `never_left` cannot be truer than its least certain attempt. Vacuously
> `True` on no attempts, which never happens through `RunSteps.step` (a
> step always tries at least one lane) but keeps the function total.

## `fingerprint_of`, [line 66](../../../../../../../backend/src/sro/domain/execution/lanes.py#L66): Docstring

> Names a failure by its lane, its kind, and the evidence it happened
> against -- not just the lane and the kind. §6.3's known-broken list is
> cleared "when that lane later succeeds for the step: repair, or a new
> doing of the job" -- and a new doing is a new demonstration, whose
> evidence differs from the old one's even when the step and the lane are
> the same. Two fingerprints that dropped the evidence would call a UI
> failure against the old recording and a UI failure against the new one
> the same broken entry, and a repaired step would still read as broken
> against a doing that never actually failed on it.

## `lanes_for`, [line 70](../../../../../../../backend/src/sro/domain/execution/lanes.py#L70): Docstring

> §3's ladder, walked once per step per run: tool if the step uses one,
> else API before UI before sight for a browser step, and never more than
> one of tool or the browser pair -- a mail step is a tool call and never a
> tab. Every entry drops out once it is on `broken` for this step and this
> run, except the ladder's own last entry (sight for a browser step, the
> only lane for a tool step), which is always offered even broken: it is
> the one lane whose failures are per run rather than sticky (§3), and a
> step with every lane dropped would never be tried again until someone
> re-recorded the job. What is left, in order, is the run's own retry
> path if an earlier lane fails without settling the step.

## `accepts`, [line 83](../../../../../../../backend/src/sro/domain/execution/lanes.py#L83): Docstring

> The status test `write_confirmed` applies to a write's own call: one of the
> statuses the belts expect, or any 2xx when none is recorded. Shared so a lane
> can name the call that confirmed the write.
