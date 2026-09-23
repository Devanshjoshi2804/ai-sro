# Notes for `backend/src/sro/application/skill/add_assertion.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/add_assertion.py`](../../../../../../../backend/src/sro/application/skill/add_assertion.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/add_assertion.py#L1): Docstring

> Somebody saying what counts as this step having worked.
>
> A step's post-conditions normally come out of the recordings: two
> demonstrations answered the same status, or agreed on a field of the response,
> and that agreement is evidence. A step performed through a connector has no
> such thing behind it -- nobody watched `send_message` work -- so its only
> possible post-condition is one a person writes.
>
> That matters because of what an unchecked write costs. A step that changes
> something and proves nothing about the result makes the version unverifiable,
> and an unverifiable version may run assisted forever and never unattended. So
> without this the mapping in `map_step_to_tool.py` reaches exactly one rung
> short of the thing it exists for.
>
> Written after a run rather than before one, by design: an assertion invented
> before anybody has seen what the tool answers is a guess about a document, and
> the shadow rung exists precisely so somebody can look first.

## `AddAssertion`, [line 25](../../../../../../../backend/src/sro/application/skill/add_assertion.py#L25): Docstring

> Add one post-condition to one step, as a new version.
>
> Only ever adds. Nothing here removes a check induction derived, because
> those are what two demonstrations agreed on and this is somebody's
> opinion -- and an opinion that could delete a measurement is not a
> tightening.

## `_refuse_unless_checkable`, [line 101](../../../../../../../backend/src/sro/application/skill/add_assertion.py#L101): Docstring

> The rung this step runs at has to be able to answer the question.
>
> A tool answers a document: it has no status code and no screen, so
> `check_text` reports the other two kinds as unmet rather than skipping
> them. An assertion nothing can ever check does not make a step safer -- it
> makes every run of it fail, which is a different thing from a step being
> verified and reads the same on a screen.

## `AddAssertion.execute`, [line 67](../../../../../../../backend/src/sro/application/skill/add_assertion.py#L67): Comment

Code: `stage=PromotionStage.RECORDED,`

> The bottom of the ladder, like a mapping and unlike a repair.
> A streak earned before this check existed is not evidence
> that this check passes: every run in it succeeded without
> ever being asked the question.
