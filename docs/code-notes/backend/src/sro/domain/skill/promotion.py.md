# Notes for `backend/src/sro/domain/skill/promotion.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/promotion.py`](../../../../../../../backend/src/sro/domain/skill/promotion.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/promotion.py#L1): Docstring

> Promotion ladder. See docs/01-architecture.md#promotion-ladder.

## `check_promotion`, [line 29](../../../../../../../backend/src/sro/domain/skill/promotion.py#L29): Docstring

> Validate a promotion, or explain precisely why it is refused.

## module, [line 26](../../../../../../../backend/src/sro/domain/skill/promotion.py#L26): Comment

Code: `HIGHEST_PERMITTED_STAGE = PromotionStage.AUTONOMOUS`

> AUTONOMOUS is reachable now that the things which make it survivable exist:
> a run is classified (domain/execution/verdict.py), a version's clean streak is
> counted rather than asserted, a skill with no assertion anywhere can never
> qualify, three consecutive failures demote automatically, and a circuit
> breaker plus a write budget stop a run before it starts.
>
> Reachable is not the same as easy. `SkillVersion.promote` refuses the last
> rung until the record earns it, so the ceiling is no longer what holds the
> line -- the evidence is.
>
> The difference the ladder actually makes: at SHADOW a write is produced and
> withheld, at ASSISTED it is sent and the run names the human who allowed it,
> at AUTONOMOUS nobody is named because nobody was asked.
