# Notes for `backend/src/sro/domain/skill/learned.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/learned.py`](../../../../../../../backend/src/sro/domain/skill/learned.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/learned.py#L1): Docstring

> What a job takes as input, decided in code from what its doings typed.
>
> Shown one doing of "Create Work Activity TEST1", nothing in the evidence says
> whether `TEST1` is the name of this activity or the name of every activity.
> Until 2026-09-27 that doubt made it fixed text; the greyorange mining baseline
> (MINE v2, 15 cases) then showed the cost: 5 cases where every step was found
> and 0 of 4, or 2 of 6, typed values were parameters -- QA's 0-parameter
> "Create a Customer Type" copies. So since M3 (user-approved) the doubt goes the
> other way: every typed value is a parameter until the evidence proves it
> constant.
>
> Two doings are that proof. What the operator typed identically in every doing
> is part of the job; anything else is input. That is arithmetic over evidence
> rather than an opinion about it -- and not the model's call, which read typed
> values as fixed text.
>
> This is available here because `identity.resolve` already finds the pairs:
> `same_job` means one job matched by SHAPE while citing different gestures --
> two occurrences, which is exactly what a diff needs. Measured on the real
> corpus, thirteen of fourteen second-pass matches came through shape rather than
> citation overlap, so the pairs are the common case rather than the rare one.

## module, [line 8](../../../../../../../backend/src/sro/domain/skill/learned.py#L8): Note on the line above

Code: `K_MIN_OCCURRENCES = 2`

> Doings needed before a value typed identically in each is called a constant.
>
> One is a recording, and one value cannot be told from a constant, so below
> this a typed value is a parameter. The name exists so that a future caller
> raising it -- three doings before trusting a constant, say -- changes a number
> rather than an argument.

## module, [line 10](../../../../../../../backend/src/sro/domain/skill/learned.py#L10): Note on the line above

Code: `K_PARAMETERS_RULE = 1`

> The version of the rule these functions apply, stamped on each job as
> `workflows.parameters_rule` (0089). The sweep brings in every live job stamped
> older or never (`MineLately._bring_in`); a later change to the rule raises
> this and every job is brought in again, once.

## module, [line 13](../../../../../../../backend/src/sro/domain/skill/learned.py#L13): Note on the line above

Code: `K_REQUIRED_MARK = "*"`

> What a form puts on the label of a field that must be filled.
>
> One character, and the only signal the recorder captures today: a gesture's
> target carries `field_label` and no `aria-required`. Widening that is a
> `make gen-recorder` change -- the recorder is generated from this side and is
> never edited by hand -- and until it happens, a page that marks required
> fields by colour alone tells this system nothing, which reads as optional.

## `demanded`, [line 18](../../../../../../../backend/src/sro/domain/skill/learned.py#L18): Docstring

> Whether the page said this stored parameter must be filled.
>
> The same rule as `LearnedParameter.required`, read off a parameter as a
> job stores it. Two callers -- the runner, deciding what stops a run, and
> the question, deciding what to offer instead of demand -- and a rule kept
> in two places is a rule that drifts.
>
> Read off the flag where a pass has written one, and off the names
> otherwise: every parameter stored before 2026-09-22 predates the flag, and
> a migration to add it would be a migration to recompute what the names
> already carry. The flag wins where both speak, because a later pass may
> have learnt from a refusal what no label ever said.

## `offerable`, [line 27](../../../../../../../backend/src/sro/domain/skill/learned.py#L27): Docstring

> The fields a job can fill that nobody has to, with what each was last
> time, for the ones this run has no value for.
>
> The last value and not every value: this is an offer somebody reads in one
> line, and "Department was IN, new, IN, OUTSIDE" is a history rather than a
> suggestion. Most recent, because `seen` is in the order the occurrences
> were seen and the newest is the likeliest to still be right.

## `LearnedParameter`, [line 44](../../../../../../../backend/src/sro/domain/skill/learned.py#L44): Docstring

> One thing a job takes as input, and what it has been given so far.
>
> Named for how it was found. `sro.domain.skill.parameter.Parameter` is the
> backend's own, declared on a skill; this one is the difference between two
> doings, and the two must not be mistaken for each other.

## `LearnedParameter`, [line 45](../../../../../../../backend/src/sro/domain/skill/learned.py#L45): Note on the line above

Code: `name: str`

> The control it was typed into, in the name a person would use: the
> field's own label where the page gives one, its ExtJS itemId otherwise.
> Named after the form rather than after the value, because `activityCode`
> says what it is and `TEST1` says what it was once.

