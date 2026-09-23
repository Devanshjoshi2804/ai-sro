# Notes for `backend/src/sro/application/skill/map_step_to_tool.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/map_step_to_tool.py`](../../../../../../../backend/src/sro/application/skill/map_step_to_tool.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/map_step_to_tool.py#L1): Docstring

> Somebody saying: this click is that tool.
>
> The one part of a skill nobody demonstrates. Induction reads recordings, and a
> recording holds gestures and the calls they made -- so a step performed through
> a connector is always a decision, and this is where the decision is recorded
> with the name of whoever made it.
>
> Why it matters at all: a gesture step can never reach `CLEAN`, so a skill whose
> mail half is clicks is assisted forever. Mapping that step onto a tool is what
> makes the ladder reachable, which is why the machinery exists (ADR 013) and why
> it is worth a screen.

## `MapStepToTool`, [line 27](../../../../../../../backend/src/sro/application/skill/map_step_to_tool.py#L27): Docstring

> Point one step of one version at a connector's tool.
>
> Produces a new version rather than editing the one in front of somebody.
> Every version is appended here -- a repair does it, an induction does it --
> and for the same reason: a version that changed under a reviewer who had
> already read it is a review of something else.

## `_refuse_unless_declared`, [line 111](../../../../../../../backend/src/sro/application/skill/map_step_to_tool.py#L111): Docstring

> Every `${name}` in the mapping is a parameter this version has.
>
> `SkillVersion` checks this too, and would refuse the new version -- but it
> would refuse it as an invariant violation, which reads as a bug in this
> system rather than as a typo in a form somebody just filled in.

## `MapStepToTool._refuse_unless_offered`, [line 88](../../../../../../../backend/src/sro/application/skill/map_step_to_tool.py#L88): Docstring

> The connector has to say it has this tool.
>
> Asked before the version is written rather than at the first run: a
> skill carrying a mapping onto a tool that does not exist looks exactly
> like a working one until somebody fires it, and by then the click it
> replaced has been mapped away.
>
> Asked as THIS operator, because that is the only person whose grant
> this is: a mapping checked against somebody else's would pass here and
> fail at the first run.

## `MapStepToTool.execute`, [line 52](../../../../../../../backend/src/sro/application/skill/map_step_to_tool.py#L52): Comment

Code: `_refuse_unless_present(source, step_index)`

> Read for the refusal alone: a mapping onto a step that is not
> there would otherwise produce a version identical to the one it
> came from, and report success.

## `MapStepToTool.execute`, [line 69](../../../../../../../backend/src/sro/application/skill/map_step_to_tool.py#L69): Comment

Code: `stage=PromotionStage.RECORDED,`

> The bottom of the ladder, whatever the version it was mapped
> from had earned. A repair inherits its rung because one
> locator changed and every value is the one the demonstrations
> carried; this is a step going through a door nobody has
> watched it go through. The streak that would let it run
> unattended has to be earned against the connector, not
> inherited from the clicks it replaced.

## `MapStepToTool.execute`, [line 77](../../../../../../../backend/src/sro/application/skill/map_step_to_tool.py#L77): Comment

Code: `induced_at=now,`

> The recordings stay: every other step, and every value
> this one sends, still came from them. What changed is how
> one step is performed, and `induced_by` is the person who
> decided that.
