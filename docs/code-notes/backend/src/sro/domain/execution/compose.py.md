# Notes for `backend/src/sro/domain/execution/compose.py`

Comments and docstrings for [`backend/src/sro/domain/execution/compose.py`](../../../../../../../backend/src/sro/domain/execution/compose.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/compose.py#L1): Docstring

> A field nobody demonstrated (spec §6.6, X10). A run value whose name no step
> fills is composed into a step that fills it before the write whose screen shows
> it, from the outline stored with that write's gesture (E6). The outline holds
> labels, roles, required flags and options, never values.

## `SELECTS`, [line 16](../../../../../../../backend/src/sro/domain/execution/compose.py#L16): Constant

> The roles that are chosen, not typed: a combobox or listbox gets `select`,
> anything else gets `type` (spec §6.6 step 2).

## `normal`, [line 45](../../../../../../../backend/src/sro/domain/execution/compose.py#L45): Docstring

> The exact-label rule. A name matches a label only after normalising case,
> spacing and a required star, nothing more. Finding a field from other wording
> ("dept", "cost centre" for "Cost center") is design 2's work: a guess here would
> fill the wrong control on a live system, so anything short of an exact match is
> asked, never inferred.

## `compose`, [line 100](../../../../../../../backend/src/sro/domain/execution/compose.py#L100): Docstring

> A name is composed only when it has a value, no step can be given it
> (`bindable`, the set mining's `undeliverable` keeps parameters by -- so a
> declared parameter whose step was lost is composed again, never silently
> dropped), it is
> not a credential name (`is_secret_field`: a password is never typed into a
> field chosen by its label), and it equals exactly one label on exactly one write
> step's last outline. No label, or more than one, is an `Unplaced` the run asks
> about with every label it saw; it is never guessed.

## `keyed`, [line 145](../../../../../../../backend/src/sro/domain/execution/compose.py#L145): Docstring

> The pairing rule for the save call's new body keys (spec §6.6.4, X10a review
> I1/I2). `extra` is the keys the recorded body lacks, each with the value sent.
> `fresh` holds, for every field filled this run, the value its control holds
> after the fill, read from the control (the input's value, or the selected
> option's value) -- not the operator's words. A key pairs with a field only when
> its sent value equals that held value and is non-empty; a learned key (`known`)
> pairs only with its own field, on the same condition. There is no pairing by
> elimination: a key whose value no field holds (`validateOnly: true`, a null a
> widget sent without taking the value, a draft flag) means the call is not this
> write's own -- `None` -- so it neither confirms the write nor teaches a key. A
> value two fields both hold cannot be attributed and is `None` too (safe: the
> write is `unknown` and the operator looks). A field whose key is not found stays
> `unknown` even when the write is `done`: a fill alone never confirms anything
> (spec §6.2), only the write's own call does.

## `with_field`, [line 157](../../../../../../../backend/src/sro/domain/execution/compose.py#L157): Docstring

> Learning a confirmed field: the step goes in at the write's order, and every
> later step, its `uses` and the repeat bounds shift by one. `moved` maps every
> old order to its new one, identities included, because `grew` drops what it
> does not find in it. The parameter is optional (`required: False`), keeps the
> value it was seen with, the label it was found by and the body key it was
> confirmed by.
>
> **Ceiling.** A later mining pass that grows the job re-derives its steps from
> demonstrations. `where_steps_moved` gives a step with no cites no place, so the
> learned step is dropped. Its parameter stays, and the next run with that value
> composes it again from the outline. Upgrade path: carry learned field steps
> through re-derivation as their own kind of step.

## `choices`, [line 68](../../../../../../../backend/src/sro/domain/execution/compose.py#L68): Docstring

> What a field question offers, each choice naming exactly one field: the
> label alone when it is on the forms once, with its role when that tells it
> apart, and with the write it comes before when that does. A label that none
> of these tells apart (two textboxes both "Notes" on one form, or on two
> writes that say the same) is not offered at all -- choosing it could never land on one control -- so the question may
> offer only "leave it out".

## `placed`, [line 89](../../../../../../../backend/src/sro/domain/execution/compose.py#L89): Docstring

> The fields labelled `label` (after `normal`) on those outlines, as `Composed`
> for `name`. `compose` places a name by its own words; an operator's answer to a
> field question places it by the label they chose -- the same exact-label rule,
> never a guess.

## `field_of`, [line 122](../../../../../../../backend/src/sro/domain/execution/compose.py#L122): Docstring

> The field a learned field step fills: its label (the parameter's first
> name) on the latest outline of the write right after it, found exactly
> once. None when that form no longer shows it, or shows it twice.

## `alias_map`, [line 49](../../../../../../../backend/src/sro/domain/execution/compose.py#L49): Docstring

> A job's aliases as `normal(wording) -> field`, so a required parameter named
> in a request's words binds to the field a step fills. Keyed by `normal`,
> the same folding the composer matches labels with.

## `compose`, [line 113](../../../../../../../backend/src/sro/domain/execution/compose.py#L113): Comment

Code: `hits = placed(workflow, by_id, name, said.get(normal(name), name))`

> A wording the operator has already placed on this job (spec §4.2, L3) is
> looked for under the label they chose, not under its own name: a confirmed
> alias outranks an exact label match, because the operator said so for this
> very wording. The composed value keeps the request's own name, so it still
> travels under the words the request used. Aliases are per job, and only an
> operator's answer makes one (`RunSteps.answered`); nothing here guesses.
