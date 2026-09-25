# Notes for `backend/src/sro/domain/execution/compose.py`

Comments and docstrings for [`backend/src/sro/domain/execution/compose.py`](../../../../../../../backend/src/sro/domain/execution/compose.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/compose.py#L1): Docstring

> A field nobody demonstrated (spec §6.6, X10). A run value whose name no step
> fills is composed into a step that fills it before the write whose screen shows
> it, from the outline stored with that write's gesture (E6). The outline holds
> labels, roles, required flags and options, never values.

## `SELECTS`, [line 14](../../../../../../../backend/src/sro/domain/execution/compose.py#L14): Constant

> The roles that are chosen, not typed: a combobox or listbox gets `select`,
> anything else gets `type` (spec §6.6 step 2).

## `normal`, [line 43](../../../../../../../backend/src/sro/domain/execution/compose.py#L43): Docstring

> The exact-label rule. A name matches a label only after normalising case,
> spacing and a required star, nothing more. Finding a field from other wording
> ("dept", "cost centre" for "Cost center") is design 2's work: a guess here would
> fill the wrong control on a live system, so anything short of an exact match is
> asked, never inferred.

## `compose`, [line 62](../../../../../../../backend/src/sro/domain/execution/compose.py#L62): Docstring

> A name is composed only when it has a value, no step already names it, it is
> not a credential name (`is_secret_field`: a password is never typed into a
> field chosen by its label), and it equals exactly one label on exactly one write
> step's last outline. No label, or more than one, is an `Unplaced` the run asks
> about with every label it saw; it is never guessed.

## `keyed`, [line 87](../../../../../../../backend/src/sro/domain/execution/compose.py#L87): Docstring

> The pairing rules for the save call's new body keys. `extra` is the keys the
> recorded body lacks, each with the value sent. Keys of learned field steps
> (`known`) are named first. Each field composed this run (`fresh`) then takes the
> key whose value equals its own, compared with `casefold` (a select sends the
> option's text or value). When exactly one field and one key are left, they pair
> (a select that sends an id). More extra keys than fields filled this run means
> the call carries something this run did not put there: it is not this write's
> own call, `None`, and the write is not confirmed by it. A field whose key is not
> found stays `unknown` even when the write is `done`: a fill alone never confirms
> anything (spec §6.2), only the write's own call does.

## `with_field`, [line 103](../../../../../../../backend/src/sro/domain/execution/compose.py#L103): Docstring

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

