# Notes for `backend/src/sro/domain/execution/learned_step.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/learned_step.py`](../../../../../../../backend/src/sro/domain/execution/learned_step.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L1): Docstring

> What a run found out about a step, kept for the next one.
>
> `mark_stale` is this module's negative twin: a step that only the weakest rung
> could find is recorded as about to break. Nothing recorded what the rung
> actually FOUND, so the discovery lived for one command and the next run climbed
> the same ladder to reach the same control.
>
> Measured on the deployment, 2026-09-17. `Create a Customer Type` step 2 clicks
> a tab whose recorded identity no longer matches anything: three runs in one
> afternoon paid for two model calls each, worked out that the control is called
> "Customer Types", and wrote it into a log line. At the end of the afternoon the
> job knew exactly what it knew at the start. That is not a system that learns --
> it is one that repeats.
>
> **What is kept is a locator, not a point.** A point is where a control was on
> one screen at one size; a name is what it is. The rung that looks at a picture
> is the expensive one and the only one that can recover from a page that moved,
> so its answer is the one worth keeping -- as `text=Customer Types`, which every
> run after it can try first for the price of a DOM query.
>
> **A run may write this and may not write the workflow.** The workflow is what a
> mining pass produces from evidence; this is what one run observed, and the two
> are kept apart so neither rewrites the other. Same reason the stale table
> exists, and the same shape: one row per step, the last answer winning.

## module, [line 11](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L11): Note on the line above

Code: `K_NAME = 80`

> How much of a control's name is kept. A button's accessible name is a few
> words; eighty characters is a label, and anything longer is a paragraph that
> happens to sit in a `<div>`.

## module, [line 13](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L13): Note on the line above

Code: `WORTH_KEEPING = ("sight", "css_path", "text")`

> The rungs whose answer is worth writing down.
>
> `component` and `test_id` are the job's own recorded identity -- when they
> match, the job is right and there is nothing to learn. These three are what a
> run falls back to when it is not, and `sight` is the one that costs a model
> call and a picture.

## module, [line 45](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L45): Note on the line above

Code: `HOLDS = "holds"`

> What a change can be about. Two constants rather than two tables: they are
> the same event -- a job changed its mind about a step -- and a reader wants
> them in one order.

## `LearnedStep`, [line 17](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L17): Docstring

> One step, and the locator that last worked for it.

## `LearnedStep`, [line 21](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L21): Note on the line above

Code: `found_by: str`

> Which rung produced it, so a reader can tell a name a picture found from
> one a css path did.

## `LearnedStep`, [line 23](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L23): Note on the line above

Code: `holds: int | None = None`

> How many characters this step's box will take, where a run found out.
>
> A field truncates in the browser, before the request, and the only moment
> the difference exists is between the value the step was given and the value
> the box ends up holding. Catching that every time is repeating; this is the
> half that makes it learning.
>
> None until a run has been told otherwise -- which is every step that does
> not type, and every typing step whose value has always fitted.

## `Taught`, [line 31](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L31): Docstring

> One thing a job changed its mind about, and what it changed from.
>
> A learned fact is stored as one row per step with the last answer winning,
> which is right for the question a run asks -- what should I try first --
> and leaves nothing behind. A locator learned from a screenshot that quietly
> replaced one learned from a component is a job that drifted, and the only
> record of it was the difference between two runs nobody compared.
>
> So a change is a thing with a shape: what it was about, what it was, what
> it became, which run taught it and how. A confirmation is not a change --
> see `changed_by` -- because four hundred rows saying "the same locator
> again" bury the four that matter.

## `changed_by`, [line 48](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L48): Docstring

> What this step just learned that it did not already know.
>
> Both halves in one pass, because a run can change both at once: the rung
> that found a control by picture also measured what its box would hold.
>
> A locator is compared as `strategy=query`, which is what makes it the same
> locator: the two together are the answer, and the rung that produced it is
> recorded beside the change rather than folded into the comparison -- the
> same query found twice is the same answer however it was found the second
> time, and a row per rung would say a job had drifted when nothing moved.

## `learned_from`, [line 78](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L78): Docstring

> What this step's reply is worth keeping, or None.
>
> Nothing is kept for a step the job's own identity found: that is the
> ordinary case and writing it down would be the job telling itself what it
> already says. Nothing is kept from a reply that names no control either --
> a run cannot pass on what it did not learn.

## `limits_for`, [line 97](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L97): Docstring

> What the boxes behind a job's parameter names will hold, by name.
>
> A limit is learnt about a STEP, because a step is what typed into the box.
> Everything that wants to use it ahead of time -- the question asked of
> somebody whose value was too long, the card asked before the press -- knows
> a parameter's name and not which step fills it. This is that translation,
> in one place, because two copies of it drift the day a job fills one name
> at two steps.
>
> Which is the case the `min` is for. A name typed at two steps has two
> limits and only the smaller one is true of the run: a value that fits the
> first box and not the second still stops the job, and a card that promised
> otherwise lied to the person who pressed.
>
> `declared` is the same rule applied to a second kind of source. What a run
> LEARNT is a measurement and what the vendor's dictionary and the captured
> form DECLARE is a claim, and neither gets to overrule the other here: a
> limit is a ceiling, so every ceiling anything names applies and the lowest
> one binds. Being wrong low asks somebody to shorten a value further than
> they had to. Being wrong high sends `NEWSROTEST`, keeps `NEWS`, and answers
> 201 -- see `application/execution/declared.py`.
>
> Empty by default, which is every caller that has only ever had the
> measurements and behaves exactly as it did.

## `too_long`, [line 112](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L112): Docstring

> The values that will not fit, and what their box actually takes.
>
> The limit and not a flag: "this will not fit" sends somebody back with a
> value that does not fit either, and they have no way to know why -- the
> browser truncates in silence and says nothing at all. What a person needs
> in order to answer once is the number.

## `Taught.worth_keeping`, [line 40](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L40): Docstring

> Whether this is a change at all.
>
> A run that found what the run before it found has taught nothing. And
> the FIRST answer is worth keeping: `was` empty and `now` set is a job
> learning something it never knew, which is the row somebody reads to
> find out where a locator nobody demonstrated came from.

## module, [line 8](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L8): Inline

Code: `if TYPE_CHECKING:`

> a domain type used in a signature, imported for the checker only

## `learned_from`, [line 83](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L83): Comment

Code: `if isinstance(matched, dict) and matched.get("strategy") in WORTH_KEEPING:`

> The locator that worked, where the browser named one: a css path that
> matched is a css path worth trying first next time.

## `learned_from`, [line 87](../../../../../../../backend/src/sro/domain/execution/learned_step.py#L87): Comment

Code: `if isinstance(control, dict):`

> Otherwise the control the point turned out to be, named. This is the
> sight rung's answer turned into something cheap.
