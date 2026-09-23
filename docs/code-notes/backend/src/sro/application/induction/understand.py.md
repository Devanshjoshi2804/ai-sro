# Notes for `backend/src/sro/application/induction/understand.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/understand.py`](../../../../../../../backend/src/sro/application/induction/understand.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/understand.py#L1): Docstring

> One demonstration to a usable skill.
>
> The two-run diff is still the better instrument, and where two runs exist it is
> what runs. This is for the ordinary case the diff cannot serve: a task nobody
> can perform twice identically, or a task somebody only had time to do once.
>
> The split is the point. **The calls are evidence and are untouched.** The
> narrative -- what each step was for, what the whole thing accomplishes, which
> values look like inputs -- is a model reading the same evidence, and every part
> of it is marked as read rather than proven. A candidate parameter that cannot be
> found in a captured payload is dropped: a parameter nobody can point at in the
> evidence is a hallucination with a name.

## `as_evidence`, [line 169](../../../../../../../backend/src/sro/application/induction/understand.py#L169): Docstring

> The demonstration as text a model can read.
>
> Bodies are included because they are where the values are, and they have
> already had credentials removed at capture time -- this sends what is
> stored, and what is stored never held a password.
>
> URLs are cleaned here rather than at capture, because the URL is the
> evidence: which endpoint was called is the whole point of keeping it. What
> a hosted model has no use for is the query string's values, and a system
> that puts a session key or a one-time token in one -- several do -- was
> sending it to Google in full.

## `_clean`, [line 187](../../../../../../../backend/src/sro/application/induction/understand.py#L187): Docstring

> The URL with any credential-shaped query value taken out.

## `_calls`, [line 200](../../../../../../../backend/src/sro/application/induction/understand.py#L200): Docstring

> Every call this gesture made. Not the "primary" one: reading only that
> hid the call that created the record from the model doing the reading.

## `_entered`, [line 207](../../../../../../../backend/src/sro/application/induction/understand.py#L207): Docstring

> Values a person typed that the calls afterwards carried.
>
> Not an inference, and not a model's: the frame records that a human entered
> this value and the control records what it was called. Without this, one
> demonstration has nothing to disagree with, so the supplier code somebody
> had just typed into a box looked as fixed as the endpoint -- and replaying it
> creates that same supplier again.
>
> The two-run path has recovered these since the day it was written. This one
> is the path a mined candidate takes, which is now most of them.

## `_believable`, [line 215](../../../../../../../backend/src/sro/application/induction/understand.py#L215): Docstring

> Candidates whose value actually appears in what was captured.
>
> The check that keeps this honest: a model can name any parameter it likes,
> and only the ones pointing at a literal in the evidence survive.
>
> A value already recovered from a typed box is skipped whatever the model
> called it: two names for one value would put two placeholders at one site,
> and the second would quietly win.

## `_steps`, [line 247](../../../../../../../backend/src/sro/application/induction/understand.py#L247): Docstring

> Steps built from the evidence, described by the reading.

## `_substitutions`, [line 279](../../../../../../../backend/src/sro/application/induction/understand.py#L279): Docstring

> This step's placeholders, in the shape the emitter already understands.

## `_replacements`, [line 291](../../../../../../../backend/src/sro/application/induction/understand.py#L291): Docstring

> Where each candidate value sits in this step, so the plan carries a
> placeholder rather than one run's literal.

## `_no_assertions`, [line 332](../../../../../../../backend/src/sro/application/induction/understand.py#L332): Docstring

> What a single run can assert: the status the system actually answered.
>
> Deliberately thin. The read-back comparison that a pair produces is not
> available here, and inventing a richer assertion from one observation is how
> a verifier starts failing correct runs.

## `UnderstandRecording.execute`, [line 105](../../../../../../../backend/src/sro/application/induction/understand.py#L105): Comment

Code: `entered = _entered(recording.frames)`

> Typed first, and they win. A frame recording that a human entered a
> value is stronger evidence than a model's reading of the same text --
> and it is the value most certain to want a different answer next run.

## `UnderstandRecording.execute`, [line 139](../../../../../../../backend/src/sro/application/induction/understand.py#L139): Comment

Code: `aligned_recording_ids=(recording.id,),`

> `_steps` builds every step from this one recording's
> frames -- the whole point of the single-run path -- so
> this is exactly the case the default `()` must not be
> left to stand in for.

## `UnderstandRecording.execute`, [line 151](../../../../../../../backend/src/sro/application/induction/understand.py#L151): Comment

Code: `systems=systems_touched(`

> Read here as well as on the two-run path: a workflow taught
> from a single occurrence is still a workflow, and a version
> that does not say so is one no breaker guards and no rule
> binds to a browser.

## `UnderstandRecording.execute`, [line 156](../../../../../../../backend/src/sro/application/induction/understand.py#L156): Comment

Code: `version.earn(Verdict.WITHHELD, now)`

> Straight to rehearsing, once it is attached: a version is added at
> RECORDED and cannot be run there, so it could never earn the rung
> that lets it run. Nothing is sent at the next one -- the request is
> built and withheld for somebody to read, and withholding it from
> the operator too is not caution, just a skill nobody can review.

## `_steps`, [line 254](../../../../../../../backend/src/sro/application/induction/understand.py#L254): Comment

Code: `for position, frame in enumerate(unfold(recording.frames)):`

> Unfolded, so a Save that created a record and then addressed it becomes
> two steps rather than one step that replays half the task.

## `_steps`, [line 265](../../../../../../../backend/src/sro/application/induction/understand.py#L265): Comment

Code: `step = SkillStep(`

> The model's sentence is a better label than "click button#x". It
> is a label only: the plans underneath are untouched.