## `LearnedParameter`, [line 47](../../../../../../../backend/src/sro/domain/skill/learned.py#L47): Note on the line above

Code: `seen: tuple[str, ...]`

> Every value observed, in the order the occurrences were seen. Two
> different values is the evidence that this varies at all.

## `LearnedParameter`, [line 49](../../../../../../../backend/src/sro/domain/skill/learned.py#L49): Note on the line above

Code: `key: str = ""`

> The page's own name for the control -- its ExtJS itemId -- where the
> recordings carried one. It is what two doings are matched on when both have
> it, because two fields can share a label and two fields cannot share an
> itemId. Empty where no recording of this control carried one.

## `LearnedParameter`, [line 51](../../../../../../../backend/src/sro/domain/skill/learned.py#L51): Note on the line above

Code: `in_all: bool = True`

> Whether every doing compared reached this control.
>
> A control two doings varied is a parameter -- that is the bar, and it does
> not change. But where a THIRD doing never reached it, the job has a route
> that does not need it, and a run taking that route must not be stopped for
> want of a value. See `_not_given`, which is where the difference is felt.

## `LearnedParameter`, [line 53](../../../../../../../backend/src/sro/domain/skill/learned.py#L53): Note on the line above

Code: `said: bool | None = None`

> What the PAGE itself said, where a recording of this control carried
> it: `aria-required`, the HTML5 attribute, a star on the label, or Ext's
> own `allowBlank: false`. None on every parameter learnt before the
> recorder captured it, which is why `required` still falls back to reading
> the star out of `names`.

## `LearnedParameter`, [line 61](../../../../../../../backend/src/sro/domain/skill/learned.py#L61): Note on the line above

Code: `names: tuple[str, ...] = ()`

> Every name this one control answers to, `name` included.
>
> A control has as many names as the page gives it -- `Customer Type` on the
> label, `customertype-customerType` on the input -- and which of them a
> recording carries is a fact about that recording, not about the job. The
> real `Create a Customer Type` was captured both ways, so its two doings
> named the same two fields four different things and the job came to declare
> four parameters for two fields: two boxes on the offer card per value, and
> a run asked for values nobody has ever typed.
>
> So a parameter carries all of them, and two doings that named one control
> differently are still one control. Empty on every parameter learnt before
> this, which is why the matching that uses it still falls back to the value
> evidence.

## `control_names`, [line 64](../../../../../../../backend/src/sro/domain/skill/learned.py#L64): Docstring

> Every name this control answers to, the readable one first.
>
> The label before the itemId, and that order is the whole of what a person
> ever sees: a parameter called `Customer Type` is one somebody can answer,
> and `customertype-customerType` is the same field wearing the name the form
> posts it under. Both are kept, because a recording carries whichever of
> them the page gave it and a later doing has to be able to find this control
> by either.

## `control_name`, [line 80](../../../../../../../backend/src/sro/domain/skill/learned.py#L80): Docstring

> What one control is called, where one name is wanted. The first of
> `control_names`, which is the readable one.

## `control_key`, [line 85](../../../../../../../backend/src/sro/domain/skill/learned.py#L85): Docstring

> The page's own name for this control -- its ExtJS itemId -- or "".
>
> Kept apart from the rest of its names because it is the only one that
> answers "which control is this" rather than "what is it called". Two
> fields can share a label; two fields do not share an itemId.

## `same_control`, [line 92](../../../../../../../backend/src/sro/domain/skill/learned.py#L92): Docstring

> Whether these name one control.
>
> **Where both recordings carried the page's own name, that decides.** Two
> fields on one form can share a label -- a Description in each of two
> sections -- and merging those would be one parameter where the job has two.
>
> **Otherwise any name in common.** A recording that carries no itemId is the
> case this exists for: `Create a Customer Type` was captured once with
> labels and once with input names, its two doings agreed on nothing, and the
> job came to declare four parameters for two fields -- four boxes on the
> offer card, two of them asking for a name nobody has ever typed.
>
> Deliberately not a comparison of values. `_same_control` in the mining pass
> does that, for parameters stored before any of this was recorded, and it
> merges two controls that happened to vary over one set.

## `_Put`, [line 101](../../../../../../../backend/src/sro/domain/skill/learned.py#L101): Docstring

> One value a doing put into one control, with every name that control
> had in THAT recording.

## `_Put`, [line 105](../../../../../../../backend/src/sro/domain/skill/learned.py#L105): Note on the line above

Code: `required: bool | None = None`

> What the page said about this control in THIS recording, or None where
> it said nothing.

