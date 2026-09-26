# Notes for `backend/src/sro/domain/execution/field_classes.py`

Notes for [`backend/src/sro/domain/execution/field_classes.py`](../../../../../../../backend/src/sro/domain/execution/field_classes.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/field_classes.py#L1): Docstring

> Every field a job could be given, classed by what the evidence showed (spec
> §3 "Optional fields", A5): `required` (`demanded`), `always` (the miner's
> `in_all` -- seen in every doing, `domain/skill/learned.py:46`), `sometimes`
> (an optional parameter never shown in every doing, so offering it is a
> guess about this run, not a fact about the field) and `never` (a field the
> job's own outlines show but no parameter binds -- the panel does not offer
> it; design 3's job is whether to offer it anyway). Limits come from three
> places, the strictest wins: what a field held after typing (`learned_step
> .limits_for`'s `holds`), the page's own `maxlength` attribute on a
> single-parameter step's typed control (`_typed_caps` -- a step typing two
> fields cannot say whose cap it saw, so multi-parameter steps contribute
> none), and `declared`, the knowledge base's second source (user decision
> 2026-09-26): a hand-written recipe's parsed Fields/Buttons table, already
> indexed by the existing KB ingest into `form-models-all.json` and read by
> `application.execution.declared.declared_limits` -- reused here as a plain
> `Mapping[str, int]`, never a second parser. A limit only the KB knows (the
> page's own gate is looser, or absent) is still enforced.

## `FieldLimits`, [line 34](../../../../../../../backend/src/sro/domain/execution/field_classes.py#L34): Docstring

> What a value must fit to be accepted: a length, a closed option list, and
> whether the page itself marks the field required. `refuses` is the request
> reader's (R1's) gate -- `""` when the value fits, else the reason a caller
> shows the operator. Options compare by `normal` (case- and space-folded),
> the same exact-match rule `compose.py` places fields with.

## `field_classes`, [line 55](../../../../../../../backend/src/sro/domain/execution/field_classes.py#L55): Docstring

> One `FieldClass` per parameter, plus one `never` entry per outline field on
> a write screen (`compose.screens`) that no parameter's name or listed
> `names` matches, skipping any that is a credential (`is_secret_field`: a
> password is never offered or limited by label). `declared` defaults to
> empty so a caller with no knowledge-base lookup in hand (a unit test, a
> caller that has not wired one) still gets the page-only limits.
