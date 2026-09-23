# Notes for `backend/src/sro/domain/execution/rescued.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/rescued.py`](../../../../../../../backend/src/sro/domain/execution/rescued.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/rescued.py#L1): Docstring

> What the operator did after a step failed, taken as the repair for it.
>
> A run's only self-repair is the locator ladder: when the job's own identity for
> a control misses and a weaker rung finds it, the run writes that down and the
> next run tries it first. That heals a control that MOVED. It does nothing at
> all for a step that fails the same way every time on a control that is exactly
> where the job says it is.
>
> Measured on the deployment 2026-09-19. `Delete a Customer Type` failed four
> times in twenty minutes, every time on its first step -- *"the filter dropdown
> is not open on the screen"* -- and every time the operator did that click by
> hand a moment later and carried on. All of it was captured: the tab was
> watched, the gestures are in the store, and the miner read them a minute
> later. Nothing reached the failing step, because mining resolves a whole new
> demonstration into the existing job rather than repairing one step of it.
>
> **So the rescue is the lesson.** A person who fixes by hand the exact thing a
> run could not do has just demonstrated the repair, on the same screen, seconds
> later. This is the rule for recognising that, and it is deliberately narrow:
>
> **After the run, never during it.** A run drives the browser, and what it
> drives is recorded like anything else. Only gestures after `finished_at` can
> be the operator's own.
>
> **Soon, or not at all.** `K_SOON` is minutes, not hours: the person who picks
> the job up again after lunch is doing today's work, not correcting this run.
>
> **On the screen the step was on.** A gesture in another system is somebody
> getting on with something else.
>
> **The first one, and only if it names a control.** The operator's next act is
> the one that answers "what should this step have done"; a scroll or a click on
> nothing names no control and teaches nothing.
>
> **Never the job's own answer.** Where the job's recorded identity for that step
> already matches what they clicked, there is nothing to learn: the step knew the
> control and failed for another reason, and writing it down would be the job
> telling itself what it already says.

## module, [line 11](../../../../../../../backend/src/sro/domain/execution/rescued.py#L11): Note on the line above

Code: `K_SOON = 300.0`

> How long after a run a gesture can still be its repair, in seconds.
>
> Five minutes. Long enough for somebody to read the card, look at the screen and
> do the thing; short enough that the next morning's work is not read as a
> correction to last night's failure.

## module, [line 13](../../../../../../../backend/src/sro/domain/execution/rescued.py#L13): Note on the line above

Code: `BY_HAND = "by_hand"`

> What wrote this locator down, where the ladder writes `sight` or `css_path`.
>
> On the row so a person reading `workflow_learned_history` can tell a job that
> healed itself from one a human repaired -- and so that the day this rule is
> wrong about something, every row it wrote can be found.

## `rescued_by`, [line 16](../../../../../../../backend/src/sro/domain/execution/rescued.py#L16): Docstring

> The control the operator used after this step failed, as a locator.
>
> `since` is the run's own end, as a gesture clock reads it; `failed_at` is
> the origin the step was working on.

## `_already_says`, [line 47](../../../../../../../backend/src/sro/domain/execution/rescued.py#L47): Docstring

> Whether the job's own evidence for this step already names that control.