## `_by_control`, [line 108](../../../../../../../backend/src/sro/domain/skill/learned.py#L108): Docstring

> What this doing put into each control it typed into.
>
> Keyed by the control rather than by the step, because two doings of one job
> reach the same control at different step numbers -- the model writes the
> prose freshly each time, and a step index is its opinion. The control is
> the evidence.

## `_page_said`, [line 141](../../../../../../../backend/src/sro/domain/skill/learned.py#L141): Docstring

> Whether the page said this control must be filled, in this recording.
>
> The control's own statement first and the component's second, because the
> DOM is where `aria-required` and the HTML5 attribute live and the star on
> a label is read there too. Ext's `allowBlank: false` is the fallback, and
> it is the one that speaks for a field rendered with neither -- which this
> application does, on the two fields it demands.
>
> None where neither said anything. A recording made before 2026-09-22
> carries neither, which is why `LearnedParameter.required` still falls back
> to the star in the names: the evidence already in the store has to go on
> answering.

## `parameters_across`, [line 153](../../../../../../../backend/src/sro/domain/skill/learned.py#L153): Docstring

> Every control the doings typed that is not proven constant.
>
> A control typed identically in every doing, with at least
> `K_MIN_OCCURRENCES` doings, is part of the job, not an input to it: a status
> every doing sets to the same thing. Everything else is a parameter -- a
> control only some doings reached (`in_all` false, so a run that takes the
> other route is not short of it), a control whose value changed, and every
> control of a single doing. Credentials never arrive here: `typed_values`
> refuses a secret gesture. A recorded sign-in's username and a chore are the
> caller's to leave out (`learn_parameters`), because only it knows the jobs.

## `constants_across`, [line 157](../../../../../../../backend/src/sro/domain/skill/learned.py#L157): Docstring

> The other half of the same arithmetic: the controls proven constant. A
> parameter minted from one doing and then typed identically by the next is
> one of these, which is how `learn_parameters` puts it back to fixed text.

## `_controls`, [line 161](../../../../../../../backend/src/sro/domain/skill/learned.py#L161): Docstring

> One walk over the doings for both answers, so a parameter and a constant
> can never be decided by two loops that drifted apart. `seen` keeps each
> value once, in the order the doings came: from three doings a value can
> repeat, and a range is a set of what it has been.

## `_told_apart`, [line 209](../../../../../../../backend/src/sro/domain/skill/learned.py#L209): Docstring

> Two controls that share a label are called by the names that differ.
>
> A form can have a Description in each of two sections. They are two
> parameters -- `same_control` kept them apart on the page's own name for
> each -- and calling both of them "Description" would put two questions
> with one wording in front of somebody, which is worse than one ugly name.
> So where a label is not unique, every control that shares it falls back to
> the name the page knows it by -- and keeps everything else it was found
> with. It was rebuilt from name, seen and names alone, which dropped `key`,
> `in_all` and what the page said: a told-apart control became "in every
> doing" and "nobody said", and lost the key a later doing is matched on.

## `placed_doings`, [line 219](../../../../../../../backend/src/sro/domain/skill/learned.py#L219): Docstring

> The other doings of a stored job, rebuilt from the gestures placed on it.
>
> A stored job cites one doing. Every later doing recognised as it was placed
> (`workflow_placements`, 0071) rather than kept, so a sweep that read only
> the cites would see one doing and mint every constant the job has ever had.
> Placements do not record which doing a gesture came from, so the doings are
> rebuilt from the typing alone: in time order per stream, a new doing starts
> where a control already typed in the current one is typed again. Two doings
> back to back therefore stay two, and every error this makes -- a correction
> or a search-as-you-type fragment read as a doing of its own -- makes a
> control look varied, never constant: it errs toward a parameter, the
> default. The job's own cites are left out; they are doing one.

## `LearnedParameter.required`, [line 56](../../../../../../../backend/src/sro/domain/skill/learned.py#L56): Docstring

