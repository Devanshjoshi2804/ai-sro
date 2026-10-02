# Notes for `backend/src/sro/domain/execution/lanes.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/lanes.py`](../../../../../../../backend/src/sro/domain/execution/lanes.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 17](../../../../../../../backend/src/sro/domain/execution/lanes.py#L17): Note on the line above

Code: `K_SIGHT_ACTIONS = 6`

> §6.1's fixed number of actions per step for the sight lane: a Computer Use
> loop that could act without limit would let one step keep spending model
> calls and cost against a job that has already gone wrong, rather than fail
> and hand the step to the operator (D4).

## `Lane`, [line 22](../../../../../../../backend/src/sro/domain/execution/lanes.py#L22): Docstring

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

## `Verdict`, [line 29](../../../../../../../backend/src/sro/domain/execution/lanes.py#L29): Note on the line above

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

## `StepResult.never_left`, [line 48](../../../../../../../backend/src/sro/domain/execution/lanes.py#L48): Comment

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

## `never_left_step`, [line 146](../../../../../../../backend/src/sro/domain/execution/lanes.py#L146): Docstring

> ANDs `never_left` across every lane tried for one step: the step itself
> never left only if none of its attempts did. One lane that reached the
> target (API 5xx, say) makes the step's own write uncertain even if a
> later lane in the same step gave up before trying -- the step's
> `never_left` cannot be truer than its least certain attempt. Vacuously
> `True` on no attempts, which never happens through `RunSteps.step` (a
> step always tries at least one lane) but keeps the function total.

## `fingerprint_of`, [line 75](../../../../../../../backend/src/sro/domain/execution/lanes.py#L75): Docstring

> Names a failure by its lane, its kind, and the evidence it happened
> against -- not just the lane and the kind. §6.3's known-broken list is
> cleared "when that lane later succeeds for the step: repair, or a new
> doing of the job" -- and a new doing is a new demonstration, whose
> evidence differs from the old one's even when the step and the lane are
> the same. Two fingerprints that dropped the evidence would call a UI
> failure against the old recording and a UI failure against the new one
> the same broken entry, and a repaired step would still read as broken
> against a doing that never actually failed on it.

## `lanes_for`, [line 79](../../../../../../../backend/src/sro/domain/execution/lanes.py#L79): Docstring

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
>
> A step with no lane at all (no tool, no replay, no gesture to aim at)
> has an empty ladder: `()`, never an index into nothing.

## `accepts`, [line 94](../../../../../../../backend/src/sro/domain/execution/lanes.py#L94): Docstring

> The status test `write_confirmed` applies to a write's own call: one of the
> statuses the belts expect, or any 2xx when none is recorded. Shared so a lane
> can name the call that confirmed the write.

## module, [line 19](../../../../../../../backend/src/sro/domain/execution/lanes.py#L19): Note

Code: `K_CONFLICT = 409`

> The one refusal that does not prove a write was never made. A 409 usually
> means the record already exists -- most likely because this very write went
> through (an operator's save, an earlier attempt). So it is in doubt, like a
> 5xx: settled by a read-back or a question, never sent again.

## `write_confirmed`, [line 113](../../../../../../../backend/src/sro/domain/execution/lanes.py#L113): Note

Code: `if any(status >= 500 or status == K_CONFLICT for status in statuses):`

> The one rule for what a write's own call says, for every lane and for a
> takeover's reading of the operator's calls: an accepted status is `done`; a
> 5xx or a 409 is `unknown` (it may have written); any other 4xx is `failed`,
> and a `failed` from here means the system refused it -- the write was never
> made, so each lane returns it with `never_left` and the step may run again.
> Before D7 round 2 a 409 was `failed`, and the lanes returned `failed`
> without `never_left`: the API lane's 409 then fell through to the UI lane,
> which sent the write a second time, and a refused write was left in doubt.

## `same_call`, [line 120](../../../../../../../backend/src/sro/domain/execution/lanes.py#L120): Docstring

> Whether a seen call is the recorded one: same method, same path shape, same
> host, sent from the frame this step acted in (`SeenCall.own_frame`, set by
> the driver when the request went out), and -- when the recorded call has a
> JSON or form body -- the same top-level request body keys. Method and path
> shape alone let any background call to the same RPC-style endpoint (a
> poller, an iframe widget, another host reusing the path) settle the write;
> the frame and body checks are what a strict "own call" means (X4 re-review
> R1). Values are never compared, only keys: a legitimate retry that resends
> the same fields with a different value is still this step's call.
>
> Here, in the domain beside `write_confirmed`, rather than in the UI lane:
> a takeover (spec §7.6) confirms the operator's own writes by the same rule.

## `K_BROKEN_COOL_DOWN`, [line 18](../../../../../../../backend/src/sro/domain/execution/lanes.py#L18): Constant

> How long a lane marked broken stays skipped. Only a winning run mends a lane,
> so without this one outage kept a lane (and, in the compile check, a job)
> skipped forever. After the cool-down `broken_for` stops returning the row,
> the lane is tried once more, and a second failure re-stamps it
> (`break_lane` upserts `at`) for another cool-down: one retry per cool-down.
