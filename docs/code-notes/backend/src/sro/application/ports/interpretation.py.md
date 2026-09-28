# Notes for `backend/src/sro/application/ports/interpretation.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/interpretation.py`](../../../../../../../backend/src/sro/application/ports/interpretation.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/interpretation.py#L1): Docstring

> Reading one demonstration as a workflow.
>
> The two-run diff proves things. This does not: it *reads* a single
> demonstration -- the gestures, the calls, the responses, the narration -- and
> says what the operator was doing and which values look like inputs. That is a
> model's opinion, and everything it produces is labelled as one.
>
> What it is allowed to change is nothing. The calls stay exactly as captured; the
> interpretation adds a title, a description, a sentence per step, and candidate
> parameters. A candidate whose value never appears in the evidence is discarded
> before it reaches the skill, because a parameter nobody can point at in a
> payload is a hallucination with a name.

## `StepReading`, [line 10](../../../../../../../backend/src/sro/application/ports/interpretation.py#L10): Note on the line above

Code: `what: str`

> One sentence: what this step did, in the warehouse's own words.

## `StepReading`, [line 12](../../../../../../../backend/src/sro/application/ports/interpretation.py#L12): Note on the line above

Code: `why: str = ""`

> Why it was done, where the narration or the response says so.

## `CandidateParameter`, [line 18](../../../../../../../backend/src/sro/application/ports/interpretation.py#L18): Note on the line above

Code: `value: str`

> The literal seen in this run. Checked against the captured payloads
> before it is believed.

## `Reading`, [line 25](../../../../../../../backend/src/sro/application/ports/interpretation.py#L25): Docstring

> What one demonstration appears to have been.

## `Reading`, [line 31](../../../../../../../backend/src/sro/application/ports/interpretation.py#L31): Note on the line above

Code: `caveat: str = ""`

> Anything the model could not account for. Kept, because "I did not
> understand step 4" is the most useful thing it can say.

## `WorkflowInterpreter.read`, [line 38](../../../../../../../backend/src/sro/application/ports/interpretation.py#L38): Docstring

> Interpret one demonstration, rendered as text.
>
> Takes text rather than the aggregate on purpose: what gets sent to a
> hosted model is assembled and redacted by the caller, so the adapter has
> no way to widen it.