> Whether the PAGE says this field must be filled.
>
> Not `in_all`, which is the question this used to be answered by and is
> a different one. `in_all` says every doing compared reached the
> control, which measures what the operator happened to do -- two
> demonstrations that both filled Manufacturer made it mandatory forever,
> and a third that skipped it would flip the answer back. Requiredness
> that moves with the sample is not a fact about the warehouse.
>
> The marker does not move. `names` carries every name the control
> answers to, exactly as the page gave them, and a form that marks its
> mandatory fields with a star gave one of them with the star on:
>
>     Customer Type              ["Customer Type", …, "Customer Type*"]
>     Customer Type Description  ["Customer Type Description", …, "…*"]
>     Department                 ["Department", "customertype-departmentNumber"]
>     Manufacturer               ["Manufacturer", "customertype-manufacturerId"]
>
> Read off the deployment 2026-09-22. The page had been saying which two
> of the four are mandatory since the day it was demonstrated, and
> nothing read it.
>
> **Unknown reads as optional**, which inverts the old default, and the
> failure modes are why. A required field treated as optional reaches
> Save, the form refuses, and the screen belt says so -- one failed run,
> and the warehouse has told us something we can keep. An optional field
> treated as required cannot run at all without a value the operator may
> not have: measured 2026-09-22 at 01:24, an operator with no Manufacturer
> to give had to drop the whole job.
>
> A star is a convention and not a contract, which is why this is one of
> two ways to be required and not the only one. The other is a warehouse
> that refused a create for the want of a field, which is evidence
> nothing can argue with -- and which this cannot learn until it happens.

## `_by_control`, [line 111](../../../../../../../backend/src/sro/domain/skill/learned.py#L111): Comment

Code: `acted: list[tuple[str, Gesture]] = []`

> In time order, not citation order. A control typed twice in one doing --
> `workArea` got TESTI then NEWTESTS in the real corpus -- keeps whichever
> value is written last, and last should mean latest, not "whichever the
> model happened to list second". Measured: 0 of 66 real steps cite out of
> order, so this changes nothing today and stops depending on that.

## `_by_control`, [line 116](../../../../../../../backend/src/sro/domain/skill/learned.py#L116): Comment

Code: `continue`

> A credential, or nothing typed. typed_values refuses the whole
> gesture when it is secret, so this is where that refusal keeps a
> password out of a skill's parameters.

## `_by_control`, [line 125](../../../../../../../backend/src/sro/domain/skill/learned.py#L125): Comment

Code: `names = control_names(gesture) or (cited,)`

> Every name the page gave this control, not the first one that was
> present. Which names a recording carries varies between recordings of
> the same form, and a control keyed on one of them is a control the
> next doing cannot recognise.

## `_by_control`, [line 127](../../../../../../../backend/src/sro/domain/skill/learned.py#L127): Comment

Code: `typed = str(gesture.action.value).strip() if gesture.action.value else ""`

> What the OPERATOR typed, where that is known. typed_values merges the
> operator's own value with the model's `values_seen` echo into one set
> and provenance is gone by the time it returns -- so a doing where the
> two disagree was being settled by string order. min() stays as the
> fallback for a gesture with no typed value of its own (a select the
> extension could not read, where the echo is all there is): it is
> arbitrary, but it is arbitrary the SAME way every run, and a
> parameter that changed value because a set iterated differently would
> be a phantom difference. Measured: 0 of 63 real type/select/upload
> gestures return more than one value, so nothing moves today --
> `values_seen` is populated on 110 of 387 intents, so the mechanism is
> armed.

## `_by_control`, [line 134](../../../../../../../backend/src/sro/domain/skill/learned.py#L134): Comment

Code: `found = [`

> Last wins, as it did when this was a dict: a control typed twice in
> one doing keeps the latest value.

## `_controls`, [line 164](../../../../../../../backend/src/sro/domain/skill/learned.py#L164): Comment

Code: `for nth, doing in enumerate(doings):`

> Every control ANY doing reached, and not only the first doing's.
>
> This iterated `doings[0]` -- the stored job, doing number one -- and
> broke out the moment a later doing did not have that control. So a
> control two LATER doings both varied was never looked at at all, and
> because a stored job's steps never grow it could never become a
> parameter however often it was used: an operator fills a field on
> Tuesday and again on Wednesday, each time with a different value, and
> the job goes on not knowing the field exists.
>
> What has gone is the accident of WHICH doing a control first appeared
> in. (The bar itself changed on 2026-09-27: see `parameters_across`.)

## `_controls`, [line 196](../../../../../../../backend/src/sro/domain/skill/learned.py#L196): Comment

Code: `name=names[0],`

> The readable name, and every name beside it. `names`
> is what the next doing is matched on, so a control
> recorded either way is recognised either way.

## `_controls`, [line 201](../../../../../../../backend/src/sro/domain/skill/learned.py#L201): Comment

Code: `said=next((one for one in said if one is not None), None),`

> What the page said about it, across the recordings
> that reached it. ANY, because a form that marks a
> field required marks it on every screen that renders
> it, and a recording that missed the mark -- an older
> capture, a screen where the label was truncated --
> is a silence rather than a denial. One recording
> that saw the mark is a page that has it.
