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

## `TaskName`, [line 35](../../../../../../../backend/src/sro/application/ports/interpretation.py#L35): Docstring

> One line a warehouse person would recognise, for a task the miner found.
>
> Cosmetic by construction: what a candidate *is* stays its signature, so two
> candidates named differently are still one candidate and two named the same
> are still two. Empty means the model had nothing to say, and the derived
> title stands.

## `Judgement`, [line 41](../../../../../../../backend/src/sro/application/ports/interpretation.py#L41): Docstring

> Whether two candidates are one piece of work, and why the model thinks so.
>
> A suggestion about candidates, never a change to them. Nothing downstream
> reads it: a person does.

## `WorkflowInterpreter.read`, [line 50](../../../../../../../backend/src/sro/application/ports/interpretation.py#L50): Docstring

> Interpret one demonstration, rendered as text.
>
> Takes text rather than the aggregate on purpose: what gets sent to a
> hosted model is assembled and redacted by the caller, so the adapter has
> no way to widen it.

## `WorkflowInterpreter.name_task`, [line 52](../../../../../../../backend/src/sro/application/ports/interpretation.py#L52): Docstring

> Name a task the miner found, from what it is made of.
>
> The derived title is honest and unreadable -- `Adjust inventory on
> bf56-kms-wms-web-np2.jdadelivers.com` -- and this is the one thing a
> model is unambiguously better at. It renames nothing else: the
> signature is the identity, and it is not shown this method's answer.

## `WorkflowInterpreter.judge_join`, [line 54](../../../../../../../backend/src/sro/application/ports/interpretation.py#L54): Docstring

> Are these two candidates the same piece of work (`variant`), or two
> halves of one (`workflow`)?
>
> Asked only about a pair a deterministic filter already found plausible,
> because the answer is a suggestion on a screen and a model call per pair
> of a day's candidates is not something to spend by default.
