# Notes for `backend/src/sro/application/induction/headers.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/headers.py`](../../../../../../../backend/src/sro/application/induction/headers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/headers.py#L1): Docstring

> Turn observed headers into a replayable header plan.
>
> Every header the call carried is recorded. Classification decides only where the
> value comes from at run time. See docs/11-capture-completeness.md.

## `build_header_plans`, [line 10](../../../../../../../backend/src/sro/application/induction/headers.py#L10): Docstring

> One HeaderPlan per observed header. Nothing is dropped.
>
> ``replacements`` carries the placeholders the diff produced. A semantic
> header that varied between the runs is a parameter like any other value:
> replaying run one's warehouse id when the operator asked for another
> warehouse is the same failure as replaying run one's wave id.

## `credential_key`, [line 59](../../../../../../../backend/src/sro/application/induction/headers.py#L59): Docstring

> Vault key for a credential. Scoped per system and facility, because a site
> has its own login even when the software is the same.

## `build_header_plans`, [line 33](../../../../../../../backend/src/sro/application/induction/headers.py#L33): Comment

Code: `plans.append(HeaderPlan(name=name, sensitivity=sensitivity, mint=True))`

> The captured value is stale by construction. Recording that the
> header is required is the useful part; the value is minted live.

## `build_header_plans`, [line 35](../../../../../../../backend/src/sro/application/induction/headers.py#L35): Comment

Code: `plans.append(HeaderPlan(name=name, sensitivity=sensitivity, managed=True))`

> Recorded because it was observed, never carried as a value:
> the domain says these are not replayable, and a captured
> Referer points at the page of a demonstration that is over.

## `build_header_plans`, [line 25](../../../../../../../backend/src/sro/application/induction/headers.py#L25): Comment

Code: `plans.append(`

> The value was taken out by SHAPE -- a token this name rule
> never recognised as one. `classify_header` judges by name
> only, so the header reads semantic while its value is the
> marker, and replaying it would put the literal characters
> «redacted» on the wire and call the plan replayable. A value
> removed because it looked like a credential is a credential,
> and the executor resolves it the way it resolves the others.

## `build_header_plans`, [line 50](../../../../../../../backend/src/sro/application/induction/headers.py#L50): Comment

Code: `value=Template(placeholder)`

> A placeholder is a deliberate `$name`; an observed
> value is a literal and means only itself. `Template`
> is `string.Template`, so a `$` in a captured header
> would report itself as a parameter the plan needs --
> and `SkillVersion` refuses a step referencing one it
> never declared, which takes down the whole build over
> a dollar sign in a header nobody parameterised.
