# Notes for `backend/src/sro/domain/execution/escalation.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/escalation.py`](../../../../../../../backend/src/sro/domain/execution/escalation.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/escalation.py#L1): Docstring

> When a rung fails, what may try next -- as a table rather than as branches.
>
> Every entry is a claim about *why* the step failed, and whether a slower medium
> could plausibly do better. Three of them are refusals, and those matter most: a
> browser cannot fix a missing credential, pointing one at a system that just
> timed out turns an outage into a heavier outage, and a step that never asked the
> server anything has nothing for a network run to escalate.
>
> **A step may escalate; a task escalates better.** A run that swaps medium
> half way through leaves the browser without the screen state the earlier steps
> would have produced, so a lone UI step often cannot find its control. The
> coherent unit is the whole task: run it over the network, and if that fails in a
> way the table says the interface can handle, run the task again in the browser
> from the first step. Choosing that automatically is Phase 5's job -- it is the
> same decision as the circuit breaker -- so today the medium is chosen when the
> run is requested, and this table says which failures make that choice sensible.

## `FailureKind`, [line 10](../../../../../../../backend/src/sro/domain/execution/escalation.py#L10): Note on the line above

Code: `NO_PLAN = "no_plan"`

> This rung has nothing to perform. Not a failure of the system.

## `FailureKind`, [line 12](../../../../../../../backend/src/sro/domain/execution/escalation.py#L12): Note on the line above

Code: `UNREPLAYABLE = "unreplayable"`

> The recorded call cannot be reproduced as a call at all.

## `FailureKind`, [line 14](../../../../../../../backend/src/sro/domain/execution/escalation.py#L14): Note on the line above

Code: `STATUS_MISMATCH = "status_mismatch"`

> The call went out and the system answered differently than it did for the
> human. Often the UI has moved on and the recorded endpoint has not.

## `FailureKind`, [line 16](../../../../../../../backend/src/sro/domain/execution/escalation.py#L16): Note on the line above

Code: `ASSERTION_FAILED = "assertion_failed"`

> It answered, and the answer was not the one the demonstration proved.

## `FailureKind`, [line 20](../../../../../../../backend/src/sro/domain/execution/escalation.py#L20): Note on the line above

Code: `UNREACHABLE = "unreachable"`

> Nothing was there to answer: a closed laptop, no tab open on the system,
> a connection that died before a response. Not a claim about the skill, which
> is why a run that ends this way is not held against it.

## `FailureKind`, [line 21](../../../../../../../backend/src/sro/domain/execution/escalation.py#L21): Note on the line above

Code: `TOOL_UNAVAILABLE = "tool_unavailable"`

> The connector is not configured, is unreachable, or does not offer the
> tool this step names. Not a claim about the skill.

## `FailureKind`, [line 23](../../../../../../../backend/src/sro/domain/execution/escalation.py#L23): Note on the line above

Code: `CONTROL_NOT_FOUND = "control_not_found"`

> A UI rung could not find the control. The skill has drifted from the
> system it was taught on.

## `EscalationRule`, [line 30](../../../../../../../backend/src/sro/domain/execution/escalation.py#L30): Note on the line above

Code: `then: Medium | None`

> ``None`` means stop. Stopping is a decision with a reason, not an
> absence of one.

## `next_medium`, [line 135](../../../../../../../backend/src/sro/domain/execution/escalation.py#L135): Docstring

> The rule that applies, or ``None`` when nothing does.
>
> An unmatched combination stops the step. Silence is the safe default here:
> a missing rule means nobody has decided this case, and inventing an
> escalation for it points a less deterministic medium at a live warehouse.
