# Notes for `backend/src/sro/application/skill/version_from_rig.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/version_from_rig.py`](../../../../../../../backend/src/sro/application/skill/version_from_rig.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L1): Docstring

> A workflow the rig mined, as a version this system can review and run.
>
> `from_rig` turns a mined step into `UiPlan`s -- what a driver would do. This is
> the rest of the journey: a `SkillVersion`, which is what `/v1/runs`, the
> promotion ladder and the console all actually take. The gap between the two is
> not mechanical, and the interesting part of this module is what it refuses to
> invent rather than what it builds.
>
> **What it will not supply.** A `Skill` needs an `ObjectiveKey` -- objective
> type, target system, entity type, facility, direction -- and the rig produces
> none of those. It knows a title, the systems a job touched, and a shape key.
> Deriving "this is an inbound receipt against BLR1" from `Create Work Area
> NEWTESTS` would be a guess wearing the clothes of a finding, which is the exact
> move the citation requirement exists to stop. So this builds the version and
> the objective stays a person's decision, which is where it belongs: naming what
> a job is FOR is the reviewer's half of induction.
>
> **What it will not fake.** `Provenance.recording_ids` must be non-empty and the
> rig has no `Recording`. What the caller passes is the rig's `stream_id`, and
> that field deserves stating plainly rather than being called a near-equivalent:
> `correlate.py` sets it to `batch.device_id`, so a rig "stream" is **one browser
> profile for all time**, not a capture session. The id therefore names a device,
> will never resolve to a `Recording` row, and `ReadDoings` shows a version citing
> it as having zero doings rather than crashing.
>
> It is still passed rather than invented here, because it is the only provenance
> the rig holds and because minting one from something to hand would lie to
> `from_one_demonstration` -- a live safety rule deciding whether a write skill's
> values were ever diffed.
>
> `from_one_demonstration` is therefore always true of a rig version, and an
> earlier note here called that a conservative approximation. It is not an
> approximation: **a version's steps come from one proposal, and one proposal is
> one telling of the job.** A second reading becomes v2 rather than merging, so
> there genuinely is one demonstration behind each version. The residual is that
> nothing stops a model citing gestures from two occurrences in a single
> proposal -- `identity.resolve` tells those apart afterwards, not before -- and
> where that happens the count understates. Understating is the safe direction:
> `values_are_fixed` follows it and promotion asks more of a skill nobody
> diffed.
>
> Every version comes out at `RECORDED`. Nothing about a mined workflow has been
> reviewed by anybody, and the stage is the one field that says so.

## `parameters_from_rig`, [line 22](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L22): Docstring

> The rig's parameters as the domain's, with the evidence they actually have.
>
> PROVEN where two doings disagreed, which is the only thing `parameters_across`
> ever reports -- it returns a control precisely when its value CHANGED between
> occurrences, so a rig parameter is a fact rather than a reading. That is a
> stronger footing than the induction path's own PROPOSED, which is one
> demonstration plus a model's opinion.
>
> A parameter carrying fewer than two distinct values is downgraded rather
> than trusted. It should not exist -- nothing in the rig produces one -- and
> if the store ever holds one, the honest reading is that whatever made it did
> not do the diff this evidence level claims.
>
> Names and collisions come from `declared_parameters`, the same reader
> `bindings_for` uses, so what a version DECLARES and what its steps
> REFERENCE cannot drift apart.

## `version_from_rig`, [line 35](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L35): Docstring

> One mined workflow as a reviewable version, or None where it is not one.
>
> None rather than a version with no steps: a workflow whose citations all
> name evidence this store does not have describes a job nobody can perform,
> and an empty `SkillVersion` would sit in a library looking runnable.
>
> A rig step is prose over several gestures, and a `SkillStep` performs one
> thing -- the same convention `emit_step` follows on the induction path. So a
> step citing three gestures becomes three steps, each carrying the operator-
> level prose it came from. The prose repeats on purpose: those three gestures
> really were one described step, and renaming them apart would invent a
> distinction the evidence does not make.

## `_ordered`, [line 96](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L96): Docstring

> The workflow's steps in the order it gives them.
>
> `plans_for_workflow` already sorts by `order` with the guard that stops a
> quoted number crashing the sort; this reuses that rather than repeating
> the rule, and throws away the plans it builds along the way.

## `_starts_on`, [line 104](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L104): Docstring

> The url of the first gesture any step cites, in workflow order.
>
> Workflow order rather than clock order: the steps are what a run performs,
> and the screen a run must start on is the one the first STEP acts on. A
> gesture that happened earlier but is cited by a later step was part of the
> job's middle, whatever the clock says.

## `parameters_from_rig`, [line 27](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L27): Comment

Code: `description=f"what the operator typed into {label}",`

> The control's own label, kept because sanitising the name throws
> away how the operator would recognise the field: `Username or
> email` becomes `Username_or_email`, and a reviewer should still
> see what they typed into.

## `version_from_rig`, [line 47](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L47): Comment

Code: `named = tuple(`

> Blank and non-string ids are dropped before the emptiness check, not
> after. `if not recordings` passed a list of empty strings straight
> through to `RecordingId`, which refuses one and raises -- and `stream_id`
> comes out of a column, so a blank is a database's answer rather than a
> caller's mistake. `str(r)` was worse than raising: a JSON null became the
> literal id "None", which is exactly the minting this module says it
> refuses to do. A version with no readable provenance is refused.

## `version_from_rig`, [line 60](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L60): Comment

Code: `if not isinstance(gesture, Mapping):`

> A Mapping, not merely present. Everything here came off
> `json.loads` out of a column, and a citation naming a string or a
> null gave `AttributeError` from `.get` -- a traceback where the
> module's whole contract is that it refuses.

## `version_from_rig`, [line 62](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L62): Comment

Code: `ui = plan_for_gesture(gesture, bindings)`

> Both recipes for the same gesture, which is what ADR 005 means by
> dual: the network plan is how a run performs it without a
> browser, the UI plan is how it performs it when the call no
> longer works. Iterated here rather than through
> `plans_for_workflow` because a network plan belongs to a specific
> gesture and that function returns plans without saying which.

## `version_from_rig`, [line 71](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L71): Comment

Code: `if requests is not None and facility`

> Gated on the FACILITY alone. `target_system` is now derived
> per call from the host it went to, so requiring it here left
> a caller that correctly declined to name one system for a
> cross-system job with no network recipe at all.

## `version_from_rig`, [line 91](../../../../../../../backend/src/sro/application/skill/version_from_rig.py#L91): Comment

Code: `starts_on=_starts_on(workflow, gestures),`

> The screen the first cited gesture happened on.
>
> `starts_on` means "every demonstration of this task began here", and
> an earlier version guarded it with `len(named) == 1` -- which is
> structurally always true, since a rig stream is a device. A guard that
> cannot be false guards nothing. What actually makes the claim true is
> that a version's steps come from one proposal, so there is one
> demonstration to speak for.
