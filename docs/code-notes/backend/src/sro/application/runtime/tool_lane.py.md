# Notes for `backend/src/sro/application/runtime/tool_lane.py`

Notes on [`backend/src/sro/application/runtime/tool_lane.py`](../../../../../../../backend/src/sro/application/runtime/tool_lane.py). Each note names the code it explains (function or class, then the line in the current file).

## `ToolLane.execute`, [line 27](../../../../../../../backend/src/sro/application/runtime/tool_lane.py#L27): Comment

Code: `if isinstance(written, Unaddressed):`

> A draft refused for who it goes to is a question to the operator
> (`recipient`), not a failed step: a failed step's only answers are done or
> not done, and neither can say who the mail goes to. Nothing has left.

## `ToolLane.execute`, [line 30](../../../../../../../backend/src/sro/application/runtime/tool_lane.py#L30): Note

Code: `raise NeedsAPerson(f"{written}. {WHAT_IT_SAYS}", kind=MAIL_BODY)`

> A mail that could not be written -- no body, a model error, a value nobody
> gave -- asks its starter what it should say (S4 round 1, I1), as the draft
> path does. It was a failed step, asked `done` / `not_done`: it could take no
> words, a `not_done` wrote the same empty mail again, and a `done` finished the
> run `held` with nothing sent. Nothing left, so nothing is in doubt.
>
> Decided for now: the redraft on Steel sends as the step's write once
> `check_draft` passes, with no draft card, as M2 designed the lane. Whether an
> operator-typed body goes through a card first is the controller's to rule.
