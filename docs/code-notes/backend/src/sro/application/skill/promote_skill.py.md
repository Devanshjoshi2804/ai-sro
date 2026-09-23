# Notes for `backend/src/sro/application/skill/promote_skill.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/promote_skill.py`](../../../../../../../backend/src/sro/application/skill/promote_skill.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/promote_skill.py#L1): Docstring

> Move a skill version one rung up the promotion ladder.
>
> Thin by design: the rules live on ``PromotionStage`` so they hold on every path,
> not only the ones that remember to call a service.

## `PromoteSkill.execute`, [line 16](../../../../../../../backend/src/sro/application/skill/promote_skill.py#L16): Docstring

> Move one version up one rung.
>
> ``acknowledging_fixed_values`` is the supervisor answering the one
> refusal they are allowed to answer: a version induced from a single
> demonstration sends the same values every time, and above shadow those
> values are actually sent. Saying so is a decision with a name on it, not
> a flag to default to true.

## `PromoteSkill.execute`, [line 33](../../../../../../../backend/src/sro/application/skill/promote_skill.py#L33): Comment

Code: `from_where="console",`

> This is a person opening the console and looking at the
> evidence, not a press on the panel's preview. The two are
> both reviews, and a blank here would read as either -- an old
> row from before this field existed, or this one -- which is
> exactly the ambiguity ADR 014 exists to remove.
